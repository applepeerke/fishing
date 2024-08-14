import uuid
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field, UUID4, model_validator, field_validator, ConfigDict
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from sqlalchemy import text, func
from sqlalchemy.orm import Mapped, mapped_column
from starlette import status


class UUIDModel(BaseModel):
    id: uuid.UUID
    # id: UUID4 = Field(nullable=False, primary_key=True, default_factory=uuid.uuid4)
    # id: UUID = Field(
    #     nullable=False,
    #     primary_key=True,
    #     server_default=func.gen_random_uuid()
    # )
    #
    # id: UUID = Field(
    #     default_factory=uuid4,
    #     primary_key=True,
    #     index=True,
    #     nullable=False,
    #     sa_column_kwargs={
    #         "server_default": text("gen_random_uuid()"),
    #         "unique": True
    #     }
    # )


def get_current_user():
    # Placeholder function to return the current user's ID
    # Replace with actual logic to get the current user's ID
    return "dummy_user"


def get_delete_response(success: bool, table_name):
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{table_name} record was not found')
    return StatusResponse(status_code=status.HTTP_200_OK, message=f'The {table_name} record has been deleted.')


def get_authorization_response(success: bool, name):
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f'The {name} is not valid.')
    return StatusResponse(status_code=status.HTTP_200_OK, message=f'The {name} is valid.')


class StatusResponse(BaseModel):
    status_code: int
    message: str


class AuditModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    created_by: str = Field(default_factory=get_current_user)
    updated_by: str = Field(default_factory=get_current_user)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode='before')
    def set_updated_by(cls, values):
        values['updated_by'] = get_current_user()
        return values

    @model_validator(mode='before')
    def set_updated_at(cls, values):
        values['updated_at'] = datetime.now()
        return values


# class TimestampModel(BaseModel):
#     created_at: datetime
#     updated_at: datetime
    # created_at: datetime = Field(
    #     default_factory=datetime.utcnow,
    #     nullable=False,
    #     # sa_column_kwargs={
    #     #     "server_default": text("current_timestamp(0)")
    #     # }
    # )
    #
    # updated_at: datetime = Field(
    #     default_factory=datetime.utcnow,
    #     nullable=False,
    #     # sa_column_kwargs={
    #     #     "server_default": text("current_timestamp(0)"),
    #     #     "onupdate": text("current_timestamp(0)")
    #     # }
    # )
