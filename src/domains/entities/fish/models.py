from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Integer, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import FishStatus


# SqlAlchemy model
class Fish(Base):
    __tablename__ = 'fish'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    fishspecies_id: Mapped[UUID] = mapped_column(ForeignKey('fishspecies.id'), nullable=False)
    status = Column(String, nullable=False, default=FishStatus.Sleeping)
    age = Column(Integer, nullable=True, default=1)
    length_cm = Column(Integer, nullable=True)
    weight_g = Column(Integer, nullable=True)
    caught_count = Column(Integer, nullable=True, default=0)

    # Relations
    fisherman_id: Mapped[UUID] = mapped_column(ForeignKey('fisherman.id'), nullable=True)
    fishingwater_id: Mapped[UUID] = mapped_column(ForeignKey('fishingwater.id'), nullable=True)
    fisherman = relationship('Fisherman', back_populates='fishes')
    fishingwater = relationship('FishingWater', back_populates='fishes')


# Pydantic models
class FishModel(BaseModel):
    fishspecies_id: UUID4
    status: FishStatus
    age: int = Field(ge=1, le=50)
    length_cm: int = Field(ge=1, le=1000)
    weight_g: int = Field(ge=1, le=100000)
    caught_count: Optional[int] = Field(le=100)
    # Relations
    fisherman_id: Optional[UUID4]
    fishingwater_id: Optional[UUID4]


class FishReadModel(FishModel):
    id: UUID4
    # Relations
    # fishingwater: Optional['FishingWaterBase'] = []
    # fisherman: Optional['FishermanBase'] = []


# Unfortunately update forward referencing does not work for FishingWater...
# from src.domains.entities.fishingwater.models import FishingWaterBase
# from src.domains.entities.fisherman.models import FishermanBase
# FishSpeciesReadModel.update_forward_refs()
