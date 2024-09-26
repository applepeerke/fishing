from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Integer, DECIMAL, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import ActiveAt, FishStatus, SpeciesEnum, CarpSubspecies
from src.utils.functions import get_random_name
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS


# SqlAlchemy model
class Fish(Base):
    __tablename__ = 'fish'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, default=get_random_name(10))
    species = Column(String, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    length = Column(DECIMAL(4, 1), nullable=False)
    weight_in_g = Column(Integer, nullable=False)
    subspecies = Column(String, nullable=True)
    active_at = Column(String, nullable=False, default=ActiveAt.Day)
    status = Column(String, nullable=False, default=FishStatus.Sleeping)
    relative_density = Column(Integer, nullable=False)
    # Foreign keys
    fisherman_id: Mapped[UUID] = mapped_column(ForeignKey('fisherman.id'), nullable=True)
    fishingwater_id: Mapped[UUID] = mapped_column(ForeignKey('fishingwater.id'), nullable=True)
    # Relations
    fisherman = relationship('Fisherman', back_populates='fishes')
    fishingwater = relationship('FishingWater', back_populates='fishes')


# Pydantic models
class FishBase(BaseModel):
    name: str = Field(min_length=1, max_length=30, pattern=REGEX_ALPHANUM_PLUS)
    species: SpeciesEnum
    age: int = Field(ge=0, le=100)
    length: Decimal
    weight_in_g: int = Field(ge=0, le=100000)
    subspecies: Optional[CarpSubspecies]
    active_at: ActiveAt
    status: FishStatus
    relative_density: int = Field(ge=1, le=100)
    # Relations
    fisherman_id: Optional[UUID4]
    fishingwater_id: Optional[UUID4]


class FishRead(FishBase):
    id: UUID4
    # Relations
    # fishingwater: Optional['FishingWaterBase'] = []
    fisherman: Optional['FishermanBase'] = []


# Todo: Unfortunately update forward referencing does not work for FishingWater...
# from src.domains.entities.fishingwater.models import FishingWaterBase
from src.domains.entities.fisherman.models import FishermanBase
FishRead.update_forward_refs()
