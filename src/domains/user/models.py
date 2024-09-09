from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, EmailStr, SecretStr, conint
from sqlalchemy import (Column, String, func, DateTime, Integer)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.base.models import Base
from src.domains.role.models import Role


class UserStatus:
    Inactive = 10
    Acknowledged = 20
    Active = 30
    Expired = 80
    Blocked = 90
    Blacklisted = 99


# SqlAlchemy model
class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, nullable=False, index=True, unique=True)
    password = Column(String, nullable=True)
    expired = Column(DateTime(timezone=True), nullable=True)
    authentication_token = Column(String, nullable=True)
    fail_count = Column(Integer, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(Integer, default=UserStatus.Inactive)
    # Relations
    roles: Mapped[List['Role']] = relationship(back_populates='user', cascade='all, delete')


# Pydantic models
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    password: Optional[SecretStr] = Field(min_length=8, max_length=256, default=None)
    expired: Optional[datetime] = Field(DateTime(timezone=True))
    fail_count: conint(ge=0, lt=100) = 0
    blocked_until: Optional[datetime] = Field(DateTime(timezone=True))
    authentication_token: Optional[SecretStr] = Field(min_length=16, max_length=1024, default=None)
    status: conint(ge=10, lt=100) = UserStatus.Inactive


class UserRead(UserUpdate):
    id: UUID4
