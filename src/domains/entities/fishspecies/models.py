from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Integer, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import ActiveAt, FishStatus, SpeciesEnum, CarpSubspecies


# SqlAlchemy model
class FishSpecies(Base):
    __tablename__ = 'fishspecies'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    species_name = Column(String, nullable=False, index=True)
    subspecies_name = Column(String, nullable=True)
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
class FishSpeciesModel(BaseModel):
    species_name: SpeciesEnum
    subspecies_name: Optional[CarpSubspecies]
    active_at: ActiveAt
    status: FishStatus
    relative_density: int = Field(ge=1, le=100)
    # Relations
    fisherman_id: Optional[UUID4]
    fishingwater_id: Optional[UUID4]


class FishReadModel(FishSpeciesModel):
    id: UUID4
    # Relations
    # fishingwater: Optional['FishingWaterBase'] = []
    fisherman: Optional['FishermanBase'] = []


# Unfortunately update forward referencing does not work for FishingWater...
# from src.domains.entities.fishingwater.models import FishingWaterBase
from src.domains.entities.fisherman.models import FishermanBase
FishReadModel.update_forward_refs()
