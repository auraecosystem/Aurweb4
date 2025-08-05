from aurweb.models.account_type import (
    MODERATOR_ID,
    PACKAGE_MAINTAINER_AND_MOD_ID,
    PACKAGE_MAINTAINER_ID,
    USER_ID,
)
from aurweb.models.user import User

ACCOUNT_CHANGE_TYPE = 1
ACCOUNT_EDIT = 2
ACCOUNT_EDIT_DEV = 3
ACCOUNT_LAST_LOGIN = 4
ACCOUNT_SEARCH = 5
ACCOUNT_LIST_COMMENTS = 28
COMMENT_DELETE = 6
COMMENT_UNDELETE = 27
COMMENT_VIEW_DELETED = 22
COMMENT_EDIT = 25
COMMENT_PIN = 26
PKGBASE_ADOPT = 7
PKGBASE_SET_KEYWORDS = 8
PKGBASE_DELETE = 9
PKGBASE_DISOWN = 10
PKGBASE_EDIT_COMAINTAINERS = 24
PKGBASE_FLAG = 11
PKGBASE_LIST_VOTERS = 12
PKGBASE_NOTIFY = 13
PKGBASE_UNFLAG = 15
PKGBASE_VOTE = 16
PKGREQ_FILE = 23
PKGREQ_CLOSE = 17
PKGREQ_LIST = 18
PM_ADD_VOTE = 19
PM_LIST_VOTES = 20
PM_VOTE = 21
PKGBASE_MERGE = 29

user_moderator_or_package_maintainer = set(
    [USER_ID, MODERATOR_ID, PACKAGE_MAINTAINER_ID, PACKAGE_MAINTAINER_AND_MOD_ID]
)
moderator = set([MODERATOR_ID, PACKAGE_MAINTAINER_AND_MOD_ID])
moderator_or_pm = set(
    [MODERATOR_ID, PACKAGE_MAINTAINER_ID, PACKAGE_MAINTAINER_AND_MOD_ID]
)
package_maintainer = set([PACKAGE_MAINTAINER_ID, PACKAGE_MAINTAINER_AND_MOD_ID])
package_maintainer_or_mod = set(
    [MODERATOR_ID, PACKAGE_MAINTAINER_ID, PACKAGE_MAINTAINER_AND_MOD_ID]
)

cred_filters = {
    PKGBASE_FLAG: user_moderator_or_package_maintainer,
    PKGBASE_NOTIFY: user_moderator_or_package_maintainer,
    PKGBASE_VOTE: user_moderator_or_package_maintainer,
    PKGREQ_FILE: user_moderator_or_package_maintainer,
    ACCOUNT_CHANGE_TYPE: moderator,
    ACCOUNT_EDIT: moderator,
    ACCOUNT_LAST_LOGIN: moderator,
    ACCOUNT_LIST_COMMENTS: moderator,
    ACCOUNT_SEARCH: moderator,
    COMMENT_DELETE: moderator,
    COMMENT_UNDELETE: moderator,
    COMMENT_VIEW_DELETED: moderator,
    COMMENT_EDIT: moderator,
    COMMENT_PIN: moderator,
    PKGBASE_ADOPT: moderator,
    PKGBASE_SET_KEYWORDS: moderator,
    PKGBASE_DELETE: moderator,
    PKGBASE_EDIT_COMAINTAINERS: moderator,
    PKGBASE_DISOWN: moderator,
    PKGBASE_LIST_VOTERS: moderator,
    PKGBASE_UNFLAG: moderator,
    PKGREQ_CLOSE: moderator,
    PKGREQ_LIST: moderator,
    PM_ADD_VOTE: package_maintainer,
    PM_LIST_VOTES: moderator,
    PM_VOTE: package_maintainer,
    ACCOUNT_EDIT_DEV: package_maintainer,
    PKGBASE_MERGE: moderator,
}


def has_credential(user: User, credential: int, approved: list = tuple()):
    if user in approved:
        return True
    return user.AccountTypeID in cred_filters[credential]
