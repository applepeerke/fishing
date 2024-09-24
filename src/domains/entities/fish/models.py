from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Integer, DECIMAL, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base


class Species(str, Enum):
    Ale = 'Ale'
    Carp = 'Carp'
    Perch = 'Perch'
    Roach = 'Roach'
    Pike = 'Pike'


class Subspecies(str, Enum):
    Row = 'Row'
    Scale = 'Scale'
    Leather = 'Leather'
    Wild = 'Wild'


# SqlAlchemy model
class Fish(Base):
    __tablename__ = 'fish'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    species = Column(String, nullable=False, index=True)
    length = Column(DECIMAL(4, 1), nullable=True)
    weight_in_g = Column(Integer, nullable=True)
    subspecies = Column(String, nullable=True)
    # Foreign keys
    fisherman_id: Mapped[UUID] = mapped_column(ForeignKey('fisherman.id'), nullable=True)
    fishingwater_id: Mapped[UUID] = mapped_column(ForeignKey('fishingwater.id'), nullable=True)
    # Relations
    fisherman = relationship('Fisherman', back_populates='fishes')
    fishingwater = relationship('FishingWater', back_populates='fishes')


# Pydantic models
class FishBase(BaseModel):
    species: Species
    length: Optional[Decimal]
    weight_in_g: Optional[int] = Field(ge=0, le=100000)
    subspecies: Optional[Subspecies]


class FishRead(FishBase):
    id: UUID4
