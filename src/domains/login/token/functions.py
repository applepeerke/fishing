import datetime
import os
from typing import Annotated

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import SecurityScopes, HTTPBearer, HTTPAuthorizationCredentials
from jwt import InvalidTokenError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import ALL, AUTHORIZATION, X_REFRESH_TOKEN, MSG_TOKEN_EXPIRED
from src.db import crud
from src.db.db import get_db_session
from src.domains.base.models import session_data_var
from src.domains.login.scope.scope_manager import ScopeManager
from src.domains.login.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, BEARER, JWT_ACCESS_TOKEN_EXPIRY_SECONDS, \
    JWT_REFRESH_TOKEN_EXPIRY_DAYS
from src.domains.login.token.models import SessionData, Authentication
from src.domains.login.user.functions import set_user_status
from src.domains.login.user.models import User, UserStatus

security = HTTPBearer()


async def session_login(db, user: User, set_status=False) -> Response:
    """ Login into the session during user login or refresh token renewal. """
    # - Get new access- and refresh tokens (for all roles)
    authentication: Authentication = await get_authentication(db, user.email)
    # - Update refresh token expiration
    user.refresh_token_expiration = authentication.refresh_token_expiration
    if set_status:
        await set_user_status(db, user, target_status=UserStatus.LoggedIn)
    else:
        await crud.upd(db, User, user)
    # - Add the authentication headers to the response
    return add_authorization_headers(authentication)


async def get_authentication(db, email, roles=None) -> Authentication:
    sm = ScopeManager(db, email)
    scopes = await sm.get_user_scopes(roles)
    access_token_expiration = _get_expiration_time(JWT_ACCESS_TOKEN_EXPIRY_SECONDS)
    refresh_token_expiration = _get_expiration_time(JWT_REFRESH_TOKEN_EXPIRY_DAYS)
    access_token = _get_jwt(email, scopes, access_token_expiration)
    refresh_token = _get_jwt(email, scopes, refresh_token_expiration)
    return Authentication(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=BEARER,
        refresh_token_expiration=refresh_token_expiration
    )


def _get_jwt(email, scopes, expiration_time):
    payload = {
        'sub': email,
        'exp': expiration_time,
        'scopes': scopes
    }
    return jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))


def _get_expiration_time(expiration_time_name):
    now = datetime.datetime.now(datetime.timezone.utc)
    if expiration_time_name == JWT_ACCESS_TOKEN_EXPIRY_SECONDS:
        expiration_time = (now + datetime.timedelta(seconds=int(os.getenv(expiration_time_name, 900))))
    elif expiration_time_name == JWT_REFRESH_TOKEN_EXPIRY_DAYS:
        expiration_time = (now + datetime.timedelta(days=int(os.getenv(expiration_time_name, 30))))
    else:
        expiration_time = now
    return expiration_time


def set_session_from_header_token(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> SessionData:
    session_data: SessionData = decode_jwt(credentials.credentials)
    session_data_var.set(session_data)
    return session_data


def decode_jwt(token):
    try:
        payload = jwt.decode(
            token,
            key=os.getenv(JWT_SECRET_KEY),
            algorithms=[os.getenv(JWT_ALGORITHM)],
            verify=True,
            options={'verify_signature': True,
                     'verify_aud': False,
                     'verify_iss': False})
        return SessionData(scopes=payload.get('scopes', []), email=payload.get('sub'))
    except ExpiredSignatureError:
        _raise(detail=MSG_TOKEN_EXPIRED)
    except InvalidTokenError:
        _raise()
    except Exception:
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


def add_authorization_headers(authentication: Authentication, response: Response = Response()):
    response.headers[AUTHORIZATION] = f'{authentication.token_type} {authentication.access_token}'
    response.headers[X_REFRESH_TOKEN] = authentication.refresh_token
    return response


def _raise(security_scopes: SecurityScopes = None, detail=None):
    # Invalidate session
    session_data_var.set(None)
    # Raise
    header_description = f'{BEARER} scope="{security_scopes.scope_str}"' if security_scopes else BEARER
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail or 'Invalid credentials',
        headers={'WWW-Authenticate': header_description})
