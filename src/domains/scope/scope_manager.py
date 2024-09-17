from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import ALL
from src.db import crud
from src.domains.user.models import User


class ScopeManager:
    @property
    def user_scopes(self):
        return self._user_scopes

    def __init__(self, db: AsyncSession, email):
        self._db = db
        self._email = email
        self._user_scopes = {}

    async def get_user_scopes(self, compressed=True) -> list:
        user_scopes = await self.get_user_scopes_dict(compressed)
        # Set the unique set of scopes
        return list({
            f'{entity}_{access}'
            for entity, accesses in user_scopes.items()
            for access in accesses
        })

    async def get_user_scopes_dict(self, compressed=True) -> dict:
        # Populate
        user = await crud.get_one_where(self._db, User, User.email, self._email)
        [self._add_access(scope.entity, scope.access)
         for role in user.roles
         for acl in role.acls
         for scope in acl.scopes]

        # Compress "*"-containing entities and accesses
        if compressed:
            self._compress()
        return self._user_scopes

    def _add_access(self, entity: str, access: str):
        if not entity or not access:
            return
        if entity not in self._user_scopes:
            self._user_scopes[entity] = set()
        self._user_scopes[entity].add(access)

    def _compress(self):
        # Generic Access: Exit
        if ALL in self._user_scopes.get(ALL, {}):
            self._user_scopes = {ALL: {ALL}}
            return

        # Apply generic access ("*") to entities that have "*" access.
        for entity, accesses in self._user_scopes.items():
            if ALL in accesses:
                self._user_scopes[entity] = {ALL}

        # Get all non-generic accesses for generic entity "*".
        all_entity_accesses = list(self._user_scopes.get(ALL, {}))

        # Apply all generic entity ("*") accesses (except the generic access ("*")) to all other entities.
        for entity, accesses in self._user_scopes.items():
            if entity != ALL:
                for access in all_entity_accesses:
                    if access in self._user_scopes[entity]:
                        self._user_scopes[entity].remove(access)
                        if not self._user_scopes[entity]:
                            del self._user_scopes[entity]
