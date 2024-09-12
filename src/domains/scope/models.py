from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Table, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.base.models import Base
from src.utils.security.input_validation import REGEX_ALPHANUM_ASTERISK


class Access(str, Enum):
    none = None
    all = '*'
    create = 'create'
    read = 'read'
    update = 'update'
    delete = 'delete'


# SqlAlchemy model
acl_scope = Table('acl_scop', Base.metadata,
                  Column('acl_id', ForeignKey('acl.id', ondelete='CASCADE'), primary_key=True),
                  Column('scope_id', ForeignKey('scope.id', ondelete='CASCADE'), primary_key=True))


# noinspection PyUnresolvedReferences
class Scope(Base):
    __tablename__ = 'scope'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    entity = Column(String, nullable=False)
    access = Column(String, nullable=True, default=None)
    # Relations
    acls: Mapped[List['ACL']] = relationship(secondary=acl_scope, back_populates='scopes', passive_deletes=True)


# Pydantic models
class ScopeBase(BaseModel):
    entity: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_ASTERISK)
    access: Access = Access.none


class ScopeRead(ScopeBase):
    id: UUID4
