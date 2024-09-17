from pydantic import BaseModel, EmailStr

from src.domains.token.constants import BEARER


class AuthenticationToken(BaseModel):
    token: str | None = None
    token_type: str = BEARER


class SessionData(BaseModel):
    email: EmailStr | None = None
    scopes: list[str] = []
