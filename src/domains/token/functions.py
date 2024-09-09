import datetime
import os
from typing import Annotated

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import crud
from src.db.db import get_db_session
from src.domains.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BEARER
from src.domains.token.models import AccessTokenData, OAuthAccessToken
from src.domains.user.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Invalid login attempt',
    headers={'WWW-Authenticate': 'Bearer'}
)

security = HTTPBearer()


def get_oauth_access_token(user) -> OAuthAccessToken:
    """ The OAuth2 scheme requires a JSON with "access_token" and "token_type". """
    payload = {
        "sub": user.email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=int(os.getenv(JWT_EXPIRY_MINUTES, 15)))}
    jwt_token = jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))
    return OAuthAccessToken(access_token=jwt_token, token_type=BEARER)


async def has_access(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> AccessTokenData:
    """ OAuth2 bearer token """
    return get_token_data(credentials.credentials)


def get_token_data(authorization_token) -> AccessTokenData:
    try:
        payload = jwt.decode(
            authorization_token,
            key=os.getenv(JWT_SECRET_KEY),
            algorithms=[os.getenv(JWT_ALGORITHM)],
            verify=True,
            options={"verify_signature": True,
                     "verify_aud": False,
                     "verify_iss": False})
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        return AccessTokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception


async def get_user_from_token(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        access_token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    # Get token data
    token_data = get_token_data(access_token)

    # Get the token user
    user = await crud.get_one_where(
        db, User,
        att_name=User.email,
        att_value=token_data.user_email)
    if not user:
        raise credentials_exception
    return user
