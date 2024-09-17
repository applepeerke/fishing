import datetime
import os

import jwt
from fastapi import HTTPException
from fastapi.security import SecurityScopes
from jwt import InvalidTokenError
from pydantic import ValidationError
from starlette import status

from src.db import crud
from src.domains.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BEARER
from src.domains.token.models import SessionData, AuthenticationToken
from src.domains.user.models import User


def create_authentication_token(email, scopes) -> AuthenticationToken:
    payload = {
        'sub': email,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=int(os.getenv(JWT_EXPIRY_MINUTES, 15))),
        'scopes': scopes}
    jwt_token = jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))
    return AuthenticationToken(token=jwt_token, token_type=BEARER)


async def get_session_data_from_token(
        security_scopes: SecurityScopes, session_token: AuthenticationToken, db) -> SessionData:
    # Read token
    try:
        payload = jwt.decode(
            session_token.token,
            key=os.getenv(JWT_SECRET_KEY),
            algorithms=[os.getenv(JWT_ALGORITHM)],
            verify=True,
            options={'verify_signature': True,
                     'verify_aud': False,
                     'verify_iss': False})
        email: str = payload.get('sub')
        if not email:
            _raise(security_scopes)

        # Check permissions
        # - User must exist
        if not await crud.get_one_where(db, User, User.email, email):
            _raise(security_scopes)
        # - All endpoint security scopes must be present in the token scopes (user)
        token_user_scopes = payload.get('scopes', [])
        if not all(scope in token_user_scopes for scope in security_scopes.scopes):
            _raise(security_scopes, 'Not authorized')
        return SessionData(scopes=token_user_scopes, email=email)

    except (InvalidTokenError, ValidationError):
        _raise(security_scopes)


def _raise(security_scopes: SecurityScopes = None, detail='Invalid credentials'):
    header_description = f'{BEARER} scope="{security_scopes.scope_str}"' if security_scopes else BEARER
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': header_description})
