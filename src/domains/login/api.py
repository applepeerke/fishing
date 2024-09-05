from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from src.domains.login.models import Login
from src.domains.login.models import LoginBase
from src.domains.token.functions import validate_user, set_user_status, invalid_login_attempt, \
    get_oauth_access_token
from src.domains.token.models import OAuthAccessToken
from src.domains.user.functions import send_otp
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_salted_hash, verify_hash, get_otp

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
    otp = get_otp()
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
    await set_user_status(db, user, target_status=UserStatus.Acknowledged)


@login_login.post('/', response_model=OAuthAccessToken)
async def login(credentials: Login, db: AsyncSession = Depends(get_db_session)):
    """ Log in with email and password (not OTP). """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user)
    # Validate credentials
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await invalid_login_attempt(db, user)
    # Activate user.
    await set_user_status(db, user, target_status=UserStatus.Active)
    # Return access token.
    return get_oauth_access_token(user)
