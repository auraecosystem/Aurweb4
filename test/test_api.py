from http import HTTPStatus
from unittest import mock

import orjson
import pytest
from fastapi.testclient import TestClient
from redis.client import Pipeline

import aurweb.models.dependency_type as dt
import aurweb.models.relation_type as rt
from aurweb import asgi, config, db, scripts, time
from aurweb.aur_redis import redis_connection
from aurweb.models.account_type import USER_ID
from aurweb.models.group import Group
from aurweb.models.license import License
from aurweb.models.package import Package
from aurweb.models.package_base import PackageBase
from aurweb.models.package_comaintainer import PackageComaintainer
from aurweb.models.package_dependency import PackageDependency
from aurweb.models.package_group import PackageGroup
from aurweb.models.package_keyword import PackageKeyword
from aurweb.models.package_license import PackageLicense
from aurweb.models.package_relation import PackageRelation
from aurweb.models.package_vote import PackageVote
from aurweb.models.user import User


@pytest.fixture
def client() -> TestClient:
    yield TestClient(app=asgi.app)


@pytest.fixture
def user(db_test) -> User:
    with db.begin():
        user = db.create(
            User,
            Username="test",
            Email="test@example.org",
            RealName="Test User 1",
            Passwd=str(),
            AccountTypeID=USER_ID,
        )
    yield user


@pytest.fixture
def user2() -> User:
    with db.begin():
        user = db.create(
            User,
            Username="user2",
            Email="user2@example.org",
            RealName="Test User 2",
            Passwd=str(),
            AccountTypeID=USER_ID,
        )
    yield user


@pytest.fixture
def user3() -> User:
    with db.begin():
        user = db.create(
            User,
            Username="user3",
            Email="user3@example.org",
            RealName="Test User 3",
            Passwd=str(),
            AccountTypeID=USER_ID,
        )
    yield user


@pytest.fixture
def packages(user: User, user2: User, user3: User) -> list[Package]:
    output = []

    # Create package records used in our tests.
    with db.begin():
        pkgbase = db.create(
            PackageBase,
            Name="big-chungus",
            Maintainer=user,
            Packager=user,
            Submitter=user2,
            SubmittedTS=1672214227,
            ModifiedTS=1672214227,
        )
        pkg = db.create(
            Package,
            PackageBase=pkgbase,
            Name=pkgbase.Name,
            Description="Bunny bunny around bunny",
            URL="https://example.com/",
            Version="1.0.0",
        )
        output.append(pkg)

        pkgbase = db.create(
            PackageBase,
            Name="chungy-chungus",
            Maintainer=user,
            Packager=user,
            Submitter=user2,
            SubmittedTS=1672214227,
            ModifiedTS=1672214227,
        )
        pkg = db.create(
            Package,
            PackageBase=pkgbase,
            Name=pkgbase.Name,
            Description="Wubby wubby on wobba wuubu",
            URL="https://example.com/",
            Version="2.0.0",
        )
        output.append(pkg)

        pkgbase = db.create(
            PackageBase, Name="gluggly-chungus", Maintainer=user, Packager=user
        )
        pkg = db.create(
            Package,
            PackageBase=pkgbase,
            Name=pkgbase.Name,
            Description="glurrba glurrba gur globba",
            URL="https://example.com/",
        )
        output.append(pkg)

        pkgbase = db.create(
            PackageBase, Name="fugly-chungus", Maintainer=user, Packager=user
        )

        desc = "A Package belonging to a PackageBase with another name."
        pkg = db.create(
            Package,
            PackageBase=pkgbase,
            Name="other-pkg",
            Description=desc,
            URL="https://example.com",
        )
        output.append(pkg)

        pkgbase = db.create(PackageBase, Name="woogly-chungus")
        pkg = db.create(
            Package,
            PackageBase=pkgbase,
            Name=pkgbase.Name,
            Description="wuggla woblabeloop shemashmoop",
            URL="https://example.com/",
        )
        output.append(pkg)

    # Setup a few more related records on the first package:
    # a license, group, some keywords, comaintainer and some votes.
    with db.begin():
        lic = db.create(License, Name="GPL")
        db.create(PackageLicense, Package=output[0], License=lic)

        grp = db.create(Group, Name="testgroup")
        db.create(PackageGroup, Package=output[0], Group=grp)

        db.create(
            PackageComaintainer,
            PackageBase=output[0].PackageBase,
            User=user2,
            Priority=1,
        )

        for keyword in ["big-chungus", "smol-chungus", "sizeable-chungus"]:
            db.create(
                PackageKeyword, PackageBase=output[0].PackageBase, Keyword=keyword
            )

        now = time.utcnow()
        for user_ in [user, user2, user3]:
            db.create(
                PackageVote, User=user_, PackageBase=output[0].PackageBase, VoteTS=now
            )
    scripts.popupdate.run_single(output[0].PackageBase)

    yield output


@pytest.fixture
def depends(packages: list[Package]) -> list[PackageDependency]:
    output = []

    with db.begin():
        dep = db.create(
            PackageDependency,
            Package=packages[0],
            DepTypeID=dt.DEPENDS_ID,
            DepName="chungus-depends",
        )
        output.append(dep)

        dep = db.create(
            PackageDependency,
            Package=packages[1],
            DepTypeID=dt.DEPENDS_ID,
            DepName="chungy-depends",
        )
        output.append(dep)

        dep = db.create(
            PackageDependency,
            Package=packages[0],
            DepTypeID=dt.OPTDEPENDS_ID,
            DepName="chungus-optdepends",
            DepCondition="=50",
        )
        output.append(dep)

        dep = db.create(
            PackageDependency,
            Package=packages[0],
            DepTypeID=dt.MAKEDEPENDS_ID,
            DepName="chungus-makedepends",
        )
        output.append(dep)

        dep = db.create(
            PackageDependency,
            Package=packages[0],
            DepTypeID=dt.CHECKDEPENDS_ID,
            DepName="chungus-checkdepends",
        )
        output.append(dep)

    yield output


@pytest.fixture
def relations(packages: list[Package]) -> list[PackageRelation]:
    output = []

    with db.begin():
        rel = db.create(
            PackageRelation,
            Package=packages[0],
            RelTypeID=rt.CONFLICTS_ID,
            RelName="chungus-conflicts",
        )
        output.append(rel)

        rel = db.create(
            PackageRelation,
            Package=packages[1],
            RelTypeID=rt.CONFLICTS_ID,
            RelName="chungy-conflicts",
        )
        output.append(rel)

        rel = db.create(
            PackageRelation,
            Package=packages[0],
            RelTypeID=rt.PROVIDES_ID,
            RelName="chungus-provides",
            RelCondition="<=200",
        )
        output.append(rel)

        rel = db.create(
            PackageRelation,
            Package=packages[0],
            RelTypeID=rt.REPLACES_ID,
            RelName="chungus-replaces",
            RelCondition="<=200",
        )
        output.append(rel)

    # Finally, yield the packages.
    yield output


@pytest.fixture
def comaintainer(
    user2: User, user3: User, packages: list[Package]
) -> list[PackageComaintainer]:
    output = []

    with db.begin():
        comaintainer = db.create(
            PackageComaintainer,
            User=user2,
            PackageBase=packages[0].PackageBase,
            Priority=1,
        )
        output.append(comaintainer)

        comaintainer = db.create(
            PackageComaintainer,
            User=user3,
            PackageBase=packages[0].PackageBase,
            Priority=1,
        )
        output.append(comaintainer)

    # Finally, yield the packages.
    yield output


@pytest.fixture(autouse=True)
def setup(db_test):
    # Create some extra package relationships.
    pass


@pytest.fixture
def pipeline():
    redis = redis_connection()
    pipeline = redis.pipeline()

    # The 'testclient' host is used when requesting the app
    # via fastapi.testclient.TestClient.
    pipeline.delete("ratelimit-ws:testclient")
    pipeline.delete("ratelimit:testclient")
    pipeline.execute()

    yield pipeline


expected_single = {
    "version": 6,
    "results": [
        {
            "Name": "big-chungus",
            "Version": "1.0.0",
            "Description": "Bunny bunny around bunny",
            "URL": "https://example.com/",
            "PackageBase": "big-chungus",
            "NumVotes": 3,
            "Popularity": 3.0,
            "Maintainer": "test",
            "Submitter": "user2",
            "FirstSubmitted": 1672214227,
            "LastModified": 1672214227,
            "URLPath": "/cgit/aur.git/snapshot/big-chungus.tar.gz",
            "Depends": ["chungus-depends"],
            "OptDepends": ["chungus-optdepends=50"],
            "MakeDepends": ["chungus-makedepends"],
            "CheckDepends": ["chungus-checkdepends"],
            "Conflicts": ["chungus-conflicts"],
            "CoMaintainers": ["user2", "user3"],
            "Provides": ["chungus-provides<=200"],
            "Replaces": ["chungus-replaces<=200"],
            "License": ["GPL"],
            "Keywords": ["big-chungus", "sizeable-chungus", "smol-chungus"],
            "Groups": ["testgroup"],
        }
    ],
    "resultcount": 1,
    "type": "info",
}

expected_multi = {
    "version": 6,
    "results": [
        expected_single["results"][0],
        {
            "Name": "chungy-chungus",
            "Version": "2.0.0",
            "Description": "Wubby wubby on wobba wuubu",
            "URL": "https://example.com/",
            "PackageBase": "chungy-chungus",
            "NumVotes": 0,
            "Popularity": 0.0,
            "Maintainer": "test",
            "Submitter": "user2",
            "FirstSubmitted": 1672214227,
            "LastModified": 1672214227,
            "URLPath": "/cgit/aur.git/snapshot/chungy-chungus.tar.gz",
            "Depends": ["chungy-depends"],
            "Conflicts": ["chungy-conflicts"],
        },
    ],
    "resultcount": 2,
    "type": "info",
}


def test_api_info_get_query(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "name"
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_get_path(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/info/big-chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with path params
    with client as request:
        resp = request.get(
            "/api/v6/info/name/big-chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_post(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: POST with form param
    with client as request:
        resp = request.post(
            "/api/v6/info",
            data={
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_get_multiple(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "name"
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "arg": ["big-chungus", "chungy-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_post_multiple(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: POST with form param
    with client as request:
        resp = request.post(
            "/api/v6/info",
            data={
                "arg": ["big-chungus", "chungy-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_depends(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "depends"
    with client as request:
        resp = request.get(
            "/api/v6/info/depends/chungus-depends",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "depends", multiple
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "by": "depends",
                "arg": ["chungus-depends", "chungy-depends"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_makedepends(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "makedepends"
    with client as request:
        resp = request.get(
            "/api/v6/info/makedepends/chungus-makedepends",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_optdepends(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "optdepends"
    with client as request:
        resp = request.get(
            "/api/v6/info/optdepends/chungus-optdepends",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_checkdepends(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "checkdepends"
    with client as request:
        resp = request.get(
            "/api/v6/info/checkdepends/chungus-checkdepends",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_provides(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "provides"
    with client as request:
        resp = request.get(
            "/api/v6/info/provides/chungus-provides",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "provides", multiple
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "by": "provides",
                "arg": ["big-chungus", "chungy-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_conflicts(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "conflicts"
    with client as request:
        resp = request.get(
            "/api/v6/info/conflicts/chungus-conflicts",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "conflicts", multiple
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "by": "conflicts",
                "arg": ["chungus-conflicts", "chungy-conflicts"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_replaces(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "replaces"
    with client as request:
        resp = request.get(
            "/api/v6/info/replaces/chungus-replaces",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_submitter(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "submitter"
    with client as request:
        resp = request.get(
            "/api/v6/info/submitter/user2",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_multi


def test_api_info_maintainer(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "maintainer"
    with client as request:
        resp = request.get(
            "/api/v6/info/maintainer/test",
        )

    response_data = orjson.loads(resp.text)
    assert response_data["resultcount"] == 4


def test_api_info_keywords(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "keywords"
    with client as request:
        resp = request.get(
            "/api/v6/info/keywords/big-chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "keywords", multiple
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "by": "keywords",
                "arg": ["big-chungus", "sizeable-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_groups(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "groups"
    with client as request:
        resp = request.get(
            "/api/v6/info/groups/testgroup",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_comaintainers(
    client: TestClient,
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with query param by "comaintainers"
    with client as request:
        resp = request.get(
            "/api/v6/info/comaintainers/user2",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_info_none(
    client: TestClient,
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with non existent pkg
    with client as request:
        resp = request.get(
            "/api/v6/info/nonsense",
        )

    response_data = orjson.loads(resp.text)
    assert len(response_data["results"]) == 0
    assert response_data["resultcount"] == 0


def test_api_info_orphans(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET by maintainer without arg
    with client as request:
        resp = request.get(
            "/api/v6/info",
            params={
                "by": "maintainer",
            },
        )

    response_data = orjson.loads(resp.text)
    assert len(response_data["results"]) == 1
    assert response_data["resultcount"] == 1

    # Make request: GET by maintainer with empty arg
    with client as request:
        resp = request.get("/api/v6/info", params={"by": "maintainer", "arg": ""})

    response_data = orjson.loads(resp.text)
    assert len(response_data["results"]) == 1
    assert response_data["resultcount"] == 1


def test_api_search_get_query(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with query param by "name-desc"
    with client as request:
        resp = request.get(
            "/api/v6/search",
            params={
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "name"
    with client as request:
        resp = request.get(
            "/api/v6/search",
            params={
                "by": "name",
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with query param by "name" with "mode"
    with client as request:
        resp = request.get(
            "/api/v6/search",
            params={
                "mode": "contains",
                "by": "name",
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_get_path(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/search/big-chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single

    # Make request: GET with path params
    with client as request:
        resp = request.get(
            "/api/v6/search/name/big-chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_post(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: POST with form param
    with client as request:
        resp = request.post(
            "/api/v6/search",
            data={
                "by": "name",
                "arg": ["big-chungus"],
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_description(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/search/name-desc/bunny",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_multiterm(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with multiple terms
    with client as request:
        resp = request.get(
            "/api/v6/search/name-desc/big%20around",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_starts_with(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/search/name/starts-with/big",
        )

    response_data = orjson.loads(resp.text)
    assert response_data == expected_single


def test_api_search_all(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "search"

    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/search/name/contains/chungus",
        )

    response_data = orjson.loads(resp.text)
    assert response_data["resultcount"] == 4


def test_api_suggest(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/suggest/big",
        )

    response_data = orjson.loads(resp.text)
    assert response_data[0] == "big-chungus"

    # Make request: GET with query param
    with client as request:
        resp = request.get(
            "/api/v6/suggest",
            params={
                "arg": "big",
            },
        )

    response_data = orjson.loads(resp.text)
    assert response_data[0] == "big-chungus"


def test_api_suggest_empty(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # set expected "type"
    expected_single["type"] = "suggest"

    # Make request: GET without arg
    with client as request:
        resp = request.get(
            "/api/v6/suggest",
        )

    response_data = orjson.loads(resp.text)
    assert response_data[0] == "big-chungus"
    assert len(response_data) == 4


def test_api_suggest_pkgbase(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with path param
    with client as request:
        resp = request.get(
            "/api/v6/suggest-pkgbase/big",
        )

    response_data = orjson.loads(resp.text)
    assert response_data[0] == "big-chungus"

    # Make request: GET with query param
    with client as request:
        resp = request.get(
            "/api/v6/suggest-pkgbase",
            params={
                "arg": "big",
            },
        )

    response_data = orjson.loads(resp.text)

    # Validate response
    assert response_data[0] == "big-chungus"


def test_api_error_wrong_type(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with wrong type
    with client as request:
        resp = request.get(
            "/api/v6/nonsense/bla",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Incorrect request type specified."


def test_api_error_wrong_version(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with wrong version
    with client as request:
        resp = request.get(
            "/api/vnonsense/info/bla",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Invalid version specified."


def test_api_error_wrong_by(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with wrong by field
    with client as request:
        resp = request.get(
            "/api/v6/info/nonsense/bla",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Incorrect by field specified."


def test_api_error_wrong_mode(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with wrong mode
    with client as request:
        resp = request.get(
            "/api/v6/search/name/nonsense/bla",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Incorrect mode specified."


def test_api_error_arg_too_small(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    # Make request: GET with no arg
    with client as request:
        resp = request.get(
            "/api/v6/search",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Query arg too small."

    # Make request: GET with single character arg
    with client as request:
        resp = request.get(
            "/api/v6/search/a",
        )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Query arg too small."


def test_api_error_too_many_results(
    client: TestClient,
    packages: list[Package],
    depends: list[PackageDependency],
    relations: list[PackageRelation],
    comaintainer: list[PackageComaintainer],
):
    config_getint = config.getint

    def mock_config(section: str, key: str):
        if key == "max_rpc_results":
            return 1
        return config_getint(section, key)

    # Make request: GET with too many results
    with mock.patch("aurweb.config.getint", side_effect=mock_config):
        with client as request:
            resp = request.get(
                "/api/v6/search/chungus",
            )

    response_data = orjson.loads(resp.text)
    assert resp.status_code == int(HTTPStatus.BAD_REQUEST)
    assert response_data["error"] == "Too many package results."


def test_api_error_ratelimit(
    client: TestClient,
    pipeline: Pipeline,
    packages: list[Package],
):
    config_getint = config.getint

    def mock_config(section: str, key: str):
        if key == "request_limit":
            return 4
        return config_getint(section, key)

    with mock.patch("aurweb.config.getint", side_effect=mock_config):
        for _ in range(4):
            # The first 4 requests should be good.
            with client as request:
                resp = request.get(
                    "/api/v6/suggest",
                )
            assert resp.status_code == int(HTTPStatus.OK)

        # The fifth request should be banned.
        with client as request:
            resp = request.get(
                "/api/v6/suggest",
            )
        assert resp.status_code == int(HTTPStatus.TOO_MANY_REQUESTS)

        # Delete the cached records.
        pipeline.delete("ratelimit-ws:testclient")
        pipeline.delete("ratelimit:testclient")
        one, two = pipeline.execute()
        assert one and two

        # The new request should be good.
        with client as request:
            resp = request.get(
                "/api/v6/suggest",
            )
        assert resp.status_code == int(HTTPStatus.OK)
