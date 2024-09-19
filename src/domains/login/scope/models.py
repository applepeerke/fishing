from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, ConfigDict
from sqlalchemy import (Column, String, func, Table, ForeignKey, event)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.base.models import Base
from src.utils.security.input_validation import REGEX_ALPHANUM_ASTERISK


class Entity(str, Enum):
    none = None
    all = '*'
    fishingwater = 'fishingwater'
    fisherman = 'fisherman'
    fish = 'fish'
    user = 'user'
    role = 'role'
    acl = 'acl'
    scope = 'scope'


class Access(str, Enum):
    none = None
    all = '*'
    create = 'create'
    read = 'read'
    update = 'update'
    delete = 'delete'

    @staticmethod
    def get_access_value(value):
        # Used to convert from pydantic to SA.
        if value == Access.none:
            return 'None'
        elif value == Access.all:
            return '*'
        elif value == Access.create:
            return 'create'
        elif value == Access.read:
            return 'read'
        elif value == Access.update:
            return 'update'
        elif value == Access.delete:
            return 'delete'
        else:
            raise NotImplementedError(f'get_access_value got unexpected value "{value}"')


# SqlAlchemy model
acl_scope = Table('acl_scope', Base.metadata,
                  Column('acl_id', ForeignKey('acl.id', ondelete='CASCADE'), primary_key=True),
                  Column('scope_id', ForeignKey('scope.id', ondelete='CASCADE'), primary_key=True))


# noinspection PyUnresolvedReferences
class Scope(Base):
    __tablename__ = 'scope'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    entity = Column(String, nullable=False)
    access = Column(String, nullable=False)
    scope_name = Column(String, nullable=False, unique=True)
    # Relations
    acls: Mapped[List['ACL']] = relationship(
        secondary=acl_scope, back_populates='scopes', passive_deletes=True, lazy='selectin')


# Function to automatically update full_name before insert and update
def update_scope_name(mapper, connection, target):
    target.scope_name = f'{target.entity}_{target.access}'


# Register the SQLAlchemy event to update full_name before insert and update
event.listen(Scope, 'before_insert', update_scope_name)
event.listen(Scope, 'before_update', update_scope_name)


# Pydantic models
class ScopeBase(BaseModel):
    # Enables compatibility with SQLAlchemy models
    model_config = ConfigDict(from_attributes=True)

    entity: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_ASTERISK)
    access: Access = Access.none
    scope_name: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_ASTERISK)


class ScopeRead(ScopeBase):
    id: UUID4
