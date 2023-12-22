"""
API routing module

Available routes:

- GET /api/v{version}/{type}/{arg}
- GET /api/v{version}/{type}/{by}/{arg}
- GET /api/v{version}/{type}/{by}/{mode}/{arg}

- GET /api/v{version}/{type} (query params: by, mode, arg)

- POST /api/v{version}/{type} (form values: by, mode, arg)

"""

from http import HTTPStatus
from typing import Any

import orjson
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from aurweb.api import API
from aurweb.ratelimit import check_ratelimit
from aurweb.util import remove_empty

router = APIRouter()


# path based
@router.get("/api/v{version}/{type}/{arg}")
async def api_version_type_arg(request: Request, version: str, type: str, arg: str):
    return handle_request(
        request=request, version=version, type=type, by="", mode="", arg=list([arg])
    )


@router.get("/api/v{version}/{type}/{by}/{arg}")
async def api_version_type_by_arg(
    request: Request, version: str, type: str, by: str, arg: str
):
    return handle_request(
        request=request, version=version, type=type, by=by, mode="", arg=list([arg])
    )


@router.get("/api/v{version}/{type}/{by}/{mode}/{arg}")
async def api_version_type_by_mode_arg(
    request: Request, version: str, type: str, by: str, mode: str, arg: str
):
    return handle_request(
        request=request, version=version, type=type, by=by, mode=mode, arg=list([arg])
    )


# query string
@router.get("/api/v{version}/{type}")
async def api_version_type(request: Request, version: str, type: str):
    params = request.query_params
    by = params.get("by")
    mode = params.get("mode")
    arg = params.getlist("arg")

    return handle_request(
        request=request, version=version, type=type, by=by, mode=mode, arg=arg
    )


# form data (POST)
@router.post("/api/v{version}/{type}")
async def api_post_version_type(request: Request, version: str, type: str):
    form = await request.form()
    by = form.get("by")
    mode = form.get("mode")
    arg = form.getlist("arg")

    return handle_request(
        request=request, version=version, type=type, by=by, mode=mode, arg=arg
    )


def handle_request(
    request: Request, version: str, type: str, by: str, mode: str, arg: list[str]
):
    """
    Middleware for checking rate-limits

    All routers should initiate requests through this function.
    """
    api = API(version=version, type=type, by=by, mode=mode, arg=arg)

    # rate limit check
    if check_ratelimit(request):
        return JSONResponse(
            api.error("Rate limit reached"),
            status_code=int(HTTPStatus.TOO_MANY_REQUESTS),
        )

    # run query and return results
    return compose_response(api.get_results())


def compose_response(result: dict[str, Any]) -> Response:
    """
    Converts our data into JSON format and generates a response.
    We also check for any errors and set the http status accordingly.
    """

    status = HTTPStatus.OK
    if result.get("error") is not None:
        status = HTTPStatus.BAD_REQUEST

    # suggest calls are returned as plain JSON string array
    if result.get("suggest") is not None:
        return JSONResponse(result["suggest"])

    # remove null values from results and compose JSON data
    result["results"] = remove_empty(result["results"])
    data = orjson.dumps(result)
    return Response(content=data, status_code=status, media_type="application/json")
