import os

from fastapi import HTTPException
from starlette import status

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
        elif c is not ' ':
            d['special'] = True
    return len(d) == 4
