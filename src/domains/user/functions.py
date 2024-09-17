import datetime
import os

from fastapi import HTTPException
from starlette import status

from src.db import crud
from src.domains.user.models import User, UserRead, UserStatus
from src.utils.functions import find_filename_path, is_debug_mode, get_otp_expiration, get_password_expiration
from src.utils.mail.mail import send_mail
from src.utils.security.crypto import get_salted_hash, get_random_password


def send_otp(email, otp):
    template_path = find_filename_path(os.getenv('OTP_TEMPLATE_NAME'))
    mail_from = os.getenv('OTP_MAIL_FROM')
    if not os.getenv('DEBUG', False) and (not template_path or not mail_from):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Invalid settings. Mail with otp could not be sent.')
    # Populate substitution variables like OTP and the link to receive_otp endpoint.
    substitutions = {
                '*APP_NAME*': os.getenv('APP_NAME'),
                '*OTP_URL*': f'{os.getenv('OTP_URL')}?email={email}&token={get_salted_hash(email)}',
                '*OTP*': otp
            }
    # Send email
    try:
        send_mail(template_path, 'Registration code', mail_from, [email], substitutions)
    except ConnectionRefusedError as e:
        if is_debug_mode():
            return
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def validate_user(db, user: User, forgot_password=False, minimum_status: int = 0) -> User:
    # a. Validation
    if not user:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user does not exist.')
    #   - Blacklisted user
    if user.status == UserStatus.Blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='The user is blacklisted.')

    # b. Forgot password clicked: Do not set to Blocked/Expired.
    if forgot_password:
        return user

    # c. Evaluate blocked/expired
    #   - Blocked user.
    if user.status == UserStatus.Blocked:
        user = await set_user_status(db, user, target_status=UserStatus.Blocked)
    #   - Expired password.
    if user.status != UserStatus.Blocked:
        user = await set_user_status(db, user, minimum_status=minimum_status)

    return user


async def set_user_status(
        db, user: User, error_message=None, target_status=None, renew_expiration=False, forgot_password=False,
        minimum_status=0) -> User:

    if not user or user.status < minimum_status:  # Not registered yet
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='The user has not the right status.')

    update_fail_count = False
    if not forgot_password:
        # a. Optionally override target status.
        #    Blocked
        #   - Invalid login attempt
        if error_message:
            user.fail_count = user.fail_count + 1
            update_fail_count = True
            # Max. fail attempts reached: block the user.
            if user.fail_count >= int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED', 3)):
                target_status = UserStatus.Blocked
                error_message = f'{error_message} The user has been blocked. Please try again later.'

        #   - Blocking time is over: reactivate the user
        if user.blocked_until and user.blocked_until < datetime.datetime.now(datetime.timezone.utc):
            target_status = UserStatus.Active

        #   Expired
        #   - Expiration time reached
        if user.expiration and user.expiration < datetime.datetime.now(datetime.timezone.utc):
            if user.status == UserStatus.Acknowledged:
                error_message = 'The temporary password has expired. Please register again.'
            else:
                target_status = UserStatus.Expired
                error_message = 'The password is expired.'

    # c. Handle error
    if error_message:
        if update_fail_count:
            await update_user_status(db, user, target_status, renew_expiration)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_message)

    # Still blocked: error
    if target_status == user.status == UserStatus.Blocked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='The user is blocked. Please try again later.')

    # Update
    return await update_user_status(db, user, target_status, renew_expiration)


async def update_user_status(db, user, target_status, renew_expiration):
    user = set_user_status_related_attributes(user, target_status, renew_expiration=renew_expiration)
    return await crud.upd(db, User, user)


def set_user_status_related_attributes(user: User, target_status=None, renew_expiration=False) -> User:
    if not target_status or (user.status == target_status and not renew_expiration):
        return user  # Nothing to do

    if target_status == UserStatus.Inactive:
        user = _reset_user_attributes(user)
        # Create the one time password (not hashed, 10 long)
        otp = get_random_password()
        user.password = get_salted_hash(otp)
        user.expiration = get_otp_expiration()  # Short ttl
        # Mail the OTP to the specified address.
        send_otp(user.email, otp)
    elif target_status == UserStatus.Acknowledged:
        pass
    elif target_status in (UserStatus.Active, UserStatus.LoggedIn):
        user = _reset_user_attributes(user)
        if renew_expiration:
            user.expiration = get_password_expiration()  # Long ttl
    elif target_status == UserStatus.Blocked:  # max fail_count reached
        if not user.blocked_until:
            user.blocked_until = _get_blocked_until()

    user.status = target_status
    return user


def _get_blocked_until():
    minutes = int(os.getenv('LOGIN_BLOCK_MINUTES', 10))
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)


def _reset_user_attributes(user) -> UserRead:
    user.blocked_until = None
    user.fail_count = 0
    return user
