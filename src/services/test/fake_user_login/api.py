from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db import get_db_session
from src.services.test.functions import login_with_fake_admin

fake_user_login = APIRouter()


@fake_user_login.post('/')
async def login_with_fake_user(
        db: AsyncSession = Depends(get_db_session),
        email='fakedummy@example.nl',
        password='FakeWelcome01!',
        role_name='fake_admin'
):
    # Authorize user
    return await login_with_fake_admin(db, email=email, password=password, role_names=[role_name])
