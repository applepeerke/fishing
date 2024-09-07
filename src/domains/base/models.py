from datetime import datetime

from fastapi import HTTPException, Response
from pydantic import BaseModel
from pydantic import Field, model_validator, ConfigDict
from sqlalchemy import Column, DateTime, String, func, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr
from starlette import status


class AuditMixin(object):
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), default=func.now())

    @declared_attr
    def created_by(cls):
        return Column(String, default=get_session_user())

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    @declared_attr
    def updated_by(cls):
        return Column(String, nullable=True, onupdate=get_session_user())

    @declared_attr
    def update_count(cls):
        return Column(Integer)


class Base(AsyncAttrs, AuditMixin, DeclarativeBase):
    pass


def get_session_user():
    return 'dummy@sample.com'


def get_delete_response(success: bool, table_name):
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{table_name} record was not found')
    return Response(status_code=status.HTTP_200_OK, content=f'The {table_name} record has been deleted.')
