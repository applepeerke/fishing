import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from src.db.db import get_async_engine


async def add_db_session(request: Request, call_next):
    """ Create an async db session at the middleware level. """
    async_session = sessionmaker(bind=get_async_engine(), class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        request.state.db = session  # Store the session in request.state
        # Process request
        response = await call_next(request)
    # Return the response
    return response


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
