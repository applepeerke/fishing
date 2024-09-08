from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domains.base.models import Base
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS


# SqlAlchemy model
# noinspection PyUnresolvedReferences
class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, index=True, unique=True)
    # Relations
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped['User'] = relationship(back_populates="roles")


# Pydantic models
class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)


class RoleRead(RoleBase):
    id: UUID4
