from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, EmailStr, SecretStr, conint
from sqlalchemy import (Column, String, func, DateTime, Integer, ForeignKey, Table)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.base.models import Base


class UserStatus:
    Inactive = 10
    Acknowledged = 20
    Active = 30
    LoggedIn = 40
    Expired = 80
    Blocked = 90
    Blacklisted = 99


# SqlAlchemy model
user_role = Table('user_role', Base.metadata,
                  Column('user_id',
                         ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
                  Column('role_id',
                         ForeignKey('role.id', ondelete='CASCADE'), primary_key=True))


# noinspection PyUnresolvedReferences
class User(Base):
    __tablename__ = 'user'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, nullable=False, index=True, unique=True)
    password = Column(String, nullable=True)
    expiration = Column(DateTime(timezone=True), nullable=True)
    fail_count = Column(Integer, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(Integer, default=UserStatus.Inactive)
    # Relations
    roles: Mapped[List['Role']] = relationship(secondary=user_role, back_populates='users', lazy='selectin')


# Pydantic models
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    password: Optional[SecretStr] = Field(min_length=8, max_length=256, default=None)
    expiration: Optional[datetime] = Field(default=None)
    fail_count: conint(ge=0, lt=100) = 0
    blocked_until: Optional[datetime] = Field(default=None)
    status: conint(ge=10, lt=100) = UserStatus.Inactive


class UserRead(UserUpdate):
    id: UUID4
