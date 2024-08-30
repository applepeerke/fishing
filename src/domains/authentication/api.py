from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import validate_user
from src.domains.user.models import User
from src.utils.db import crud
from src.utils.db.db import get_db_session
from src.utils.security.crypto import verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

token = APIRouter()


async def get_current_user(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        access_token: Annotated[str, Depends(oauth2_scheme)]
):
    current_user = await crud.get_one_where(db, User, att_name=User.email, att_value=access_token)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@token.post("/")
async def get_access_token(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await crud.get_one_where(db, User, att_name=User.email, att_value=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    # ToDo: Get auth token
    return {"access_token": form_data.username, "token_type": "bearer"}


@token.get("/current_user")
async def get_current_active_user(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        current_user: Annotated[User, Depends(get_current_user)]):
    await validate_user(db, current_user)
    return current_user
