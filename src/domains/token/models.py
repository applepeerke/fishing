from pydantic import BaseModel, EmailStr


class OAuthAccessToken(BaseModel):
    access_token: str
    token_type: str


class SessionTokenData(BaseModel):
    email: EmailStr | None = None
