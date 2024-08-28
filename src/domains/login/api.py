from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import validate_user, set_user_status, invalid_login_attempt, map_user, \
    validate_new_password
from src.domains.login.models import Password, PasswordEncrypted, LoginBase
from src.domains.login.models import Login, SetPassword
from src.domains.user.functions import send_otp
from src.domains.user.models import User, UserStatus, UserRead
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_hashed_password, verify_password, get_random_password

login_login = APIRouter()
login_register = APIRouter()
login_activate = APIRouter()
login_password_set = APIRouter()
login_password_reset = APIRouter()
login_password_forgot = APIRouter()

password = APIRouter()
password_validate = APIRouter()


@login_register.post('/', response_model=LoginBase)
async def register(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """  Target status: 10 (Inactive): User record created with email. """
    # The user must not already exist.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    if user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user already exists.')
    # Create the one time password.
    otp = get_random_password()
    # Mail the otp to the specified address.
    send_otp(payload.email, otp)
    # Insert the user (N.B. password is null yet)
    expired = get_otp_expiration()
    user = User(email=payload.email, password=otp, expired=expired, status=UserStatus.Inactive.value)
    await crud.add(db, user)
    return LoginBase(email=user.email)


@login_activate.post('/', response_model=UserRead)
async def activate(payload: SetPassword, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 20 (Active): Password validated. """
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)

    # Verify the new password
    error_message = validate_new_password(payload=payload)
    if error_message:
        return await invalid_login_attempt(db, user, error_message)
    # Success: Activate the user and set the new password
    user.password = get_hashed_password(payload.new_password.get_secret_value())
    return await set_user_status(db, map_user(user), target_status=UserStatus.Active.value)


@login_login.post('/')
async def login(payload: Login, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)
    # Validate password
    try:
        validate_password(Password(plain_text=payload.password.get_secret_value(), encrypted_text=user.password))
    except HTTPException:
        await invalid_login_attempt(db, user)
        raise


@login_password_set.post('/', response_model=UserRead)
async def set_password(payload: SetPassword, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)

    # a. Verify old password
    if not verify_password(
            plain_text=payload.password.get_secret_value(),
            hashed_password=user.password):
        error_message = 'Incorrect existing password.'
    # b. Validate new password (various kinds of restrictions)
    else:
        error_message = validate_new_password(payload=payload, old_password_hashed=user.password)

    # Fail
    if error_message:
        await invalid_login_attempt(db, user, error_message)

    # Success: Set new password
    user.password = get_hashed_password(payload.new_password.get_secret_value())
    return await set_user_status(db, map_user(user), target_status=UserStatus.Active.value)


@login_password_forgot.post('/', response_model=UserRead)
async def forgot_password(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 10 (Inactive): New OTP sent. """
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user, forgot_password=True)
    # Reset the user
    return await set_user_status(db, map_user(user), target_status=UserStatus.Inactive.value)


@password.post('/', response_model=PasswordEncrypted)
def encrypt_password(payload: Password):
    encrypted_text = get_hashed_password(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@password_validate.post('/')
def validate_password(payload: Password):
    success = verify_password(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    if not success:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

