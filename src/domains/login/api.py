from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import EMAIL, TOKEN
from src.db import crud
from src.db.db import get_db_session
from src.domains.login.models import Login
from src.domains.login.models import LoginBase
from src.domains.user.functions import validate_user, set_user_status, send_otp
from src.domains.user.models import User, UserStatus
from src.session.session import create_response_session_token
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
        expiration=get_otp_expiration(),
        status=UserStatus.Inactive
    )
    await crud.add(db, user)
    return {}


@login_acknowledge.get('/')
async def acknowledge(request: Request, db: AsyncSession = Depends(get_db_session)):
    """  Validate email link to get a handshake which expires after a short time. """
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
async def login(credentials: Login, response: Response, db: AsyncSession = Depends(get_db_session)):
    """ Log in with email and password (not OTP). """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must be active and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user, minimum_status=UserStatus.Active)
    # Validate credentials.
    if not credentials.password.get_secret_value() == credentials.password_repeat.get_secret_value():
        await set_user_status(db, user, 'Repeated password must be the same.')
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await set_user_status(db, user, 'Invalid login attempt.')
    # Log in the user.
    await set_user_status(db, user, target_status=UserStatus.LoggedIn)
    # Create session token and update the response
    create_response_session_token(user, response)
