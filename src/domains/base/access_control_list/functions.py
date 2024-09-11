from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.role.models import Role
from src.domains.scope.models import Scope


async def add_scope_to_role(db: AsyncSession, role_id, scope_id):
    role = await crud.get_one_where(db, Role, Role.id, role_id)
    scope = await crud.get_one_where(db, Scope, Scope.id, scope_id)
    if role and scope:
        role.scopes.append(scope)
        await db.commit()
