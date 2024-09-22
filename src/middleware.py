import os
import time

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import AUTHORIZATION, X_REFRESH_TOKEN, MSG_TOKEN_EXPIRED
from src.db import crud
from src.db.db import get_async_engine
from src.domains.login.token.constants import BEARER
from src.domains.login.token.functions import decode_jwt, session_login
from src.domains.login.token.models import SessionData
from src.domains.login.user.models import User
from src.utils.logging.log import logger


async def auto_token_refresh(request: Request, call_next) -> Response:
    """ # Automatic token refresh """
    access_token = request.headers.get(AUTHORIZATION, '').replace(f'{BEARER} ', '')
    refresh_token = request.headers.get(X_REFRESH_TOKEN)

    # If the access token is expired, try to refreh it automatically.
    try:
        if access_token:
            decode_jwt(access_token)
    except HTTPException as e:
        if (e.status_code == status.HTTP_401_UNAUTHORIZED
                and e.detail == MSG_TOKEN_EXPIRED
                and refresh_token):
            # The access token has expired. Try to refresh it using the refresh token.
            try:
                session_data: SessionData = decode_jwt(refresh_token)
                # The refresh token is valid. Log the session in with the new access- and refresh tokens.
                async_session = sessionmaker(bind=get_async_engine(), class_=AsyncSession, expire_on_commit=False)
                async with async_session() as db:
                    user = await crud.get_one_where(db, User, User.email, session_data.email)
                    logger.info(f'{__name__}: User "{session_data.email}" tokens are auto-refreshed.')
                    response = await session_login(db, user)
                    return response

            except HTTPException as e:
                logger.warning(f'{__name__}: refresh token could not be decoded. {e.detail}')
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)
        else:
            logger.warning(f'{__name__}: access token could not be decoded. {e.detail}')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)

    # Call the next handler in the middleware chain
    return await call_next(request)


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


async def add_log_entry(request: Request, call_next):
    # Preparation
    url_length = int(os.getenv('LOGGING_MAX_URL_NAME', '50'))
    formatted_url = str(request.url).replace(str(request.base_url), '').ljust(url_length)
    if len(formatted_url) > url_length:
        formatted_url = f'{formatted_url[:url_length - 3]}...'
    method = request.method.ljust(6)
    # Log before
    logger.info(f'{__name__}: Str {method} {formatted_url}')
    start_time = time.perf_counter()
    # Execute
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    # Log after
    logger.info(f'{__name__}: End {method} {formatted_url} Duration: {str(process_time)}')
    return response
