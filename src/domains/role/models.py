from typing import List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.acl.models import role_acl
from src.domains.base.models import Base
from src.domains.user.models import user_role
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS


# SqlAlchemy model
# noinspection PyUnresolvedReferences
class Role(Base):
    __tablename__ = 'role'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, index=True, unique=True)
    # Relations
    users: Mapped[List['User']] = relationship(
        secondary=user_role, back_populates='roles', passive_deletes=True, lazy='selectin')
    acls: Mapped[List['ACL']] = relationship(secondary=role_acl, back_populates='roles', lazy='selectin')


# Pydantic models
class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)


class RoleRead(RoleBase):
    id: UUID4
