from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from starlette.requests import Request

from src.constants import AUTHORIZATION
from src.domains.base.models import session_token_var
from src.domains.scope.scope_manager import ScopeManager
from src.domains.token.functions import get_session_data_from_token, create_authentication_token
from src.domains.token.models import SessionData, AuthenticationToken

security = HTTPBearer()


async def has_access(request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> SessionData | None:
    """ Dependency is for OpenAPI docs (test) """
    await authenticate_session(request)
    return session_token_var.get(None)


async def authenticate_session(request: Request):
    """ Middleware"""
    # Set session token
    # Extract the token part after "Bearer "
    authorization_header = request.headers.get(AUTHORIZATION)
    authentication_token = authorization_header.split(" ")[1] if authorization_header else None
    await set_session_user(AuthenticationToken(token=authentication_token), db=request.state.db)


def authorize_session(scopes: dict = None):
    token_data = session_token_var.get(None)
    token_data.scopes = scopes
    session_token_var.set(token_data)


async def create_authenticated_session(email, scopes, db) -> AuthenticationToken:
    """ After logging in and from tests """
    # - Create session token (oauth2)
    authentication_token: AuthenticationToken = create_authentication_token(email, scopes)
    # - Persist session token in session
    await set_session_user(authentication_token, db)
    return authentication_token


async def set_session_user(authentication_token=None, db=None):
    """ Set the insensitive data (email) from the encrypted token as plain text in a context variable """
    # Todo: FAstAPI scopes
    security_scopes = SecurityScopes()
    session_data: SessionData = await get_session_data_from_token(security_scopes, authentication_token, db) \
        if authentication_token else None
    session_token_var.set(session_data)


async def create_authorization_header_in_response(db, email, response):
    """ After logging in """
    sm = ScopeManager(db, email)
    scopes = await sm.get_user_scopes()
    oauth2_token = await create_authenticated_session(email, scopes, db)
    # - Add authorization header
    response.headers.append(AUTHORIZATION, f'{oauth2_token.token_type} {oauth2_token.token}')


async def delete_session(request: Request):
    # Remove Authorization header
    request_headers = dict(request.scope['headers'])
    request.scope['headers'] = [(k, v) for k, v in request_headers.items() if k != b'authorization']
    # Remove session user (TokenData)
    await set_session_user(authentication_token=None)

