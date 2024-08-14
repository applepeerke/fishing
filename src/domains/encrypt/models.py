from typing import Optional

from pydantic import BaseModel, Field, SecretStr


# Pydantic models
class Password(BaseModel):
    plain_text: SecretStr = Field(min_length=1, max_length=9999)
    encrypted_text: Optional[str] = Field(default=None)


class PasswordEncrypted(BaseModel):
    encrypted_text: str = Field(default=None)
