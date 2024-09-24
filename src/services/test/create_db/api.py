from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db.db import get_db_session
from src.domains.login.token.models import Authentication
from src.services.test.functions import create_fake_authenticated_user

fake_user_login = APIRouter()


@fake_user_login.post('/', response_model=Authentication)
async def login_with_fake_user(
        response: Response,
        db: AsyncSession = Depends(get_db_session),
        email='fakedummy@example.nl',
        password='FakeWelcome01!',
        role_name='fake_admin',
        clear_db=False
):
    # Authorize user
    authentication: Authentication = await create_fake_authenticated_user(
        db, email, password, [role_name], clear_db)
    response.headers.append(AUTHORIZATION, f'{authentication.token_type} {authentication.access_token}')
    return authentication


