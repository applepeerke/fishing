import os
import datetime

from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status

from src.domains.user.functions import is_valid_password, send_otp, map_user
from src.domains.user.models import UserRead, UserStatus
from src.utils.functions import get_otp_expiration, get_password_expiration
from src.utils.security.crypto import get_random_password, get_hashed_password


from src.domains.user.models import User
from src.utils.db import crud
from src.utils.security.crypto import verify_password

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


async def authenticate_user(db, email: str, password: str) -> User:
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=email)
    if not user or not verify_password(password, user.password):
        raise credentials_exception
    return user


def validate_new_password(payload: BaseModel, old_password_hashed=None):
    detail = None
    new_password_plain_text = payload.new_password.get_secret_value()
    new_password_repeated_plain_text = payload.new_password_repeated.get_secret_value()
    # a. New password is required.
    if not new_password_plain_text:
        detail = f'New password is required.'
    # b. New password repetition must be the same.
    if not detail and not (new_password_plain_text == new_password_repeated_plain_text):
        detail = f'New password must be the same as the repeated one.'
    # c. New password must differ from old one.
    if not detail and old_password_hashed and verify_password(new_password_plain_text, old_password_hashed):
        detail = f'New password must differ from the old one.'
    # d. New password must be valid.
    if not detail and not is_valid_password(new_password_plain_text):
        detail = f'The password is not valid.'
    return detail


async def validate_user(db, user: User, forgot_password=False) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user does not exist.')
    # Blacklisted user
    if user.status == UserStatus.Blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='The user is blacklisted.')
    # Blocked user
    if user.status == UserStatus.Blocked:
        # Set the expiration date if it has not been set already
        if not user.blocked_until:
            user = await set_user_status(db, map_user(user), target_status=UserStatus.Blocked)
        # a. Blocking time is over: reset the user
        if user.blocked_until < datetime.datetime.now(datetime.timezone.utc):
            user = await set_user_status(db, map_user(user), target_status=UserStatus.Active)
        # b. Still blocked. Allow this only when forgot_password is requested.
        elif user.blocked_until > datetime.datetime.now(datetime.timezone.utc) and not forgot_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='The user is blocked. Please try again later.')
    elif user.status != UserStatus.Expired:
        if user.expired and user.expired < datetime.datetime.now(datetime.timezone.utc):
            user = await set_user_status(db, map_user(user), target_status=UserStatus.Expired)
    if user.status == UserStatus.Expired and not forgot_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='The password is expired.')
    return user


async def invalid_login_attempt(db, user: User, error_message=''):
    initial_detail = error_message
    user = map_user(user)

    # Increment fail counter
    user.fail_count = user.fail_count + 1

    # Max. fail attempts reached: block the user.
    if user.fail_count >= int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED', 3)):
        await set_user_status(db, user, target_status=UserStatus.Blocked)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'{initial_detail} The user has been blocked. Please try again later.')
    # Update fail counter
    await crud.upd(db, User, user.id, user)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f'{initial_detail} Please try again.')


async def set_user_status(db, user: UserRead, target_status=None) -> UserRead:
    if target_status == UserStatus.Inactive:
        user = reset_user(user)
        # Create the one time password
        temporary_password = get_random_password()
        user.password = get_hashed_password(temporary_password)
        user.expired = get_otp_expiration()
        # Mail the otp to the specified address.
        send_otp(user.email, temporary_password)
    elif target_status == UserStatus.Active:
        user = reset_user(user)
        user.expired = get_password_expiration()
        user.status = UserStatus.Active
    elif target_status == UserStatus.Blocked:
        user.blocked_until = get_blocked_until()
    # Set status
    if target_status:
        user.status = target_status
    return await crud.upd(db, User, user.id, user)


def get_blocked_until():
    minutes = int(os.getenv('LOGIN_BLOCK_MINUTES', 10))
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)


def reset_user(user) -> UserRead:
    user.blocked_until = None
    user.fail_count = 0
    user.authentication_token = None
    return user
