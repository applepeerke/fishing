from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

from src.constants import AUTHORIZATION
from src.domains.base.models import session_token_var
from src.domains.token.functions import get_session_token_data
from src.domains.token.models import SessionTokenData

security = HTTPBearer()


def set_session(request: Request):
    """ Middleware"""
    # Set session token
    set_session_token(request.headers.get(AUTHORIZATION))


def delete_session(request: Request):
    # Remove Authorization header
    headers = dict(request.scope['headers'])
    request.scope['headers'] = [(k, v) for k, v in headers.items() if k != b'authorization']
    # Remove session token
    set_session_token(None)


def set_session_token(authorization_header=None):
    if authorization_header:
        # Extract the token part after "Bearer "
        session_token = authorization_header.split(" ")[1]
        token_data: SessionTokenData = get_session_token_data(session_token)
        # Set the user in the context variable
        session_token_var.set(token_data)
    else:
        session_token_var.set(None)


async def has_access(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> SessionTokenData | None:
    """ Dependency is for OpenAPI docs only (for now) """
    return session_token_var.get(None)
