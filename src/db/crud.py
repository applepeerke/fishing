from pydantic import SecretStr
from sqlalchemy.future import select

from src.constants import ID
from src.domains.login.scope.models import Access

"""
CRUD on SQLAlchemy
"""


# C
async def add(db, obj):
    db.add(obj)
    await db.commit()
    await db.refresh(obj)  # Get the new ID
    return obj


# R
async def get_all(db, obj_def, skip: int = 0, limit: int = 9999):
    result = await db.execute(
        select(obj_def)
        .offset(skip)
        .limit(limit)
    )
    objects = result.scalars().all()
    return objects


async def get_one(db, obj_def, id):
    """ Get one by id """
    result = await db.execute(select(obj_def).filter(obj_def.id == id))
    return result.scalars().first()


async def get_where(db, obj_def, att_name, att_value):
    result = await db.execute(select(obj_def).where(att_name == att_value))
    objects = result.scalars().all()
    return objects


async def get_one_where(db, obj_def, att_name, att_value):
    result = await db.execute(select(obj_def).where(att_name == att_value))
    return result.scalars().first()


# U
async def upd(db, obj_def, obj_upd):
    """ SQlAlchemy direct update (test purpose) """
    # Get the record
    obj = await get_one(db, obj_def, obj_upd.id)
    # Copy the updated attributes to SQLAlchemy model
    for key in obj_def.__table__.columns.keys():
        value = getattr(obj_upd, key, None)
        if value is not None and key != ID:
            if isinstance(value, SecretStr):
                value = value.get_secret_value()
            elif isinstance(value, Access):
                value = Access.get_access_value(value)
            setattr(obj, key, value)
    # Increment update_count
    obj.update_count = 1 if not obj.update_count else obj.update_count + 1
    await db.commit()
    await db.refresh(obj)  # Get the new values
    return obj


# D
async def delete(db, obj_def, id) -> bool:
    obj = await get_one(db, obj_def, id)
    await db.delete(obj)
    await db.commit()
    return True

