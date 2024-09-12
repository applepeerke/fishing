from pydantic import BaseModel, EmailStr


class SessionToken(BaseModel):
    token: str
    token_type: str


class SessionTokenData(BaseModel):
    email: EmailStr | None = None
