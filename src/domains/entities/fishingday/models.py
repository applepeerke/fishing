from uuid import UUID

from pydantic import BaseModel, UUID4
from sqlalchemy import (Column, String, func, Table, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.db import Base
from src.domains.entities.enums import Day


# SqlAlchemy model
fisherman_fishingday = Table(
    'fisherman_fishingday', Base.metadata,
    Column('fisherman_id', ForeignKey('fisherman.id', ondelete='CASCADE'), primary_key=True),
    Column('fishingday_id', ForeignKey('fishingday.id', ondelete='CASCADE'), primary_key=True))


class FishingDay(Base):
    __tablename__ = 'fishingday'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False, index=True)
    # Relations
    fisherman = relationship(
        'Fisherman', secondary=fisherman_fishingday,  back_populates='fishing_days', passive_deletes=True,
        lazy='selectin')


# Pydantic models
class FishingDayBase(BaseModel):
    name: Day


class FishingDayRead(FishingDayBase):
    id: UUID4
