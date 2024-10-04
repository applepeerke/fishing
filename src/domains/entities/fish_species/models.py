from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, UUID4, Field, model_validator
from sqlalchemy import (Column, String, func, Integer, ARRAY)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.db import Base
from src.domains.entities.enums import ActiveAt, SpeciesEnum, CarpSubspecies

HOURS_OF_ACTIVITY = {
    ActiveAt.Day: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    ActiveAt.Night: [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6],
    ActiveAt.Both: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
}


# SqlAlchemy model
class FishSpecies(Base):
    __tablename__ = 'fishspecies'
    id: Mapped[UUID] = mapped_column(nullable=False, primary_key=True, server_default=func.gen_random_uuid())
    species_name = Column(String, nullable=False, index=True)
    subspecies_name = Column(String, nullable=True)
    active_at = Column(String, nullable=False, default=ActiveAt.Day)
    relative_density = Column(Integer, nullable=False)
    minimum_length_to_keep_cm = Column(Integer, nullable=False)
    max_length_cm = Column(Integer, nullable=False)
    max_weight_g = Column(Integer, nullable=False)
    yearly_growth_in_cm = Column(Integer, nullable=False)
    yearly_growth_in_g = Column(Integer, nullable=False)
    # Derived
    hours_of_activity = Column(ARRAY(Integer), nullable=False, default=HOURS_OF_ACTIVITY[ActiveAt.Day])


# Pydantic models
class FishSpeciesModel(BaseModel):
    species_name: SpeciesEnum
    subspecies_name: Optional[CarpSubspecies]
    active_at: ActiveAt
    relative_density: int = Field(ge=1, le=100)
    minimum_length_to_keep_cm: int = Field(ge=10, le=80)
    max_length_cm: int = Field(ge=10, le=800)
    max_weight_g: int = Field(ge=5, le=1000000)
    yearly_growth_in_cm: int = Field(ge=1, le=30)
    yearly_growth_in_g: int = Field(ge=5, le=500)
    # Derived
    hours_of_activity: List[int]

    @model_validator(mode="after")
    def check_hours_of_activity(self):
        self.hours_of_activity = HOURS_OF_ACTIVITY.get(self.active_at, [])
        return self


class FishSpeciesReadModel(FishSpeciesModel):
    id: UUID4
