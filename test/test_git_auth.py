import base64
from http import HTTPStatus
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from aurweb import db, time, util
from aurweb.asgi import app
from aurweb.models.account_type import PACKAGE_MAINTAINER_ID, USER_ID
from aurweb.models.api_key import ApiKey
from aurweb.models.package_base import PackageBase
from aurweb.models.user import User


def _basic_auth(username: str, key: str) -> dict:
    encoded = base64.b64encode(f"{username}:{key}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def _write_uri(pkgbase: str = "test-pkg") -> dict:
    return {"X-Original-URI": f"/{pkgbase}.git/info/refs?service=git-receive-pack"}


def _read_uri(pkgbase: str = "test-pkg") -> dict:
    return {"X-Original-URI": f"/{pkgbase}.git/info/refs?service=git-upload-pack"}


@pytest.fixture(autouse=True)
def setup(db_test):
    return


@pytest.fixture
def client() -> TestClient:
    client = TestClient(app=app)
    client.follow_redirects = False
    yield client


@pytest.fixture
def user() -> Generator[User]:
    with db.begin():
        user = db.create(
            User,
            Username="test",
            Email="test@example.org",
            Passwd="testPassword",
            AccountTypeID=USER_ID,
        )
    yield user


@pytest.fixture
def api_key_pair(user: User) -> Generator[tuple[ApiKey, str]]:
    """Returns (ApiKey record, raw key string)."""
    raw_key = util.generate_api_key()
    with db.begin():
        api_key = db.create(
            ApiKey,
            UserID=user.ID,
            KeyHash=ApiKey.hash_key(raw_key),
            Name="test",
        )
    yield api_key, raw_key


def test_read_op_no_auth(client: TestClient):
    with client as request:
        response = request.get("/_git_auth_check", headers=_read_uri())
    assert response.status_code == int(HTTPStatus.OK)


def test_write_op_no_auth(client: TestClient):
    with client as request:
        response = request.get("/_git_auth_check", headers=_write_uri())
    assert response.status_code == int(HTTPStatus.UNAUTHORIZED)
    assert response.headers.get("WWW-Authenticate") == 'Basic realm="AUR"'


def test_write_op_valid_key(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    _, raw_key = api_key_pair
    headers = {**_write_uri(), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.OK)
    assert response.headers.get("X-AUR-User") == "test"
    assert response.headers.get("X-AUR-Privileged") == "0"


def test_write_op_invalid_key(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    headers = {**_write_uri(), **_basic_auth("test", "aur_wrongkey")}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.FORBIDDEN)


def test_write_op_wrong_username(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    _, raw_key = api_key_pair
    headers = {**_write_uri(), **_basic_auth("wronguser", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.FORBIDDEN)


def test_write_op_suspended_user(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    with db.begin():
        user.Suspended = 1
    _, raw_key = api_key_pair
    headers = {**_write_uri(), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.FORBIDDEN)


def test_write_op_no_write_access(client: TestClient, api_key_pair: tuple[ApiKey, str]):
    _, raw_key = api_key_pair
    with db.begin():
        other = db.create(
            User,
            Username="other",
            Email="other@example.org",
            Passwd="testPassword",
            AccountTypeID=USER_ID,
        )
    now = time.utcnow()
    with db.begin():
        db.create(
            PackageBase,
            Name="other-pkg",
            MaintainerUID=other.ID,
            SubmitterUID=other.ID,
            SubmittedTS=now,
            ModifiedTS=now,
            FlaggerComment="",
        )
    headers = {**_write_uri("other-pkg"), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.FORBIDDEN)


def test_write_op_orphaned_package(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    _, raw_key = api_key_pair
    now = time.utcnow()
    with db.begin():
        db.create(
            PackageBase,
            Name="orphan-pkg",
            MaintainerUID=None,
            SubmittedTS=now,
            ModifiedTS=now,
            FlaggerComment="",
        )
    headers = {**_write_uri("orphan-pkg"), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.OK)


def test_write_op_new_package(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    _, raw_key = api_key_pair
    headers = {
        **_write_uri("nonexistent-pkg"),
        **_basic_auth("test", raw_key),
    }
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.OK)


def test_write_op_malformed_auth(client: TestClient):
    headers = {**_write_uri(), "Authorization": "Basic notvalidbase64!!!"}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.UNAUTHORIZED)


def test_last_used_updated(
    client: TestClient, user: User, api_key_pair: tuple[ApiKey, str]
):
    api_key, raw_key = api_key_pair
    assert api_key.LastUsedTS is None
    headers = {**_write_uri(), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.OK)
    db.get_session().refresh(api_key)
    assert api_key.LastUsedTS is not None


def test_privileged_user_bypass_access_check(
    client: TestClient, api_key_pair: tuple[ApiKey, str]
):
    api_key, raw_key = api_key_pair
    user = api_key.User
    with db.begin():
        user.AccountTypeID = PACKAGE_MAINTAINER_ID
    with db.begin():
        other = db.create(
            User,
            Username="other",
            Email="other@example.org",
            Passwd="testPassword",
            AccountTypeID=USER_ID,
        )
    now = time.utcnow()
    with db.begin():
        db.create(
            PackageBase,
            Name="priv-pkg",
            MaintainerUID=other.ID,
            SubmitterUID=other.ID,
            SubmittedTS=now,
            ModifiedTS=now,
            FlaggerComment="",
        )
    headers = {**_write_uri("priv-pkg"), **_basic_auth("test", raw_key)}
    with client as request:
        response = request.get("/_git_auth_check", headers=headers)
    assert response.status_code == int(HTTPStatus.OK)
    assert response.headers.get("X-AUR-Privileged") == "1"
