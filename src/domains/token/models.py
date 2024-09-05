from pydantic import BaseModel, EmailStr


class OAuthAccessToken(BaseModel):
    access_token: str
    token_type: str


class AccessTokenData(BaseModel):
    email: EmailStr | None = None
