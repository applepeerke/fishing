from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.fish.models import FishBase
from src.domains.entities.fisherman.models import FishermanBase, fishingwater_fisherman
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS


# SqlAlchemy model
class FishingWater(Base):
    __tablename__ = 'fishingwater'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    location = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    # Relations
    fishermen = relationship(
        'Fisherman', secondary=fishingwater_fisherman, back_populates='fishingwaters', lazy='selectin')
    fishes = relationship(
        'Fish', back_populates='fishingwater', cascade='all, delete-orphan', lazy='selectin')


# Pydantic models
class FishingWaterBase(BaseModel):
    location: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)
    type: str = Field(min_length=1, max_length=30, pattern=REGEX_ALPHANUM_PLUS)


class FishingWaterRead(FishingWaterBase):
    id: UUID4
    # Relations
    fishes: Optional[List[FishBase]] = []
    fishermen: Optional[List[FishermanBase]] = []
