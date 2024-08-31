import os

from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from src.domains.authentication.functions import authenticate_user, credentials_exception, validate_user
from src.domains.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES
from src.domains.token.models import Token, TokenData
from src.domains.user.models import User
from src.utils.db.db import get_db_session

from datetime import timedelta, datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.db import crud

token = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_token_user(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        access_token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    # Get token data
    token_data = _get_token_data(access_token)

    # Get the token user
    user = await crud.get_one_where(
        db, User,
        att_name=User.email,
        att_value=token_data.user_email
    )
    if not user:
        raise credentials_exception
    return user


def _get_token_data(access_token) -> TokenData:
    try:
        payload = jwt.decode(
            access_token, os.getenv(JWT_SECRET_KEY), algorithms=[os.getenv(JWT_ALGORITHM)], verify=True)
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        return TokenData(user_email=email)
    except InvalidTokenError:
        raise credentials_exception


def create_access_token(payload: dict):
    minutes = int(os.getenv(JWT_EXPIRY_MINUTES, 15))
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload_copy = payload.copy()
    payload_copy.update({"exp": expire})
    jwt_token = jwt.encode(
        payload=payload_copy,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM)
    )
    return jwt_token


@token.post("/")
async def get_access_token(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        credentials: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = await authenticate_user(db, credentials.username, credentials.password)
    access_token = create_access_token(payload={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")


@token.get("/authenticated_token_user")
async def get_authenticated_user(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        token_user: Annotated[User, Depends(get_token_user)]):
    authenticated_user = await validate_user(db, token_user)
    return authenticated_user
