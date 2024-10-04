from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.fish_species.models import FishSpeciesReadModel, FishSpeciesModel, FishSpecies
from src.domains.login.token.functions import is_authorized

fish_species = APIRouter()


@fish_species.post('/', response_model=FishSpeciesReadModel)
async def create_fish_species(
        fish_species_create: FishSpeciesModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishspecies_create'])]
):
    new_fish_species = FishSpecies(
        species_name=fish_species_create.species_name,
        subspecies_name=fish_species_create.subspecies_name,
        relative_density=fish_species_create.relative_density,
        active_at=fish_species_create.active_at,
        minimum_length_to_keep_cm=fish_species_create.minimum_length_to_keep_cm,
        max_length_cm=fish_species_create.max_length_cm,
        max_weight_g=fish_species_create.max_weight_g,
        yearly_growth_in_cm=fish_species_create.yearly_growth_in_cm,
        yearly_growth_in_g=fish_species_create.yearly_growth_in_g,
    )
    return await crud.add(db, new_fish_species)


@fish_species.get('/', response_model=list[FishSpeciesReadModel])
async def read_fish_specieses(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishspecies_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, FishSpecies, skip=skip, limit=limit)


@fish_species.get('/{id}', response_model=FishSpeciesReadModel)
async def read_fish_species(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishspecies_read'])]
):
    return await crud.get_one(db, FishSpecies, id)


@fish_species.put('/{id}', response_model=FishSpeciesReadModel)
async def update_fish_species(
        id: UUID,
        fish_species_update: FishSpeciesReadModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishspecies_update'])]
):
    fish_species_update.id = id
    return await crud.upd(db, FishSpecies, fish_species_update)


@fish_species.delete('/{id}')
async def delete_fish_species(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishspecies_delete'])]
):
    success = await crud.delete(db, FishSpecies, id)
    return get_delete_response(success, FishSpecies.__tablename__)
