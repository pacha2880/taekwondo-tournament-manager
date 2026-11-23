import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def validation_error_with_json_safe_input(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Same 422 as FastAPI's default, but its error echoes the rejected `input`: an `Infinity` or `NaN` sent in the
    # body (Python's JSON parser accepts them) can't be serialized back, and the 422 turned into a 500.
    return JSONResponse(status_code=422, content={"detail": _json_safe(jsonable_encoder(exc.errors()))})


def add_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_with_json_safe_input)
