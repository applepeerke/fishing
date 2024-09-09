from pydantic import BaseModel, Field, EmailStr, SecretStr


# Pydantic models

class LoginBase(BaseModel):
    email: EmailStr


class Login(LoginBase):
    password: SecretStr = Field(min_length=10, max_length=20)
    password_repeat: SecretStr = Field(min_length=10, max_length=20)
