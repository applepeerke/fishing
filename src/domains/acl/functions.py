from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.acl.models import ACL
from src.domains.scope.models import Scope


async def add_scope_to_acl(db: AsyncSession, acl_id, scope_id):
    acl = await crud.get_one_where(db, ACL, ACL.id, acl_id)
    scope = await crud.get_one_where(db, Scope, Scope.id, scope_id)
    if acl and scope:
        acl.scopes.append(scope)
        await db.commit()
