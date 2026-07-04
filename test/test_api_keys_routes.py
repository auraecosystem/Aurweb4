from http import HTTPStatus
from typing import Generator

import pytest
from fastapi.testclient import TestClient

import aurweb.config
from aurweb import db
from aurweb.asgi import app
from aurweb.models.account_type import USER_ID
from aurweb.models.api_key import ApiKey
from aurweb.models.user import User
from aurweb.testing.requests import Request

TEST_REFERER = {
    "referer": aurweb.config.get("options", "aur_location") + "/",
}


@pytest.fixture(autouse=True)
def setup(db_test):
    return


@pytest.fixture
def client() -> TestClient:
    client = TestClient(app=app)
    client.headers.update(TEST_REFERER)
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
def user2() -> Generator[User]:
    with db.begin():
        user = db.create(
            User,
            Username="test2",
            Email="test2@example.org",
            Passwd="testPassword",
            AccountTypeID=USER_ID,
        )
    yield user


def test_api_keys_list_requires_auth(client: TestClient):
    with client as request:
        response = request.get("/account/test/api-keys")
    assert response.status_code == int(HTTPStatus.SEE_OTHER)
    assert "/login" in response.headers.get("location", "")


def test_api_keys_list_empty(client: TestClient, user: User):
    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.get("/account/test/api-keys")
    assert response.status_code == int(HTTPStatus.OK)
    assert "No API keys have been created" in response.text


def test_api_keys_create(client: TestClient, user: User):
    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.post(
            "/account/test/api-keys/create",
            data={"name": ""},
        )
    assert response.status_code == int(HTTPStatus.OK)
    assert "aur_" in response.text
    assert "will not be shown again" in response.text
    assert db.query(ApiKey).filter(ApiKey.UserID == user.ID).count() == 1


def test_api_keys_create_with_name(client: TestClient, user: User):
    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.post(
            "/account/test/api-keys/create",
            data={"name": "CI pipeline"},
        )
    assert response.status_code == int(HTTPStatus.OK)
    key = db.query(ApiKey).filter(ApiKey.UserID == user.ID).first()
    assert key.Name == "CI pipeline"


def test_api_keys_list_shows_keys(client: TestClient, user: User):
    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        # Create a key first
        request.post(
            "/account/test/api-keys/create",
            data={"name": "my key"},
        )
        # Then list
        response = request.get("/account/test/api-keys")
    assert response.status_code == int(HTTPStatus.OK)
    assert "my key" in response.text
    assert "Delete" in response.text


def test_api_keys_delete(client: TestClient, user: User):
    with db.begin():
        api_key = db.create(
            ApiKey,
            UserID=user.ID,
            KeyHash=ApiKey.hash_key("aur_testkey"),
            Name="deleteme",
        )
    key_id = api_key.ID

    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.post(f"/account/test/api-keys/{key_id}/delete")
    assert response.status_code == int(HTTPStatus.SEE_OTHER)
    assert db.query(ApiKey).filter(ApiKey.ID == key_id).first() is None


def test_api_keys_delete_nonexistent(client: TestClient, user: User):
    sid = user.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.post("/account/test/api-keys/99999/delete")
    assert response.status_code == int(HTTPStatus.NOT_FOUND)


def test_api_keys_other_user_forbidden(client: TestClient, user: User, user2: User):
    sid = user2.login(Request(), "testPassword")
    with client as request:
        request.cookies = {"AURSID": sid}
        response = request.get("/account/test/api-keys")
    assert response.status_code == int(HTTPStatus.UNAUTHORIZED)
