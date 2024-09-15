from tkinter.constants import ALL

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.acl.models import ACL
from src.domains.base.models import session_token_var
from src.domains.role.models import Role
from src.domains.scope.models import Scope
from src.domains.token.models import SessionData
from src.domains.user.models import User
from src.session.session import authorize_session


async def add_scope_to_role(db: AsyncSession, role_id, scope_id):
    role = await crud.get_one_where(db, Role, Role.id, role_id)
    scope = await crud.get_one_where(db, Scope, Scope.id, scope_id)
    if role and scope:
        role.scopes.append(scope)
        await db.commit()


async def set_user_scopes_in_session(db: AsyncSession, email):
    scope_dict = {}
    # Populate
    user = await crud.get_one_where(db, User, User.email, email, relation=User.roles)
    # Todo: see if "get_one_where" can be ignored
    roles = user.roles
    for role in roles:
        acls = await crud.get_one_where(db, Role, Role.name, role.name, relation=Role.acls)
        for acl in acls:
            scopes = await crud.get_one_where(db, ACL, ACL.name, acl.name, relation=ACL.scopes)
            for scope in scopes:
                scope_dict = _add_access(scope_dict, scope.entity, scope.access)

    # Compress if "*"
    # - Entities
    compressed_scopes = {}
    if ALL in scope_dict.keys():
        compressed_scopes = {k: v for k, v in scope_dict.items() if k != ALL}
    # - Access
    for entity, accesses in compressed_scopes.items():
        if ALL in accesses:
            compressed_scopes[entity] = {ALL}

    # Update session data
    authorize_session(compressed_scopes)


def _add_access(scope_dict, entity, access) -> dict:
    if entity not in scope_dict:
        scope_dict[entity] = set()
    scope_dict[entity].add(access)
    return scope_dict
