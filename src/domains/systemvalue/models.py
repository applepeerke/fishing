from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, DateTime, Integer)
from sqlalchemy.orm import Mapped, mapped_column

from src.general.models import get_session_user
from src.utils.db.db import Base


# SqlAlchemy model
class SystemValue(Base):
    __tablename__ = 'systemvalues'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    token_expiration_days = Column(Integer, default=1)
    max_login_failures = Column(Integer, default=5)
    block_minutes = Column(Integer, default=10)
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, default=get_session_user())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    updated_by = Column(String, nullable=True, onupdate=get_session_user())


# Pydantic models
class SystemValueBase(BaseModel):
    token_expiration_days: int = Field(gt=0, lt=365)
    max_login_failures: int = Field(gt=0, lt=10)
    block_minutes: int = Field(gt=0, lt=9999)


class SystemValueCreate(SystemValueBase):
    pass


class SystemValueRead(SystemValueBase):
    id: UUID4


