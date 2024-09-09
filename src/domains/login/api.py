from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.domains.login.models import Login
from src.domains.login.models import LoginBase
from src.domains.token.functions import create_oauth_token
from src.domains.user.functions import validate_user, evaluate_user_status, invalid_login_attempt, send_otp
from src.domains.user.models import User, UserStatus
from src.db import crud
from src.db.db import get_db_session
from src.session.session import set_session_token
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_salted_hash, verify_hash, get_random_password

login_register = APIRouter()
login_acknowledge = APIRouter()
login_login = APIRouter()


@login_register.post('/')
async def register(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Create the user record. """
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
        expired=get_otp_expiration(),
        status=UserStatus.Inactive
    )
    await crud.add(db, user)
    return {}


@login_acknowledge.get('/')
async def acknowledge(request: Request, db: AsyncSession = Depends(get_db_session)):
    """  Validate email link to get a handshake which expires after a short time. """
    if (not request
            or not request.query_params
            or 'email' not in request.query_params
            or 'token' not in request.query_params):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # Check Email and hashed email from the link.
    username = request.query_params['email']
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=username)
    if not user:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    if not verify_hash(username, request.query_params['token']):
        await invalid_login_attempt(db, user)
    # Acknowledge user.
    await evaluate_user_status(db, user, target_status=UserStatus.Acknowledged)


@login_login.post('/')
async def login(credentials: Login, response: Response, db: AsyncSession = Depends(get_db_session)):
    """ Log in with email and password (not OTP). """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user)
    # Validate credentials.
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await invalid_login_attempt(db, user)
    # Activate user.
    # - Create oauth2 token
    oauth2_token = create_oauth_token(user)
    # - Add authorization header
    response.headers.append(AUTHORIZATION, f'{oauth2_token.token_type} {oauth2_token.access_token}')
    # - Set session token
    set_session_token(response.headers.get(AUTHORIZATION))
    # Update status and audit user.
    await evaluate_user_status(db, user, target_status=UserStatus.Active)

