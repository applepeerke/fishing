import time

from fastapi import HTTPException
from fastapi.exceptions import ResponseValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.session.session import authenticate_session


async def add_authentication_header(request: Request, call_next):
    try:
        authenticate_session(request)
        return await call_next(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={'detail': e.detail}
        )
    except ResponseValidationError as e:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'detail': f'An unexpected error occurred in the session middleware: "{e}"'}
        )


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
