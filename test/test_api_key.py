from typing import Generator

import pytest
from sqlalchemy.exc import IntegrityError

from aurweb import db, util
from aurweb.models.account_type import USER_ID
from aurweb.models.api_key import ApiKey
from aurweb.models.user import User


@pytest.fixture(autouse=True)
def setup(db_test):
    return


@pytest.fixture
def user() -> Generator[User]:
    with db.begin():
        user = db.create(
            User,
            Username="test",
            Email="test@example.org",
            RealName="Test User",
            Passwd="testPassword",
            AccountTypeID=USER_ID,
        )
    yield user


@pytest.fixture
def api_key(user: User) -> Generator[ApiKey]:
    raw_key = util.generate_api_key()
    with db.begin():
        api_key = db.create(
            ApiKey,
            UserID=user.ID,
            KeyHash=ApiKey.hash_key(raw_key),
            Name="test key",
        )
    yield api_key


def test_api_key_creation(user: User, api_key: ApiKey) -> None:
    assert api_key.UserID == user.ID
    assert len(api_key.KeyHash) == 64
    assert api_key.Name == "test key"
    assert api_key.CreatedTS is not None
    assert api_key.ID is not None


def test_api_key_user_relationship(user: User, api_key: ApiKey) -> None:
    assert api_key.User == user
    assert api_key in user.api_keys.all()


def test_api_key_hash() -> None:
    key = "aur_abc123"
    hash1 = ApiKey.hash_key(key)
    hash2 = ApiKey.hash_key(key)
    assert hash1 == hash2
    assert len(hash1) == 64
    assert ApiKey.hash_key("aur_different") != hash1


def test_api_key_cascade_delete(user: User, api_key: ApiKey) -> None:
    key_id = api_key.ID
    with db.begin():
        db.delete(user)
    assert db.query(ApiKey).filter(ApiKey.ID == key_id).first() is None


def test_api_key_unique_hash(user: User, api_key: ApiKey) -> None:
    with pytest.raises(IntegrityError):
        with db.begin():
            db.create(
                ApiKey,
                UserID=user.ID,
                KeyHash=api_key.KeyHash,
                Name="duplicate",
            )
