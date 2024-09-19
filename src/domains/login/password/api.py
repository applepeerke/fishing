from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import crud
from src.db.db import get_db_session
from src.domains.login.password.functions import validate_new_password
from src.domains.login.password.models import ChangePassword
from src.domains.login.password.models import Password, PasswordEncrypted, ChangePasswordBase
from src.domains.login.user.functions import validate_user, set_user_status
from src.domains.login.user.models import User, UserStatus
from src.utils.security.crypto import get_salted_hash, verify_hash

password_hash = APIRouter()
password_verify = APIRouter()
password_change = APIRouter()
password_forgot = APIRouter()


@password_change.post('/')
async def change_password(
        credentials: ChangePassword,
        db: AsyncSession = Depends(get_db_session)
):
    """ Change OTP or password. """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist and be valid.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user, minimum_status=UserStatus.Acknowledged)
    # a. Verify old password
    if not verify_hash(credentials.password.get_secret_value(), user.password):
        await set_user_status(db, user, 'Invalid login attempt.')
    # b. Validate new password (various kinds of restrictions)
    error_message = validate_new_password(credentials=credentials, old_password_hashed=user.password)
    if error_message:
        await set_user_status(db, user, error_message)
    # Set new password.
    user.password = get_salted_hash(credentials.new_password.get_secret_value())
    # Activate user.
    await set_user_status(db, user, target_status=UserStatus.Active, renew_expiration=True)


@password_forgot.post('/')
async def forgot_password(
        credentials: ChangePasswordBase,
        db: AsyncSession = Depends(get_db_session)
):
    """ Send a new acknowledge mail with link and OTP. """
    if not credentials:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    # The user must already exist. User may be blocked, not blacklisted.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=credentials.email)
    user = await validate_user(db, user, forgot_password=True)
    # Inactivate the user
    await set_user_status(db, user, target_status=UserStatus.Inactive, forgot_password=True)


@password_hash.post('/', response_model=PasswordEncrypted)
def encrypt(
        payload: Password
):
    """ Hashing. Used for test purposes only. """
    if not payload:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    encrypted_text = get_salted_hash(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@password_verify.post('/')
def validate_hash(
        payload: Password
):
    """ Hash validation. Used for test purposes only. """
    if not payload:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    success = verify_hash(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    if not success:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
