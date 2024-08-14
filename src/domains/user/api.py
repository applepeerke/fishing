import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.user.models import User, UserRead, UserCreate
from src.general.models import get_delete_response, StatusResponse
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.functions import find_filename_path
from src.utils.mail.mail import send_mail
from src.utils.security.crypto import get_otp_as_number

user = APIRouter()
user_registration = APIRouter()


@user.post('/', response_model=UserRead)
async def create_user(user_create: UserCreate, db: AsyncSession = Depends(get_db_session)):
    new_user = User(
        email=user_create.email,
        password=user_create.password.get_secret_value()
    )
    return await crud.add(db, new_user)


@user.get('/', response_model=list[UserRead])
async def read_users(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, User, skip=skip, limit=limit)


@user.get('/{id}', response_model=UserRead)
async def read_user(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, User, id)


@user.put('/{id}', response_model=UserRead)
async def update_user(id: UUID, user_update: UserCreate, db: AsyncSession = Depends(get_db_session)):
    user_update.password = user_update.password.get_secret_value()
    user_update.authentication_token = user_update.authentication_token.get_secret_value()
    return await crud.upd(db, User, id, user_update)


@user.delete('/{id}', response_model=StatusResponse)
async def delete_user(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, User, id)
    return get_delete_response(success, User.__tablename__)

"""
LogIn
"""


@user_registration.post('/', response_model=UserRead)
async def register_user(user_create: UserCreate, db: AsyncSession = Depends(get_db_session)):
    # The user must not already exist.
    obj = await crud.get_one_where(db, User, att_name=User.email, att_value=user_create.email)
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
            template_path, 'Registration code', mail_from, [user_create.email], substitutions
        )
    except ConnectionRefusedError as e:
        if not os.getenv('DEBUG'):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Add the user
    user_create.otp = otp
    return await crud.add(db, user_create)
