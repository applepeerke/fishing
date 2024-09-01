import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, EmailStr, SecretStr, conint
from sqlalchemy import (Column, String, func, DateTime, Integer)
from sqlalchemy.orm import Mapped, mapped_column

from src.general.models import get_session_user
from src.utils.db.db import Base


class UserStatus:
    Inactive = 10
    Active = 20
    Expired = 80
    Blocked = 90
    Blacklisted = 99


# SqlAlchemy model
class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, nullable=False, index=True)
    password = Column(String, nullable=True)
    expired = Column(DateTime(timezone=True), nullable=True)
    authentication_token = Column(String, nullable=True)
    fail_count = Column(Integer, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(Integer, default=UserStatus.Inactive)
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, default=get_session_user())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    updated_by = Column(String, nullable=True, onupdate=get_session_user())


# Pydantic models
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: UUID4
    password: Optional[SecretStr] = Field(min_length=8, max_length=256, default=None)
    expired: Optional[datetime] = Field(DateTime(timezone=True))
    fail_count: conint(ge=0, lt=100) = 0
    blocked_until: Optional[datetime] = Field(DateTime(timezone=True))
    authentication_token: Optional[SecretStr] = Field(min_length=16, max_length=1024, default=None)
    status: conint(ge=10, lt=100) = UserStatus.Inactive
