from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, DateTime)
from sqlalchemy.orm import Mapped, mapped_column

from src.general.models import get_session_user
from src.utils.db.db import Base
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS


# SqlAlchemy model
class FishingWater(Base):
    __tablename__ = 'fishingwaters'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    location = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, default=get_session_user())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())
    updated_by = Column(String, nullable=True, onupdate=get_session_user())


# Pydantic models
class FishingWaterBase(BaseModel):
    location: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)
    type: str = Field(min_length=1, max_length=30, pattern=REGEX_ALPHANUM_PLUS)


class FishingWaterCreate(FishingWaterBase):
    pass


class FishingWaterRead(FishingWaterBase):
    id: UUID4


