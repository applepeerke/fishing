import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.entities.fish.models import Fish
from src.domains.entities.fisherman.models import Fisherman
from src.domains.entities.fishingwater.models import FishingWater
from src.domains.login.role.models import Role
from src.domains.login.user.models import User


@pytest.mark.asyncio
async def test_cascading_user(client: AsyncClient, db: AsyncSession):
    """ No "cascading all, delete" is used in relationships because that deletes e.g. roles when a user is deleted."""
    # a. Create role-1 and role-2
    role_1 = await crud.add(db, Role(name='role_1'))
    assert role_1 is not None
    role_2 = await crud.add(db, Role(name='role_2'))
    assert role_2 is not None
    # b. create user-1 with both roles.
    user_1 = await add_user_with_roles(db, 'dummy-1@sample.com', roles=[role_1, role_2])
    assert user_1 and len(user_1.roles) == 2

    # c. Delete role-1
    await crud.delete(db, Role, user_1.roles[0].id)
    #    User 1 must still exist with 2 roles (unfortunately) - but table "user_role" has 1 link.
    user_1 = await crud.get_one(db, User, user_1.id)
    assert user_1 and len(user_1.roles) == 2
    #    Only role-2 must exist
    assert not await crud.get_one_where(db, Role, Role.name, 'role_1')
    assert await crud.get_one_where(db, Role, Role.name, 'role_2')

    # d. create user-2 with role-2
    user_2 = await add_user_with_roles(db, 'dummy-2@sample.com', roles=[role_2])

    # e. Delete user-1
    await crud.delete(db, User, user_1.id)
    assert not await crud.get_one(db, User, user_1.id)
    #    Role-2 must still exist
    roles = await crud.get_all(db, Role)
    assert len(roles) == 1

    # f. Delete user-2
    await crud.delete(db, User, user_2.id)
    assert not await crud.get_one(db, User, user_1.id)
    # There should still be 1 role.
    roles = await crud.get_all(db, Role)
    assert len(roles) == 1


async def add_user_with_roles(db, email, roles: list = None) -> User:
    # a. Create user
    user = await crud.add(db, User(email=email))
    assert user is not None
    # Add the roles to the user
    if roles:
        for role in roles:
            user.roles.append(role)
            await db.commit()
    # Verify
    user = await crud.get_one(db, User, user.id)
    assert len(user.roles) == len(roles) if roles else 0
    return user


@pytest.mark.asyncio
async def test_cascading_fishingwater(client: AsyncClient, db: AsyncSession):
    """ No "cascading all, delete" is used in relationships because that deletes e.g. roles when a user is deleted."""
    # a. Create base data
    # - Fish-1, 2, and 3
    fish_1 = await crud.add(db, Fish(species='fish_1'))
    fish_2 = await crud.add(db, Fish(species='fish_2'))
    fish_3 = await crud.add(db, Fish(species='fish_3'))
    assert len(await crud.get_all(db, Fish)) == 3
    # - Fisherman-1 and 2
    fisherman_1 = await crud.add(db, Fisherman(forename='Petri', surname='Heil'))
    fisherman_2 = await crud.add(db, Fisherman(forename='John', surname='Catch'))
    assert len(await crud.get_all(db, Fisherman)) == 2
    # - FishingWater-1 and 2
    fishingwater_1 = await crud.add(db, FishingWater(location='Leiden', type='Rivier'))
    fishingwater_2 = await crud.add(db, FishingWater(location='Voorschoten', type='Meer'))
    assert len(await crud.get_all(db, FishingWater)) == 2
    # b. Populate fishing waters
    # - Add fish-1 and fish-3 to fishingwater-1 and fish-2 to fishingwater-2
    fishingwater_1.fishes.append(fish_1)
    fishingwater_1.fishes.append(fish_3)
    fishingwater_2.fishes.append(fish_2)
    # - Link fisherman-1 to fishingwater-1 and fisherman-2 to fishingwater-2
    fishingwater_1.fishermen.append(fisherman_1)
    fishingwater_2.fishermen.append(fisherman_2)
    await db.commit()
    # - Check population
    fishingwater_1 = await crud.get_one(db, FishingWater, fishingwater_1.id)
    assert len(fishingwater_1.fishermen) == 1
    assert len(fishingwater_1.fishes) == 2
    # c. Catch fish-1
    #  - Add fish-1 to fisherman-1 and remove it from fishingwater
    await catch_a_fish(db, fishingwater_1, fisherman_1, fish_1)
    # d. Delete fishingwater-1 - Fish-3 should also be deleted,
    #    FishingWater 2, Fisherman 1, 2 and fish 1, 2 should still exist.
    await crud.delete(db, FishingWater, fishingwater_1.id)
    assert await crud.get_one(db, FishingWater, fishingwater_2.id) is not None
    assert len(await crud.get_all(db, Fisherman)) == 2
    assert len(await crud.get_all(db, Fish)) == 2
    # e. Delete fisherman-1 - Caught Fish-1 should also be deleted.
    #    Fisherman 2 and fish 2 should still exist.
    await crud.delete(db, Fisherman, fisherman_1.id)
    assert len(await crud.get_all(db, Fisherman)) == 1
    assert len(await crud.get_all(db, Fish)) == 1
    # f. Delete fishingwater-2 - Fisherman 2 should still exist.
    await crud.delete(db, FishingWater, fishingwater_2.id)
    assert await crud.get_one(db, Fisherman, fisherman_2.id) is not None
    # g.  Delete Fisherman-2 - No FishingWater, Fisherman, Fish should be left.
    await crud.delete(db, Fisherman, fisherman_2.id)
    assert not await crud.get_all(db, FishingWater)
    assert not await crud.get_all(db, Fisherman)
    assert not await crud.get_all(db, Fish)


async def catch_a_fish(db, fishingwater, fisherman, fish_to_catch):
    assert fishingwater and fisherman and fish_to_catch
    # Fish must not been caught already
    assert not fish_to_catch.fisherman_id
    # Remove fish from fishing water
    new_fishes = [fish for fish in fishingwater.fishes if fish.id != fish_to_catch.id]
    assert len(new_fishes) == len(fishingwater.fishes) - 1
    fishingwater.fishes = new_fishes
    # Add fish to fisherman
    fisherman.fishes.append(fish_to_catch)
    # Commit!
    await db.commit()
