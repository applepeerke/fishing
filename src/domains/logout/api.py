from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db import crud
from src.db.db import get_db_session
from src.domains.login.models import LoginBase
from src.domains.user.functions import set_user_status
from src.domains.user.models import User, UserStatus
from src.session.session import delete_session

login_logout = APIRouter()


@login_logout.post('/')
async def logout(
        request: Request, response: Response, login_base: LoginBase, db: AsyncSession = Depends(get_db_session)):
    """ Logout with email """
    if not login_base:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    # The user must exist and be logged in.
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=login_base.email)
    if not user or user.status != UserStatus.LoggedIn:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='The user has not the right status.')

    # a. Delete session authorization.
    await delete_session(request)
    # b. Update db status.
    await set_user_status(db, user, target_status=UserStatus.Active)
    # c. Remove response authorization.
    if AUTHORIZATION in response.headers:
        del response.headers[AUTHORIZATION]
