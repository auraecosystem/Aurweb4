import base64
import re

from fastapi import APIRouter, Request
from fastapi.responses import Response

from aurweb import db, time
from aurweb.models.api_key import ApiKey
from aurweb.models.package_base import PackageBase
from aurweb.models.package_comaintainer import PackageComaintainer
from aurweb.models.user import User
from aurweb.ratelimit import check_ratelimit
from aurweb.util import get_client_ip

router = APIRouter()

# Matches /pkgbase.git/... or /pkgbase/...
_PKGBASE_RE = re.compile(r"^/([a-z0-9][a-z0-9.+_-]*?)(?:\.git)?/")


def _is_write_op(uri: str) -> bool:
    return "service=git-receive-pack" in uri or uri.endswith("/git-receive-pack")


def _has_write_access(pkgbase_name: str, user: User) -> bool:
    pkgbase = db.query(PackageBase).filter(PackageBase.Name == pkgbase_name).first()

    if not pkgbase:
        return True

    if not pkgbase.MaintainerUID:
        return True

    if pkgbase.MaintainerUID == user.ID:
        return True

    is_comaintainer = (
        db.query(PackageComaintainer)
        .filter(
            PackageComaintainer.PackageBaseID == pkgbase.ID,
            PackageComaintainer.UsersID == user.ID,
        )
        .first()
    )

    return is_comaintainer is not None


@router.get("/_git_auth_check")
@db.async_retry_stale_connection
async def git_auth_check(request: Request):
    original_uri = request.headers.get("X-Original-URI", "")

    if not _is_write_op(original_uri):
        return Response(status_code=200)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AUR"'},
        )

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        username, api_key = decoded.split(":", 1)
    except Exception:
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="AUR"'},
        )

    if check_ratelimit(request):
        return Response(status_code=429)

    key_hash = ApiKey.hash_key(api_key)
    api_key_record = (
        db.query(ApiKey)
        .join(User, ApiKey.UserID == User.ID)
        .filter(
            ApiKey.KeyHash == key_hash,
            User.Username == username,
            User.Suspended == 0,
        )
        .first()
    )

    if not api_key_record:
        return Response(status_code=403)

    user = api_key_record.User
    privileged = "1" if user.AccountTypeID > 1 else "0"

    # Check write access to the specific package base.
    match = _PKGBASE_RE.match(original_uri)
    if match:
        pkgbase_name = match.group(1)
        if privileged != "1" and not _has_write_access(pkgbase_name, user):
            return Response(status_code=403)

    # Update last-used tracking.
    with db.begin():
        api_key_record.LastUsedTS = time.utcnow()
        api_key_record.LastUsedIPAddress = get_client_ip(request)

    return Response(
        status_code=200,
        headers={
            "X-AUR-User": user.Username,
            "X-AUR-Privileged": privileged,
        },
    )
