import datetime
import os
from typing import Annotated

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.password.models import ChangePassword
from src.domains.token.constants import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, BEARER
from src.domains.token.models import AccessTokenData, OAuthAccessToken
from src.domains.user.functions import send_otp, map_user
from src.domains.user.models import User
from src.domains.user.models import UserRead, UserStatus
from src.db import crud
from src.db.db import get_db_session
from src.utils.functions import get_otp_expiration, get_password_expiration
from src.utils.security.crypto import get_random_password, get_salted_hash, is_valid_password
from src.utils.security.crypto import verify_hash

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Invalid login attempt',
    headers={'WWW-Authenticate': 'Bearer'}
)

security = HTTPBearer()


def get_oauth_access_token(user) -> OAuthAccessToken:
    """ The OAuth2 scheme requires a JSON with "access_token" and "token_type". """
    payload = {
        "sub": user.email,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=int(os.getenv(JWT_EXPIRY_MINUTES, 15)))}
    jwt_token = jwt.encode(
        payload=payload,
        key=str(os.getenv(JWT_SECRET_KEY)),
        algorithm=os.getenv(JWT_ALGORITHM))
    return OAuthAccessToken(access_token=jwt_token, token_type=BEARER)


async def has_access(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> AccessTokenData:
    """ ToDo: Tests if the token is valid, not if the user is the one in the token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            key=os.getenv(JWT_SECRET_KEY),
            algorithms=[os.getenv(JWT_ALGORITHM)],
            verify=True,
            options={"verify_signature": True,
                     "verify_aud": False,
                     "verify_iss": False})
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        return AccessTokenData(user_email=email)
    except InvalidTokenError:
        raise credentials_exception


def _get_token_data(access_token) -> AccessTokenData:
    try:
        payload = jwt.decode(
            access_token, os.getenv(JWT_SECRET_KEY), algorithms=[os.getenv(JWT_ALGORITHM)], verify=True)
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        return AccessTokenData(user_email=email)
    except InvalidTokenError:
        raise credentials_exception


async def get_user_from_token(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        access_token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    # Get token data
    token_data = _get_token_data(access_token)

    # Get the token user
    user = await crud.get_one_where(
        db, User,
        att_name=User.email,
        att_value=token_data.user_email)
    if not user:
        raise credentials_exception
    return user


def validate_new_password(credentials: ChangePassword, old_password_hashed=None) -> str | None:
    """ Change password extra validation """
    detail = None
    new_password_plain_text = credentials.new_password.get_secret_value()
    new_password_repeated_plain_text = credentials.new_password_repeated.get_secret_value()
    # a. New password is required.
    if not new_password_plain_text:
        detail = f'New password is required.'
    # b. New password repetition must be the same.
    if not detail and not (new_password_plain_text == new_password_repeated_plain_text):
        detail = f'New password must be the same as the repeated one.'
    # c. New password must differ from old one.
    if not detail and old_password_hashed and verify_hash(new_password_plain_text, old_password_hashed):
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
    # Forgot password: Do not validate Blocked/Expired.
    if forgot_password:
        return user
    # Blocked user
    if user.status == UserStatus.Blocked:
        # Set/check the expiration date
        user = await set_user_status(db, user, target_status=UserStatus.Blocked)
        # Still blocked: error
        if user.status == UserStatus.Blocked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='The user is blocked. Please try again later.')
    elif user.status != UserStatus.Expired:
        if user.expired and user.expired < datetime.datetime.now(datetime.timezone.utc):
            user = await set_user_status(db, user, target_status=UserStatus.Expired)
    if user.status == UserStatus.Expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='The password is expired.')
    return user


async def invalid_login_attempt(db, user: User, error_message=None):
    """ Always raise an exception. """
    if not user:  # Not registered yet
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    prefix = error_message or 'Invalid login attempt.'

    # Increment fail counter
    user.fail_count = user.fail_count + 1

    # Max. fail attempts reached: block the user.
    if user.fail_count >= int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED', 3)):
        await set_user_status(db, user, target_status=UserStatus.Blocked)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'{prefix} The user has been blocked. Please try again later.')
    # Update fail counter
    await crud.upd(db, User, map_user(user))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f'{prefix} Please try again.')


async def set_user_status(db, user: User, target_status=None, new_expiry=False):
    user = get_user_status(user, target_status, new_expiry)
    return await crud.upd(db, User, map_user(user))


def get_user_status(user: User, target_status=None, new_expiry=False) -> User:
    if target_status == UserStatus.Inactive:
        user = reset_user_attributes(user)
        # Create the one time password (not hashed, 10 long)
        otp = get_random_password()
        user.password = get_salted_hash(otp)
        user.expired = get_otp_expiration()  # Short ttl
        # Mail the OTP to the specified address.
        send_otp(user.email, otp)
    elif target_status == UserStatus.Acknowledged:
        pass
    elif target_status == UserStatus.Active:
        user = reset_user_attributes(user)
        if new_expiry:
            user.expired = get_password_expiration()  # Long ttl
    elif target_status == UserStatus.Blocked:  # max fail_count reached
        if not user.blocked_until:
            user.blocked_until = get_blocked_until()
        # a. Blocking time is over: reactivate the user
        if user.blocked_until < datetime.datetime.now(datetime.timezone.utc):
            user = reset_user_attributes(user)
            target_status = UserStatus.Active
    # Set status
    if target_status:
        user.status = target_status
    return user


def get_blocked_until():
    minutes = int(os.getenv('LOGIN_BLOCK_MINUTES', 10))
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)


def reset_user_attributes(user) -> UserRead:
    user.blocked_until = None
    user.fail_count = 0
    user.authentication_token = None
    return user
