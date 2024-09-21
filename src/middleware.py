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


async def auto_token_refresh(request: Request, call_next) -> Response:
    """ # Automatic token refresh """
    access_token = request.headers.get(AUTHORIZATION, '').replace(f'{BEARER} ', '')
    refresh_token = request.headers.get(X_REFRESH_TOKEN)

    # Check if the access token is valid or expired
    try:
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
                    response = await session_login(db, user)
                    return response

            except HTTPException as e:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)

    # Call the next handler in the middleware chain
    return await call_next(request)


async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
