from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, EmailStr, SecretStr
from sqlalchemy import (Column, String, func, DateTime, Integer, Boolean)
from sqlalchemy.orm import Mapped, mapped_column

from src.general.models import get_current_user
from src.utils.db.db import Base


# Pydantic models
class LoginBase(BaseModel):
    email: EmailStr
    password: Optional[SecretStr] = Field(min_length=8, max_length=20)
    fail_count: int = 0
    blocked_until: Optional[datetime] = Field(DateTime(timezone=True))
    black_listed: bool = False


class Register(LoginBase):
    otp: Optional[int] = Field(gt=100000, lt=1000000, default=None)

