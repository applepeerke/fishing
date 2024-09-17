import contextvars

from sqlalchemy import Column, DateTime, String, func, Integer
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

from src.constants import UNKNOWN
from src.domains.token.models import SessionData

# Create a context variable for the authorization_token
session_token_var = contextvars.ContextVar('session_token')


class AuditMixin(object):
    created_at = Column(DateTime(timezone=True), default=func.now())
    created_by = Column(String)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String, nullable=True)
    update_count = Column(Integer)

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
    #
    # @declared_attr
    # def update_count(self):
    #     return Column(Integer)


class Base(AsyncAttrs, AuditMixin, DeclarativeBase):
    pass


def set_created_by(mapper, connection, target):
    """ Event listener """
    # Get the current user from the context variable
    token_data: SessionData = session_token_var.get(None)
    target.created_by = token_data.email if token_data else UNKNOWN


def set_updated_by(mapper, connection, target):
    """ Event listener """
    token_data: SessionData = session_token_var.get(None)
    target.updated_by = token_data.email if token_data else UNKNOWN


# Attach event listeners to SQLAlchemy models
event.listen(AuditMixin, 'before_insert', set_created_by, propagate=True)
event.listen(AuditMixin, 'before_update', set_updated_by, propagate=True)
