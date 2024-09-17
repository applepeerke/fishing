from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.scope.scope_manager import ScopeManager
from src.session.session import authorize_session


async def set_user_scopes_in_session(db: AsyncSession, email):
    # Update session data
    scope_manager = ScopeManager(db, email)
    authorize_session(await scope_manager.get_user_scopes_dict())
