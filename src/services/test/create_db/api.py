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
        role_name='fake_admin',
        clear_fake_db='false'
):
    # Authorize user
    clear_fake_db = False if str(clear_fake_db).lower() == 'false' else True
    kwargs = {'db': db, 'email': email, 'password': password, 'role_names': [role_name], 'clear_fake_db': clear_fake_db}
    return await login_with_fake_admin(**kwargs)
