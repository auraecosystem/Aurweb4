from collections import defaultdict
from typing import Any

from sqlalchemy import Float, and_, cast, literal
from sqlalchemy.orm import Query, aliased
from sqlalchemy.sql.expression import func

from aurweb import config, db, models
from aurweb.exceptions import APIError
from aurweb.models import (
    DependencyType,
    Group,
    Package,
    PackageBase,
    PackageComaintainer,
    PackageDependency,
    PackageGroup,
    PackageKeyword,
    PackageLicense,
    PackageRelation,
    RelationType,
    User,
)
from aurweb.models.dependency_type import (
    CHECKDEPENDS_ID,
    DEPENDS_ID,
    MAKEDEPENDS_ID,
    OPTDEPENDS_ID,
)
from aurweb.models.relation_type import CONFLICTS_ID, PROVIDES_ID, REPLACES_ID

VALID_VERSIONS = {6}

VALID_TYPES = {
    "search",
    "info",
    "suggest",
    "suggest-pkgbase",
}

VALID_BYS_SEARCH = {
    "name",
    "name-desc",
}

VALID_BYS_INFO = {
    "name",
    "maintainer",
    "submitter",
    "depends",
    "makedepends",
    "optdepends",
    "checkdepends",
    "provides",
    "conflicts",
    "replaces",
    "groups",
    "keywords",
    "comaintainers",
}

VALID_MODES = {"contains", "starts-with"}

TYPE_MAPPING = {
    "depends": "Depends",
    "makedepends": "MakeDepends",
    "checkdepends": "CheckDepends",
    "optdepends": "OptDepends",
    "conflicts": "Conflicts",
    "provides": "Provides",
    "replaces": "Replaces",
}

DEPENDS_MAPPING = {
    "depends": DEPENDS_ID,
    "makedepends": MAKEDEPENDS_ID,
    "optdepends": OPTDEPENDS_ID,
    "checkdepends": CHECKDEPENDS_ID,
}

RELATIONS_MAPPING = {
    "provides": PROVIDES_ID,
    "replaces": REPLACES_ID,
    "conflicts": CONFLICTS_ID,
}


class API:
    """
    API handler class.

    Parameters:
    :param version: API version
    :param type: Type of request
    :param by: The field that is being used to filter our query
    :param mode: The search mode (only applicable for the search type)
    :param arg: A list of keywords that is used to filter our records
    """

    def __init__(self, version: str, type: str, by: str, mode: str, arg: list[str]):
        try:
            self.version = int(version)
        except ValueError:
            self.version = None
        self.type = type
        self.by = by
        self.mode = mode
        self.arg = arg

        # set default for empty "by" parameter
        if type == "search" and (by == "" or by is None):
            self.by = "name-desc"
        elif by == "" or by is None:
            self.by = "name"

        # set default for empty "mode" parameter
        if mode == "" or mode is None:
            self.mode = "contains"

        # base query
        self.query = self._get_basequery()

    def get_results(self) -> dict[str, Any]:
        """
        Returns a dictionary with our data.
        """

        # input validation
        try:
            self._validate_parameters()
        except APIError as ex:
            return self.error(str(ex))

        data = {
            "resultcount": 0,
            "results": [],
            "type": self.type,
            "version": self.version,
        }

        # get results according to type
        try:
            if self.type == "search":
                data["results"] = self._search()
            if self.type.startswith("suggest"):
                data["suggest"] = self._suggest()
            if self.type == "info":
                data["results"] = self._info()
        except APIError as ex:
            return self.error(str(ex))

        data["resultcount"] = len(data["results"])

        return data

    def error(self, message: str) -> dict[str, Any]:
        """
        Returns a dictionary with an empty result set and error message.
        """
        return {
            "error": message,
            "resultcount": 0,
            "results": [],
            "type": "error",
            "version": self.version,
        }

    def _validate_parameters(self):
        if self.version not in VALID_VERSIONS:
            raise APIError("Invalid version specified.")
        if self.type not in VALID_TYPES:
            raise APIError("Incorrect request type specified.")
        if (self.type == "search" and self.by not in VALID_BYS_SEARCH) or (
            self.type == "info" and self.by not in VALID_BYS_INFO
        ):
            raise APIError("Incorrect by field specified.")
        if self.mode not in VALID_MODES:
            raise APIError("Incorrect mode specified.")
        if self.type == "search" and (len(self.arg) == 0 or len(self.arg[0]) < 2):
            raise APIError("Query arg too small.")
        if self.type == "info" and self.by != "maintainer" and len(self.arg) == 0:
            raise APIError("Query arg too small.")

    def _search(self) -> list[dict[str, Any]]:
        for keyword in self.arg[0].split(" "):
            # define search expression according to "mode"
            expression = f"{keyword}%" if self.mode == "starts-with" else f"%{keyword}%"

            # name or name/desc search
            if self.by == "name":
                self.query = self.query.filter(Package.Name.like(expression))
            else:
                self.query = self.query.filter(
                    (Package.Name.like(expression))
                    | (Package.Description.like(expression))
                )

        return self._run_queries()

    def _suggest(self) -> list[dict[str, Any]]:
        if len(self.arg) == 0:
            self.arg.append("")
        query = (
            db.query(Package.Name)
            .join(PackageBase)
            .filter(
                (PackageBase.PackagerUID.isnot(None))
                & Package.Name.like(f"{self.arg[0]}%")
            )
            .order_by(Package.Name)
        )

        if self.type == "suggest-pkgbase":
            query = (
                db.query(PackageBase.Name)
                .filter(
                    (PackageBase.PackagerUID.isnot(None))
                    & PackageBase.Name.like(f"{self.arg[0]}%")
                )
                .order_by(PackageBase.Name)
            )

        data = query.limit(20).all()

        # "suggest" returns an array of strings
        return [rec[0] for rec in data]

    def _info(self) -> list[dict[str, Any]]:  # noqa: C901
        # get unique list of arguments
        args = set(self.arg)

        # subquery for submitter and comaintainer queries
        users = db.query(User.ID).filter(User.Username.in_(args))

        # Define joins and filters for our "by" parameter
        if self.by == "name":
            self.query = self.query.filter(Package.Name.in_(args))
        elif self.by == "maintainer":
            if len(args) == 0 or self.arg[0] == "":
                self.query = self.query.filter(PackageBase.MaintainerUID.is_(None))
            else:
                self.query = self.query.filter(PackageBase.MaintainerUID.in_(users))
        elif self.by == "submitter":
            self.query = self.query.filter(PackageBase.SubmitterUID.in_(users))
        elif self.by in ["depends", "makedepends", "optdepends", "checkdepends"]:
            self.query = self.query.join(PackageDependency).filter(
                (PackageDependency.DepTypeID == DEPENDS_MAPPING.get(self.by, 0))
                & (PackageDependency.DepName.in_(args))
            )
        elif self.by in ["provides", "conflicts", "replaces"]:
            self.query = self.query.join(PackageRelation).filter(
                (PackageRelation.RelTypeID == RELATIONS_MAPPING.get(self.by, 0))
                & (PackageRelation.RelName.in_(args))
            )

            # A package always provides itself, so we have to include it.
            # Union query is the fastest way of doing this.
            if self.by == "provides":
                itself = self._get_basequery().filter(Package.Name.in_(args))
                self.query = self.query.union(itself)
        elif self.by == "groups":
            self.query = (
                self.query.join(PackageGroup).join(Group).filter(Group.Name.in_(args))
            )
        elif self.by == "keywords":
            self.query = (
                self.query.join(PackageKeyword)
                .filter(PackageKeyword.Keyword.in_(args))
                .distinct()
            )
        elif self.by == "comaintainers":
            self.query = (
                self.query.join(
                    PackageComaintainer,
                    PackageBase.ID == PackageComaintainer.PackageBaseID,
                )
                .filter(PackageComaintainer.UsersID.in_(users))
                .distinct()
            )

        return self._run_queries()

    def _run_queries(self) -> list[dict[str, Any]]:
        max_results = config.getint("options", "max_rpc_results")

        # get basic package data
        base_data = self.query.limit(max_results + 1).all()
        packages = [dict(row._asdict()) for row in base_data]

        # return error if we exceed max results
        if len(base_data) > max_results:
            raise APIError("Too many package results.")

        # get list of package IDs for our subquery
        ids = {pkg.ID for pkg in base_data}

        # get data from related tables
        sub_data = self._get_subqueries(ids).all()

        # store extended information in dict for later lookup
        extra_info = defaultdict(lambda: defaultdict(list))
        for record in sub_data:
            type_ = TYPE_MAPPING.get(record.Type, record.Type)

            name = record.Name
            if record.Cond:
                name += record.Cond

            extra_info[record.ID][type_].append(name)

        # add extended info to each package
        for pkg in packages:
            pkg.update(extra_info.get(pkg["ID"], []))
            pkg.pop("ID")  # remove ID from our results

        return packages

    def _get_basequery(self) -> Query:
        snapshot_uri = config.get("options", "snapshot_uri")
        Submitter = aliased(User)
        return (
            db.query(Package)
            .join(PackageBase)
            .join(
                User,
                User.ID == PackageBase.MaintainerUID,
                isouter=True,
            )
            .join(
                Submitter,
                Submitter.ID == PackageBase.SubmitterUID,
                isouter=True,
            )
            .with_entities(
                Package.ID,
                Package.Name,
                Package.Description,
                Package.Version,
                PackageBase.Name.label("PackageBase"),
                Package.URL,
                func.replace(snapshot_uri, "%s", PackageBase.Name).label("URLPath"),
                User.Username.label("Maintainer"),
                Submitter.Username.label("Submitter"),
                PackageBase.SubmittedTS.label("FirstSubmitted"),
                PackageBase.ModifiedTS.label("LastModified"),
                PackageBase.OutOfDateTS.label("OutOfDate"),
                PackageBase.NumVotes,
                cast(PackageBase.Popularity, Float).label("Popularity"),
            )
        )

    def _get_subqueries(self, ids: set[int]) -> Query:
        subqueries = [
            # PackageDependency
            db.query(PackageDependency)
            .join(DependencyType)
            .filter(PackageDependency.PackageID.in_(ids))
            .with_entities(
                PackageDependency.PackageID.label("ID"),
                DependencyType.Name.label("Type"),
                PackageDependency.DepName.label("Name"),
                PackageDependency.DepCondition.label("Cond"),
            )
            .distinct()  # A package could have the same dependency multiple times
            .order_by("Name"),
            # PackageRelation
            db.query(PackageRelation)
            .join(RelationType)
            .filter(PackageRelation.PackageID.in_(ids))
            .with_entities(
                PackageRelation.PackageID.label("ID"),
                RelationType.Name.label("Type"),
                PackageRelation.RelName.label("Name"),
                PackageRelation.RelCondition.label("Cond"),
            )
            .distinct()  # A package could have the same relation multiple times
            .order_by("Name"),
            # Groups
            db.query(PackageGroup)
            .join(
                Group,
                and_(
                    PackageGroup.GroupID == Group.ID,
                    PackageGroup.PackageID.in_(ids),
                ),
            )
            .with_entities(
                PackageGroup.PackageID.label("ID"),
                literal("Groups").label("Type"),
                Group.Name.label("Name"),
                literal(str()).label("Cond"),
            )
            .order_by("Name"),
            # Licenses
            db.query(PackageLicense)
            .join(models.License, PackageLicense.LicenseID == models.License.ID)
            .filter(PackageLicense.PackageID.in_(ids))
            .with_entities(
                PackageLicense.PackageID.label("ID"),
                literal("License").label("Type"),
                models.License.Name.label("Name"),
                literal(str()).label("Cond"),
            )
            .order_by("Name"),
            # Keywords
            db.query(PackageKeyword)
            .join(
                Package,
                and_(
                    Package.PackageBaseID == PackageKeyword.PackageBaseID,
                    Package.ID.in_(ids),
                ),
            )
            .with_entities(
                Package.ID.label("ID"),
                literal("Keywords").label("Type"),
                PackageKeyword.Keyword.label("Name"),
                literal(str()).label("Cond"),
            )
            .order_by("Name"),
            # Co-Maintainer
            db.query(PackageComaintainer)
            .join(User, User.ID == PackageComaintainer.UsersID)
            .join(
                Package,
                Package.PackageBaseID == PackageComaintainer.PackageBaseID,
            )
            .with_entities(
                Package.ID,
                literal("CoMaintainers").label("Type"),
                User.Username.label("Name"),
                literal(str()).label("Cond"),
            )
            .distinct()  # A package could have the same co-maintainer multiple times
            .order_by("Name"),
        ]

        # Union all subqueries into one statement.
        return subqueries[0].union_all(*subqueries[1:])
