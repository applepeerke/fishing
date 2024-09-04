from pydantic import BaseModel, EmailStr


class AccessToken(BaseModel):
    access_token: str
    token_type: str


class AccessTokenData(BaseModel):
    email: EmailStr | None = None
