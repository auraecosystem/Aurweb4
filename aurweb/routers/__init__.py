"""
API routers for FastAPI.

See https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""
from . import (
    accounts,
    api,
    auth,
    html,
    package_maintainer,
    packages,
    pkgbase,
    requests,
    rpc,
    rss,
    sso,
)

"""
aurweb application routes. This constant can be any iterable
and each element must have a .router attribute which points
to a fastapi.APIRouter.
"""
APP_ROUTES = [
    accounts,
    api,
    auth,
    html,
    packages,
    pkgbase,
    requests,
    package_maintainer,
    rss,
    rpc,
    sso,
]
