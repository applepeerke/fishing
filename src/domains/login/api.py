from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request

from src.domains.authentication.functions import validate_user, set_user_status, invalid_login_attempt, map_user, \
    validate_new_password
from src.domains.login.models import Login, ChangePassword
from src.domains.login.models import Password, PasswordEncrypted, LoginBase
from src.domains.user.functions import send_otp
from src.domains.user.models import User, UserStatus, UserRead
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


@login_register.post('/', response_model=LoginBase)
async def register(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """  Target status: 10 (Inactive): User record created with email. """
    # The user must not already exist.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    if user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user already exists.')
    # Create a random secret password (OTP)
    otp = get_otp()
    # Send it in an activation mail
    send_otp(payload.email, otp)
    # Set expiration (short ttl)
    expired = get_otp_expiration()
    # Insert the user
    user = User(email=payload.email, password=get_salted_hash(otp), expired=expired, status=UserStatus.Inactive)
    await crud.add(db, user)
    return LoginBase(email=user.email)


@login_activate.get('/')
async def activate(request: Request):
    """  Validate OTP from request parameters. Redirect to Change password. """
    if not verify_hash(
            plain_text=request.query_params['email'],
            hashed_password=request.query_params['token']
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


@password_change.post('/', response_model=UserRead)
async def change_password(payload: ChangePassword, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    user = await validate_user(db, user)



    error_message = None
    # a. Verify old password
    #    N.B. If user is inactive, the password is not validated.
    #    This method is called internally then from activate_user.
    if user.status != UserStatus.Inactive and not verify_hash(
            plain_text=payload.password.get_secret_value(),
            hashed_password=user.password):
        error_message = 'Incorrect existing password.'
    # b. Validate new password (various kinds of restrictions)
    if not error_message:
        error_message = validate_new_password(payload=payload, old_password_hashed=user.password)

    # Fail
    if error_message:
        await invalid_login_attempt(db, user, error_message)

    # Success: Set new password
    user.password = get_salted_hash(payload.new_password.get_secret_value())
    return await set_user_status(db, map_user(user), target_status=UserStatus.Active)


@login_login.post('/')
async def login(payload: Login, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    user = await validate_user(db, user)
    # Validate password
    try:
        validate_password(Password(plain_text=payload.password.get_secret_value(), encrypted_text=user.password))
    except HTTPException:
        await invalid_login_attempt(db, user, 'The password is not valid.')
        raise


@password_forgot.post('/', response_model=UserRead)
async def forgot_password(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 10 (Inactive): New OTP sent. """
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    user = await validate_user(db, user, forgot_password=True)
    # Reset the user
    return await set_user_status(db, map_user(user), target_status=UserStatus.Inactive)


@password_hash.post('/', response_model=PasswordEncrypted)
def encrypt_password(payload: Password):
    encrypted_text = get_salted_hash(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@password_verify.post('/')
def validate_password(payload: Password):
    success = verify_hash(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    if not success:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
