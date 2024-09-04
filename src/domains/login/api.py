from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from src.domains.token.functions import validate_user, set_user_status, invalid_login_attempt, \
    validate_new_password, get_access_token
from src.domains.login.models import Login, ChangePassword
from src.domains.login.models import Password, PasswordEncrypted, LoginBase
from src.domains.token.models import AccessToken
from src.domains.user.functions import send_otp
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_salted_hash, verify_hash, get_otp

login_register = APIRouter()
login_activate = APIRouter()
login_login = APIRouter()

password_hash = APIRouter()
password_verify = APIRouter()
password_change = APIRouter()
password_reset = APIRouter()
password_forgot = APIRouter()


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
    # Send it in an activation mail
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


@login_activate.get('/')
async def activate(request: Request, db: AsyncSession = Depends(get_db_session)):
    """  Validate email link to get a handshake which expires after a short time. """
    if not request:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # Check Email and hashed email from the link.
    username = request.query_params['email']
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=username)
    if not verify_hash(username, request.query_params['token']):
        await invalid_login_attempt(db, user)
    # Activate user.
    await set_user_status(db, user, target_status=UserStatus.Active)


@login_login.post('/', response_model=AccessToken)
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
    return get_access_token(user)


@password_change.post('/', response_model=AccessToken)
async def change_password(credentials: ChangePassword, db: AsyncSession = Depends(get_db_session)):
    """ Change OTP or password. """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user)
    # a. Verify old password
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await invalid_login_attempt(db, user)
    # b. Validate new password (various kinds of restrictions)
    error_message = validate_new_password(credentials=credentials, old_password_hashed=user.password)
    if error_message:
        await invalid_login_attempt(db, user, error_message)
    # Set new password.
    user.password = get_salted_hash(credentials.new_password.get_secret_value())
    # Activate user.
    await set_user_status(db, user, target_status=UserStatus.Active, new_expiry=True)
    # Return access token.
    return get_access_token(user)


@password_forgot.post('/')
async def forgot_password(credentials: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Send a new activation mail with link and OTP. """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user, forgot_password=True)
    # Reset the user
    await set_user_status(db, user, target_status=UserStatus.Inactive)


@password_hash.post('/', response_model=PasswordEncrypted)
def encrypt(payload: Password):
    """ Hashing. Used for test purposes only. """
    if not payload:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    encrypted_text = get_salted_hash(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@password_verify.post('/')
def validate_hash(payload: Password):
    """ Hash validation. Used for test purposes only. """
    if not payload:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    success = verify_hash(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    if not success:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
