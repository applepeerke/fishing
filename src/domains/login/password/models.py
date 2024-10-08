from typing import Optional
from pydantic import BaseModel, Field, EmailStr, SecretStr


# Pydantic models
class Password(BaseModel):
    plain_text: SecretStr = Field(min_length=8, max_length=9999)
    encrypted_text: Optional[str] = Field(default=None)


class PasswordEncrypted(BaseModel):
    encrypted_text: str = Field(default=None)


class ChangePasswordBase(BaseModel):
    email: EmailStr


class ChangePassword(ChangePasswordBase):
    password: SecretStr = Field(min_length=10, max_length=20)
    new_password: SecretStr = Field(min_length=10, max_length=20)
    new_password_repeated: SecretStr = Field(min_length=10, max_length=20)

