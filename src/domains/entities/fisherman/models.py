from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, UUID4, Field
from sqlalchemy import (Column, String, func, Table, ForeignKey, Integer)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import SpeciesEnum, Frequency, FishermanStatus
from src.domains.entities.fish.models import FishBase
from src.domains.entities.fishingdays.models import FishingDayBase, fisherman_fishingday
from src.utils.functions import get_random_name
from src.utils.security.input_validation import REGEX_ALPHANUM_PLUS

# SqlAlchemy model
fishingwater_fisherman = Table(
    'fishingwater_fisherman', Base.metadata,
    Column('fishingwater_id', ForeignKey('fishingwater.id', ondelete='CASCADE'), primary_key=True),
    Column('fisherman_id', ForeignKey('fisherman.id', ondelete='CASCADE'), primary_key=True))


class Fisherman(Base):
    __tablename__ = 'fisherman'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    forename = Column(String, nullable=False, default=get_random_name(8))
    surname = Column(String, nullable=False, default=get_random_name(20))
    fish_species = Column(String, nullable=False, default=SpeciesEnum.Roach)
    frequency = Column(String, nullable=False)
    fishing_session_duration = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    # Relations
    fishingwaters = relationship(
        'FishingWater', secondary=fishingwater_fisherman, back_populates='fishermen',
        passive_deletes=True, lazy='selectin')
    fishes = relationship(
        'Fish', back_populates='fisherman', cascade='all, delete-orphan', lazy='selectin')
    fishing_days = relationship(
        'FishingDay', secondary=fisherman_fishingday, back_populates='fisherman', lazy='selectin')


# Pydantic models
class FishermanBase(BaseModel):
    forename: str = Field(min_length=1, max_length=20, pattern=REGEX_ALPHANUM_PLUS)
    surname: str = Field(min_length=1, max_length=50, pattern=REGEX_ALPHANUM_PLUS)
    fish_species: SpeciesEnum
    frequency: Frequency
    fishing_session_duration: int = Field(ge=1, le=24)
    status: FishermanStatus


class FishermanRead(FishermanBase):
    id: UUID4
    # Relations
    fishes: Optional[List[FishBase]] = []
    fishing_days: Optional[List[FishingDayBase]] = []
