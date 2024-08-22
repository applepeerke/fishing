import datetime
import os
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import validate_user, reset_user, invalid_login_attempt, map_user, \
    validate_new_password
from src.domains.login.models import Password, PasswordEncrypted, LoginBase
from src.domains.login.models import Register, ChangePassword, Login, SetPassword
from src.domains.user.functions import send_otp
from src.domains.user.models import User
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.security.crypto import get_hashed_password, verify_password, get_otp_as_number

login = APIRouter()
login_register = APIRouter()
login_register_validate = APIRouter()
login_password_set = APIRouter()
login_password_reset = APIRouter()
login_password_forgot = APIRouter()

password = APIRouter()
password_validate = APIRouter()


@login_register.post('/', response_model=Register)
async def register_user(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    # The user must not already exist.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    if user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user already exists.')
    # Create the one time password as a 5-digit number.
    otp = get_otp_as_number()
    # Mail the otp to the specified address.
    send_otp(payload.email, otp)
    # Insert the user (N.B. password is null yet)
    expired = (datetime.datetime.now(datetime.timezone.utc) +
               datetime.timedelta(minutes=int(int(os.getenv('OTP_EXPIRATION_MINUTES', 10)))))
    user = User(email=payload.email, password=None, otp=otp, expired=expired)
    await crud.add(db, user)
    return Register(email=user.email, otp=user.otp, expired=expired)


@login_register_validate.post('/')
async def register_validate(payload: Register, db: AsyncSession = Depends(get_db_session)):
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
        await invalid_login_attempt(db, user)

    # Success: Reset user
    await reset_user(db, map_user(user), reset_otp=False)


@login.post('/')
async def login_user(payload: Login, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)
    # Validate password
    try:
        password_verify(Password(plain_text=payload.password.get_secret_value(), encrypted_text=user.password))
    except HTTPException:
        await invalid_login_attempt(db, user)
        raise


@login_password_forgot.post('/')
async def password_forgot(payload: LoginBase, db: AsyncSession = Depends(get_db_session)):
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user, allow_blocked=True)
    # Create the one time password as a 5-digit number.
    user.otp = get_otp_as_number()
    user.expired = (datetime.datetime.now(datetime.timezone.utc) +
                    datetime.timedelta(minutes=int(os.getenv('OTP_EXPIRATION_MINUTES', 10))))
    # Mail the otp to the specified address.
    send_otp(payload.email, user.otp)
    # Update the user otp
    await crud.upd(db, User, user.id, map_user(user))


@login_password_set.post('/')
async def password_set(payload: SetPassword, db: AsyncSession = Depends(get_db_session)):
    """ Set the password, this should be done immediately after otp validation """
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=payload.email)
    await validate_user(db, user)

    # a. Verify if the otp is correct
    if not payload.otp or payload.otp != user.otp:
        error_message = f'Incorrect otp. Please try again.'
    # b. Verify the new password
    else:
        error_message = validate_new_password(payload=payload)
    # Fail
    if error_message:
        await invalid_login_attempt(db, user, error_message)
    # Success: Reset the user with the new password
    user.password = get_hashed_password(payload.new_password.get_secret_value())
    user.expired = (datetime.datetime.now(datetime.timezone.utc) +
                    relativedelta(months=os.getenv('PASSWORD_EXPIRATION_MONTHS', 10)))
    await reset_user(db, map_user(user))


@login_password_reset.post('/')
async def password_reset(payload: ChangePassword, db: AsyncSession = Depends(get_db_session)):
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
    await reset_user(db, map_user(user))


@password.post('/', response_model=PasswordEncrypted)
def password_encrypt(payload: Password):
    encrypted_text = get_hashed_password(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@password_validate.post('/')
def password_verify(payload: Password):
    success = verify_password(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    if not success:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)

