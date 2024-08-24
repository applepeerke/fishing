import datetime
from fastapi import APIRouter, Depends, HTTPException
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import validate_user, reset_user, invalid_login_attempt, map_user, \
    validate_new_password
from src.domains.login.models import Password, PasswordEncrypted, LoginBase
from src.domains.login.models import Register, ChangePassword, Login, SetPassword
from src.domains.user.functions import send_otp
from src.domains.user.models import User, UserStatus, UserRead
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import get_otp_expiration, get_password_expiration
from src.utils.security.crypto import get_hashed_password, verify_password, get_otp_as_number

login_login = APIRouter()
login_register = APIRouter()
login_initialize = APIRouter()
login_activate = APIRouter()
login_password_set = APIRouter()
login_change_password = APIRouter()
login_forgot_password = APIRouter()

password = APIRouter()
password_validate = APIRouter()


@login_register.post('/', response_model=Register)
async def register(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """  Target status: 10 (Registered): User record created with email. """
    # The user must not already exist.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    if user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user already exists.')
    # Create the one time password as a 5-digit number.
    otp = get_otp_as_number()
    # Mail the otp to the specified address.
    send_otp(payload.email, otp)
    # Insert the user (N.B. password is null yet)
    expired = get_otp_expiration()
    user = User(email=payload.email, password=None, otp=otp, expired=expired, status=UserStatus.Registered)
    await crud.add(db, user)
    return Register(email=user.email, otp=user.otp, expired=expired)


@login_initialize.post('/', response_model=UserRead)
async def initialize(payload: Register, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 20 (Initialized): OTP validated. """
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)
    # The otp must not be expired.
    if not user.expired or (user.expired < datetime.datetime.now(datetime.timezone.utc)):
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content='The one time password has expired. Please register again.')

    # Fail: the otp in the user input <> server-generated otp.
    if not payload.otp or payload.otp == 0 or payload.otp != user.otp:
        # Fail: increment failure attempt.
        return await invalid_login_attempt(db, user)

    # Success: Initialize user
    user.status = UserStatus.Initialized
    return await reset_user(db, map_user(user))


@login_activate.post('/', response_model=UserRead)
async def activate(payload: SetPassword, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 30 (Active): Password validated. """
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)

    # a. Verify if the otp is correct
    if not payload.otp or payload.otp != user.otp:
        return await invalid_login_attempt(db, user, 'Incorrect otp. Please try again.')
    # b. Verify the new password
    else:
        error_message = validate_new_password(payload=payload)
        if error_message:
            return await invalid_login_attempt(db, user, error_message)
    # Success: Activate the user with the password
    user.password = get_hashed_password(payload.new_password.get_secret_value())
    user.expired = get_password_expiration()
    user.status = UserStatus.Active
    return await reset_user(db, map_user(user))


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


@login_forgot_password.post('/', response_model=UserRead)
async def forgot_password(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Target status: 10 (Registered): New OTP sent. """
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user, allow_blocked=True)
    # Create the one time password as a 5-digit number.
    user.otp = get_otp_as_number()
    user.expired = get_otp_expiration()
    # Mail the otp to the specified address.
    send_otp(payload.email, user.otp)
    # Update the user otp
    return await crud.upd(db, User, user.id, map_user(user))


@login_change_password.post('/', response_model=UserRead)
async def change_password(payload: ChangePassword, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)

    # a. Verify old password
    if not verify_password(
            plain_text=payload.old_password.get_secret_value(),
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
    return await reset_user(db, map_user(user))


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

