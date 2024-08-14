import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.models import Register
from src.domains.user.models import User, UserRead, UserCreate
from src.general.models import get_delete_response, StatusResponse
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import find_filename_path
from src.utils.mail.mail import send_mail
from src.utils.security.crypto import get_otp_as_number

register = APIRouter(prefix='user')


@register.post('/', response_model=UserRead)
async def register_user(regist: Register, db: AsyncSession = Depends(get_db_session)):
    # The user must not already exist.
    obj = await crud.get_one_where(db, User, att_name=User.email, att_value=register.email)
    if obj:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f'The user already exists.')
    # Get the one time password as a 5-digit number
    otp = get_otp_as_number()
    template_path = find_filename_path(os.getenv('OTP_TEMPLATE_NAME'))
    mail_from = os.getenv('OTP_MAIL_FROM')
    substitutions = {
                '*APP_NAME*': os.getenv('APP_NAME'),
                '*OTP_URL*': os.getenv('OTP_URL'),
                '*OTP*': otp,
            }
    # Send email
    try:
        send_mail(
            template_path, 'Registration code', mail_from, [register.email], substitutions
        )
    except ConnectionRefusedError as e:
        if not os.getenv('DEBUG'):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Add the user
    register.otp = otp
    return await crud.add(db, register)
