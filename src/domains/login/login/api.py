from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import EMAIL, TOKEN, AUTHORIZATION
from src.db import crud
from src.db.db import get_db_session
from src.domains.base.models import session_data_var
from src.domains.login.login.models import Login
from src.domains.login.login.models import LoginBase
from src.domains.login.scope.scope_manager import ScopeManager
from src.domains.login.token.functions import get_authorization, is_authorized
from src.domains.login.token.models import Authorization
from src.domains.login.user.functions import validate_user, set_user_status, send_otp
from src.domains.login.user.models import User, UserStatus
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_salted_hash, verify_hash, get_random_password

login_register = APIRouter()
login_acknowledge = APIRouter()
login_login = APIRouter()
login_logout = APIRouter()


@login_register.post('/')
async def register(
        payload: LoginBase,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Create the user record.
    """
    if not payload:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must not already exist.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    if user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user already exists.')
    # Create a random secret password (OTP)
    otp = get_random_password()
    # Send it in an acknowledgement mail
    send_otp(payload.email, otp)
    # Insert the user with a short expiration
    user = User(
        email=payload.email,
        password=get_salted_hash(otp),
        expiration=get_otp_expiration(),
        status=UserStatus.Inactive
    )
    await crud.add(db, user)
    return {}


@login_acknowledge.get('/')
async def acknowledge(
        request: Request,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Validate email link to get a handshake which expires after a short time.
    """
    if (not request
            or not request.query_params
            or EMAIL not in request.query_params
            or TOKEN not in request.query_params):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # Check Email and hashed email from the link.
    username = request.query_params[EMAIL]
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=username)
    if not user:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    if not verify_hash(username, request.query_params[TOKEN]):
        await set_user_status(db, user, 'Invalid login attempt.')
    # Acknowledge user.
    await set_user_status(db, user, target_status=UserStatus.Acknowledged)


@login_login.post('/')
async def login(
        credentials: Login,
        response: Response,
        db: AsyncSession = Depends(get_db_session)
):
    """
    Log in with email and password (not OTP).
    """
    # Validation
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # - The user must be active and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user, minimum_status=UserStatus.Active)
    # - Validate credentials.
    if not credentials.password.get_secret_value() == credentials.password_repeat.get_secret_value():
        await set_user_status(db, user, 'Repeated password must be the same.')
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await set_user_status(db, user, 'Invalid login attempt.')

    # Log in
    # - Get user scopes for all roles
    scope_manager = ScopeManager(db, user.email)
    scopes = await scope_manager.get_user_scopes()
    # - Add the authorization header to the response
    authorization: Authorization = get_authorization(user.email, scopes)
    response.headers.append(AUTHORIZATION, f'{authorization.token_type} {authorization.token}')
    # Log in the user.
    await set_user_status(db, user, target_status=UserStatus.LoggedIn)


@login_logout.post('/')
async def logout(
        response: Response,
        login_base: LoginBase,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['login_delete'])]
):
    """ Logout with email """
    if not login_base:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    # The user must exist and be logged in.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=login_base.email)
    if not user or user.status != UserStatus.LoggedIn:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='The user has not the right status.')

    # a. Delete session authorization.
    # Invalidate session
    session_data_var.set(None)
    # b. Remove response authorization.
    if AUTHORIZATION in response.headers:
        del response.headers[AUTHORIZATION]
    # c. Update db status.
    await set_user_status(db, user, target_status=UserStatus.Active)
