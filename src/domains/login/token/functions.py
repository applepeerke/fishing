import datetime
import os
from typing import Annotated

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import SecurityScopes, HTTPBearer, HTTPAuthorizationCredentials
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from src.constants import ALL
from src.db import crud
from src.db.db import get_db_session
from src.domains.base.models import session_data_var
from src.domains.login.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BEARER
from src.domains.login.token.models import SessionData, Authorization
from src.domains.login.user.models import User

security = HTTPBearer()


def get_authorization(email, scopes: list) -> Authorization:
    payload = {
        'sub': email,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=int(os.getenv(JWT_EXPIRY_MINUTES, 15))),
        'scopes': scopes}
    jwt_token = jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))
    return Authorization(token=jwt_token, token_type=BEARER, scopes=scopes)


def set_session_from_header_token(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> SessionData:
    try:
        payload = jwt.decode(
            credentials.credentials,
            key=os.getenv(JWT_SECRET_KEY),
            algorithms=[os.getenv(JWT_ALGORITHM)],
            verify=True,
            options={'verify_signature': True,
                     'verify_aud': False,
                     'verify_iss': False})
        session_data = SessionData(scopes=payload.get('scopes', []), email=payload.get('sub'))
        session_data_var.set(session_data)
        return session_data
    except (InvalidTokenError, Exception):
        _raise()


async def is_authorized(
        security_scopes: SecurityScopes,
        token_data: Annotated[SessionData, Depends(set_session_from_header_token)],
        db: Annotated[AsyncSession, Depends(get_db_session)]
) -> bool:
    # Read token
    if not token_data.email:
        _raise(detail='Not authorized: No email')

    # Check permissions
    # - User must exist
    if not await crud.get_one_where(db, User, User.email, token_data.email):
        _raise(detail='Not authorized: User does not exist')

    # - All endpoint security scopes must be present in the token scopes (user)
    if not security_scopes or not all(_is_valid_scope(scope, token_data.scopes) for scope in security_scopes.scopes):
        _raise(
            security_scopes,
            detail=f'Not authorized: security_scopes "{security_scopes}" <> user_scopes "{token_data.scopes}"')
    return True


def _is_valid_scope(endpoint_scope, user_scopes) -> bool:
    """ Compare endpoint scope with user_scopes. """
    # Validation
    if not endpoint_scope or not user_scopes:
        return False
    ep_entity, ep_access = endpoint_scope.split('_', maxsplit=1)
    if not ep_entity or not ep_access:
        return False
    # Evaluate user_scopes
    for scope in user_scopes:
        # Validation
        entity, access = scope.split('_', maxsplit=1)
        if not entity or not access:
            continue
        if entity == ALL:  # E.g. "*_*" or "*_read"
            if access in (ALL, ep_access):
                return True
        else:  # E.g. "fish_*" or "fish_read"
            if entity == ep_entity or ep_entity == ALL:
                if access in (ALL, ep_access):
                    return True
    # No match
    return False


def remove_authorization_header(request: Request):
    request_headers = dict(request.scope['headers'])
    request.scope['headers'] = [(k, v) for k, v in request_headers.items() if k != b'authorization']


def _raise(security_scopes: SecurityScopes = None, detail='Invalid credentials'):
    # Invalidate session
    session_data_var.set(None)
    # Raise
    header_description = f'{BEARER} scope="{security_scopes.scope_str}"' if security_scopes else BEARER
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={'WWW-Authenticate': header_description})
