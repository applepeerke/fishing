from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, model_validator
from sqlalchemy import (Column, String, func, Float, Integer)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import WaterType
from src.domains.entities.fish.models import FishBase
from src.domains.entities.fisherman.models import FishermanBase, fishingwater_fisherman
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS

FLOATING_WATER = (WaterType.Canal, WaterType.River, WaterType.Brook, WaterType.Sea)


# SqlAlchemy model
class FishingWater(Base):
    __tablename__ = 'fishingwater'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    water_type = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False)
    density = Column(Float, nullable=False, default=1)  # Fishes per m3
    m3 = Column(Integer, nullable=True)  # null for floating water or sea
    # Relations
    fishermen = relationship(
        'Fisherman', secondary=fishingwater_fisherman, back_populates='fishingwaters', lazy='selectin')
    fishes = relationship(
        'Fish', back_populates='fishingwater', cascade='all, delete-orphan', lazy='selectin')


# Pydantic models
class FishingWaterBase(BaseModel):
    location: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)
    water_type: WaterType
    density: float = Field(ge=0.1, le=1)
    m3: int

    @model_validator(mode="after")
    def check_m3(self):
        if self.water_type not in FLOATING_WATER and self.m3 < 1000:
            raise ValueError("For still water the minimum amount of m3 is 1000.")
        elif self.water_type in FLOATING_WATER and self.m3 != 0:
            raise ValueError("For floating water the amount of m3 must be 0.")
        return self


class FishingWaterRead(FishingWaterBase):
    id: UUID4
    # Relations
    fishes: Optional[List[FishBase]] = []
    fishermen: Optional[List[FishermanBase]] = []
