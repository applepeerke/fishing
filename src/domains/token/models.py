from pydantic import BaseModel, EmailStr


class SessionToken(BaseModel):
    token: str
    token_type: str


class SessionData(BaseModel):
    email: EmailStr | None = None
    scopes: dict | None = None
