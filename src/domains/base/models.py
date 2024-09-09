import contextvars

from sqlalchemy import Column, DateTime, String, func, Integer
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr

from src.constants import UNKNOWN
from src.domains.token.models import AccessTokenData

# Create a context variable for the current user
current_user_var = contextvars.ContextVar('current_user')


class AuditMixin(object):
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(String)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String, nullable=True)
    # @declared_attr
    # def created_at(self):
    #     return Column(DateTime(timezone=True), default=func.now())
    #
    # @declared_attr
    # def created_by(self):
    #     return Column(String)
    #
    # @declared_attr
    # def updated_at(self):
    #     return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    #
    # @declared_attr
    # def updated_by(self):
    #     return Column(String, nullable=True)

    @declared_attr
    def update_count(self):
        return Column(Integer)


class Base(AsyncAttrs, AuditMixin, DeclarativeBase):
    pass


def set_created_by(mapper, connection, target):
    """ Event listener """
    # Get the current user from the context variable
    user: AccessTokenData = current_user_var.get(None)
    target.created_by = user.email if user else UNKNOWN


def set_updated_by(mapper, connection, target):
    """ Event listener """
    user: AccessTokenData = current_user_var.get(None)
    target.updated_by = user.email if user else UNKNOWN


# Attach event listeners to SQLAlchemy models
event.listen(AuditMixin, 'before_insert', set_created_by, propagate=True)
event.listen(AuditMixin, 'before_update', set_updated_by, propagate=True)
