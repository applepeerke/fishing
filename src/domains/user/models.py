from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, EmailStr, SecretStr
from sqlalchemy import (Column, String, func, DateTime, Integer, Boolean)
from sqlalchemy.orm import Mapped, mapped_column

from src.general.models import get_current_user
from src.utils.db.db import Base


class UserStatus(str, Enum):
    Inactive = "Inactive"
    Initialized = "Initialized"
    Registered = "Registered"
    Active = "Active"
    Expired = "Expired"
    Blocked = "Blocked"
    Blacklisted = "Blacklisted"


# SqlAlchemy model
class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, nullable=False, index=True)
    password = Column(String, nullable=True)
    expired = Column(DateTime(timezone=True), nullable=True)
    authentication_token = Column(String, nullable=True)
    otp = Column(Integer, nullable=True)
    fail_count = Column(Integer, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default=UserStatus.Inactive)
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, default=get_current_user())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    updated_by = Column(String, nullable=True, onupdate=get_current_user())


# Pydantic models
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: UUID4
    password: Optional[SecretStr] = Field(min_length=8, max_length=64, default=None)
    authentication_token: Optional[SecretStr] = Field(min_length=16, max_length=1024, default=None)
    otp: Optional[int] = Field(ge=10000, lt=100000, default=None)
    expired: Optional[datetime] = Field(DateTime(timezone=True))
    fail_count: int = 0
    blocked_until: Optional[datetime] = Field(DateTime(timezone=True))
    black_listed: bool = False
    status: UserStatus = UserStatus.Inactive
