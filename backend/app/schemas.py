from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import AssetStatus, AssetType, Priority, Role, TicketStatus


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


# ---- Tickets -------------------------------------------------------------------------


class UserBrief(BaseModel):
    """Minimal public view of a user, safe to show to any ticket viewer (no email)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    role: Role


class TicketCreate(BaseModel):
    """Only title and description. Status, priority, requester and assignee are set by the
    server, so extra fields a client sends are ignored."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: Priority
    requester: UserBrief
    assignee: UserBrief | None
    created_at: datetime
    updated_at: datetime


class TicketPage(BaseModel):
    items: list[TicketRead]
    total: int  # matching tickets across ALL pages, so a UI can render page controls
    limit: int
    offset: int


class StatusUpdate(BaseModel):
    status: TicketStatus


class PriorityUpdate(BaseModel):
    priority: Priority


class AssigneeUpdate(BaseModel):
    # No default on purpose: the field must be present. `null` means "unassign".
    assignee_id: int | None


# ---- Comments ------------------------------------------------------------------------


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5_000)
    # Internal notes are for staff only. Requesters must not be able to create them.
    is_internal: bool = False

    @field_validator("body")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    author: UserBrief
    body: str
    is_internal: bool
    created_at: datetime


# ---- Assets --------------------------------------------------------------------------


class AssetCreate(BaseModel):
    """Status and assignee are not accepted here: they change only through their own
    endpoints, so an asset's status can't contradict who holds it."""

    asset_tag: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    type: AssetType
    serial_number: str | None = Field(default=None, max_length=100)

    @field_validator("asset_tag")
    @classmethod
    def normalise_tag(cls, value: str) -> str:
        value = value.strip().upper()  # "lt-100" and "LT-100" are the same asset
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("name")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("serial_number")
    @classmethod
    def blank_serial_is_none(cls, value: str | None) -> str | None:
        return (value or "").strip() or None


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    type: AssetType | None = None
    serial_number: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if self.name is None and self.type is None and self.serial_number is None:
            raise ValueError("provide name, type and/or serial_number")
        return self


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_tag: str
    name: str
    type: AssetType
    serial_number: str | None
    status: AssetStatus
    assigned_user: UserBrief | None
    created_at: datetime


class AssetPage(BaseModel):
    items: list[AssetRead]
    total: int
    limit: int
    offset: int


class AssetAssigneeUpdate(BaseModel):
    user_id: int | None  # required; null means "return to stock"
