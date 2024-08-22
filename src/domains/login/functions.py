import os
import datetime

from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status

from src.domains.user.functions import is_valid_password
from src.domains.user.models import User, UserRead, UserStatus
from src.utils.db import crud
from src.utils.security.crypto import verify_password


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


async def validate_user(db, user: User, allow_blocked=False) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user does not exist.')
    # Blacklisted user
    if user.status == UserStatus.Blacklisted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user blacklisted.')
    # Blocked user
    if user.blocked_until:
        # a. Blocking time is over: reset the user
        if user.blocked_until < datetime.datetime.now(datetime.timezone.utc):
            user = await reset_user(db, map_user(user))
        # b. Still blocked. Allow this only when forgot_password is requested.
        elif user.blocked_until > datetime.datetime.now(datetime.timezone.utc) and not allow_blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='The user is blocked. Please try again later.')
    return user


async def reset_user(db, user: UserRead, reset_otp=True) -> UserRead:
    user = reset_user_attributes(user, reset_otp)
    return await crud.upd(db, User, user.id, user)


async def invalid_login_attempt(db, user: User, error_message=''):
    initial_detail = error_message
    user = map_user(user)

    # Increment fail counter
    user.fail_count = user.fail_count + 1

    # Max. fail attempts reached: block the user.
    if user.fail_count >= int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED', 3)):
        minutes = int(os.getenv('LOGIN_BLOCK_MINUTES', 10))
        user = reset_user_attributes(user)
        user.blocked_until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes))
        await crud.upd(db, User, user.id, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'{initial_detail}The user has been blocked. Please try again later.')
    # Update fail counter
    await crud.upd(db, User, user.id, user)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f'{initial_detail}Invalid login attempt. Please try again.')


def reset_user_attributes(user: UserRead, reset_otp=False) -> UserRead:
    user.blocked_until = None
    user.fail_count = 0
    if reset_otp:
        user.otp = None
        user.expired = None
    user.authentication_token = None
    return user


def map_user(user: User) -> UserRead:
    """ Map User (SQLAlchemy) to UserRead (pydantic) (except password) """
    user_read = UserRead(
        id=user.id,
        email=user.email,
        authentication_token=user.authentication_token,
        status=user.status,
        otp=user.otp,
        expired=user.expired,
        fail_count=user.fail_count,
        blocked_until=user.blocked_until,
    )
    # This must be done afterwards
    user_read.password = user.password
    return user_read
