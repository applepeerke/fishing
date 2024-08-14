from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

"""
CRUD
"""


# C
async def add(db, obj):
    db.add(obj)
    await db.commit()
    await db.refresh(obj)  # Get the new ID
    return obj


# R
async def get_all(db, obj_def, relation=None, skip: int = 0, limit: int = 9999):
    if relation:
        # E.g. obj.children
        result = await db.execute(
            select(obj_def)
            .options(selectinload(relation))
            .offset(skip)
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(obj_def)
            .offset(skip)
            .limit(limit)
        )
    objects = result.scalars().all()
    return objects


async def get_one(db, obj_def, id, relation=None):
    if relation:
        # E.g. obj.children
        result = await db.execute(
            select(obj_def)
            .filter(obj_def.id == id)
            .options(selectinload(relation))
        )
    else:
        result = await db.execute(
            select(obj_def)
            .filter(obj_def.id == id)
        )
    return result.scalars().first()


async def get_one_where(db, obj_def, att_name, att_value):
    result = await db.execute(
        select(obj_def)
        .filter(att_name == att_value)
    )
    return result.scalars().first()

# U
async def upd(db, obj_def, id, obj_upd):
    obj = await _get(db, obj_def, id)
    atts = obj_upd.model_dump(exclude_unset=True)
    for att_name, value in atts.items():
        setattr(obj, att_name, value)
    await db.commit()
    await db.refresh(obj)  # Get the new values
    return obj


# D
async def delete(db, obj_def, id) -> bool:
    obj = await _get(db, obj_def, id)
    await db.delete(obj)
    await db.commit()
    return True

"""
Routines
"""


async def _get(db, obj_def, id: int):
    result = await db.execute(
        select(obj_def)
        .filter(obj_def.id == id)
    )
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj
