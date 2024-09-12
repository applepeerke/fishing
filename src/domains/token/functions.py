import datetime
import os

import jwt
from fastapi import HTTPException
from jwt import InvalidTokenError
from starlette import status

from src.domains.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BEARER
from src.domains.token.models import SessionTokenData, SessionToken

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Invalid login attempt',
    headers={'WWW-Authenticate': 'Bearer'}
)


def create_session_token(user) -> SessionToken:
    payload = {
        "sub": user.email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=int(os.getenv(JWT_EXPIRY_MINUTES, 15)))}
    jwt_token = jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))
    return SessionToken(token=jwt_token, token_type=BEARER)


def get_session_token_data(authorization_token) -> SessionTokenData:
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
        return SessionTokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

