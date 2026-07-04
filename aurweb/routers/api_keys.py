from http import HTTPStatus

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from aurweb import db, l10n, models, util
from aurweb.auth import creds, requires_auth
from aurweb.models.api_key import ApiKey
from aurweb.templates import make_context, render_template
from aurweb.users.util import get_user_by_name

router = APIRouter()


def _check_permission(request: Request, user: models.User):
    has_cred = request.user.has_credential(creds.ACCOUNT_EDIT, approved=[user])
    if not has_cred:
        _ = l10n.get_translator_for_request(request)
        raise HTTPException(
            detail=_("You do not have permission to edit this account."),
            status_code=HTTPStatus.UNAUTHORIZED,
        )


def _make_context(request: Request, user: models.User, **kwargs):
    context = make_context(request, "Accounts")
    context["user"] = user
    context["api_keys"] = user.api_keys.order_by(ApiKey.CreatedTS.desc()).all()
    context.update(kwargs)
    return context


@router.get("/account/{username}/api-keys", response_class=HTMLResponse)
@requires_auth
async def api_keys_list(request: Request, username: str):
    user = get_user_by_name(username)
    _check_permission(request, user)
    context = _make_context(request, user)
    return render_template(request, "account/api_keys.html", context)


@router.post("/account/{username}/api-keys/create", response_class=HTMLResponse)
@requires_auth
async def api_keys_create(
    request: Request,
    username: str,
    name: str = Form(default=""),
):
    user = get_user_by_name(username)
    _check_permission(request, user)

    context = _make_context(request, user)

    raw_key = util.generate_api_key()
    key_hash = ApiKey.hash_key(raw_key)

    with db.begin():
        db.create(
            ApiKey,
            UserID=user.ID,
            KeyHash=key_hash,
            Name=name.strip(),
        )

    # Re-fetch keys after creation.
    context["api_keys"] = user.api_keys.order_by(ApiKey.CreatedTS.desc()).all()
    context["new_key"] = raw_key
    return render_template(request, "account/api_keys.html", context)


@router.post(
    "/account/{username}/api-keys/{key_id}/delete", response_class=HTMLResponse
)
@requires_auth
async def api_keys_delete(
    request: Request,
    username: str,
    key_id: int,
):
    user = get_user_by_name(username)
    _check_permission(request, user)

    api_key = (
        db.query(ApiKey).filter(ApiKey.ID == key_id, ApiKey.UserID == user.ID).first()
    )
    if not api_key:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    with db.begin():
        db.delete(api_key)

    return RedirectResponse(
        f"/account/{username}/api-keys", status_code=HTTPStatus.SEE_OTHER
    )
