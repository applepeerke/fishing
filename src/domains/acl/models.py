from typing import List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Table, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.domains.base.models import Base
from src.domains.scope.models import acl_scope
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS

# SqlAlchemy model
role_acl = Table('role_acl', Base.metadata,
                 Column('role_id', ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
                 Column('acl_id', ForeignKey('acl.id', ondelete='CASCADE'), primary_key=True))


# noinspection PyUnresolvedReferences
class ACL(Base):
    __tablename__ = 'acl'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    # Relations
    roles: Mapped[List['Role']] = relationship(secondary=role_acl, back_populates='acls', passive_deletes=True)
    scopes: Mapped[List['Scope']] = relationship(secondary=acl_scope, back_populates='acls', passive_deletes=True)


# Pydantic models
class ACLBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)


class ACLRead(ACLBase):
    id: UUID4
