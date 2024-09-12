from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

from src.constants import AUTHORIZATION
from src.domains.base.models import session_token_var
from src.domains.token.functions import get_session_token_data, create_session_token
from src.domains.token.models import SessionTokenData, SessionToken

security = HTTPBearer()


async def has_access(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> SessionTokenData | None:
    """ Dependency is for OpenAPI docs (test) """
    return session_token_var.get(None)


def authenticate_session(request: Request):
    """ Middleware"""
    # Set session token
    # Extract the token part after "Bearer "
    authorization_header = request.headers.get(AUTHORIZATION)
    session_token = authorization_header.split(" ")[1] if authorization_header else None
    set_session_user(session_token)


def create_authenticated_session(user) -> SessionToken:
    """ After logging in and from tests """
    # - Create session token (oauth2)
    session_token = create_session_token(user)
    # - Persist session token in session
    set_session_user(session_token.token)
    return session_token


def set_session_user(session_token=None):
    """ Set the plain text user-data from the encrypted token in a context variable """
    token_data: SessionTokenData = get_session_token_data(session_token) if session_token else None
    session_token_var.set(token_data)


def create_response_session_token(user, response):
    """ After logging in """
    oauth2_token = create_authenticated_session(user)
    # - Add authorization header
    response.headers.append(AUTHORIZATION, f'{oauth2_token.token_type} {oauth2_token.token}')


def delete_session(request: Request):
    # Remove Authorization header
    request_headers = dict(request.scope['headers'])
    request.scope['headers'] = [(k, v) for k, v in request_headers.items() if k != b'authorization']
    # Remove session user (TokenData)
    set_session_user(None)

