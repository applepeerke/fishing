from pydantic import BaseModel, EmailStr

from src.domains.login.token.constants import BEARER


class AuthenticationToken(BaseModel):
    token: str | None = None
    token_type: str = BEARER


class Authorization(AuthenticationToken):
    scopes: list[str] = []


class SessionData(BaseModel):
    email: EmailStr | None = None
    scopes: list[str] = []
