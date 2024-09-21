from datetime import datetime

from pydantic import BaseModel, EmailStr

from src.domains.login.token.constants import BEARER


class Authentication(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = BEARER
    refresh_token_expiration: datetime | None = None


class Authorization(Authentication):
    scopes: list[str] = []


class SessionData(BaseModel):
    email: EmailStr | None = None
    scopes: list[str] = []
