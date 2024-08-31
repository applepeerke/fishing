import os


from fastapi import HTTPException
from starlette import status

from src.domains.user.models import User, UserRead
from src.utils.functions import find_filename_path
from src.utils.mail.mail import send_mail


def send_otp(email, otp):
    template_path = find_filename_path(os.getenv('OTP_TEMPLATE_NAME'))
    mail_from = os.getenv('OTP_MAIL_FROM')
    if not os.getenv('DEBUG', False) and (not template_path or not mail_from):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Invalid settings. Mail with otp could not be sent.')
    # Populate substitution variables like OTP and the link to receive_otp endpoint.
    substitutions = {
                '*APP_NAME*': os.getenv('APP_NAME'),
                '*OTP_URL*': os.getenv('OTP_URL'),
                '*OTP*': otp
            }
    # Send email
    try:
        send_mail(template_path, 'Registration code', mail_from, [email], substitutions)
    except ConnectionRefusedError as e:
        if os.getenv('DEBUG', False):
            return
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


def is_valid_password(password) -> bool:
    """ Precondition: pydantic has checked already on type, min_length and max_length """
    # must contain upper, lower, number, special
    d = {}
    for c in str(password):
        if c.islower():
            d['LC'] = True
        elif c.isupper():
            d['UC'] = True
        elif c.isnumeric():
            d['number'] = True
        elif c != ' ':
            d['special'] = True
    return len(d) == 4


def map_user(user: User) -> UserRead:
    """ Map User (SQLAlchemy) to UserRead (pydantic) """
    user_read = UserRead(
        id=user.id,
        email=user.email,
        authentication_token=user.authentication_token,
        status=user.status,
        expired=user.expired,
        fail_count=user.fail_count,
        blocked_until=user.blocked_until,
    )
    # This must be done afterward
    user_read.password = user.password
    return user_read
