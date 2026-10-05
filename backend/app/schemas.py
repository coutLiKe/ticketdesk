from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import Role


class UserCreate(BaseModel):
    """What a client may send to register. There is deliberately no `role` field:
    Pydantic ignores unknown fields, so a client can't pick their own role."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        # bcrypt only looks at the first 72 BYTES; refuse longer ones instead of
        # silently truncating them.
        if len(value.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """What the API returns about a user. The password hash is not a field, so it can
    never leak, even by accident."""

    model_config = ConfigDict(from_attributes=True)  # allow building from ORM objects

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if self.role is None and self.is_active is None:
            raise ValueError("provide role and/or is_active")
        return self
