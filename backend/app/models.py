import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(enum.StrEnum):
    REQUESTER = "requester"
    TECHNICIAN = "technician"
    ADMIN = "admin"


class TicketStatus(enum.StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AssetType(enum.StrEnum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    PHONE = "phone"
    OTHER = "other"


class AssetStatus(enum.StrEnum):
    IN_STOCK = "in_stock"
    ASSIGNED = "assigned"
    RETIRED = "retired"


def enum_column(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Store an enum as VARCHAR plus a CHECK constraint, using the lowercase values.

    Native Postgres ENUM types are awkward to change in migrations (adding a value needs
    special SQL), so a plain string column with a CHECK constraint is easier to evolve.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [member.value for member in e],
    )


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# Pure link table for the many-to-many between tickets and assets.
# The composite primary key makes it impossible to link the same pair twice.
ticket_assets = Table(
    "ticket_assets",
    Base.metadata,
    Column("ticket_id", ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
    Column("asset_id", ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column(Role, "role"), default=Role.REQUESTER)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at_column()


class Ticket(Base):
    __tablename__ = "tickets"
    # Filtering by these columns is the main read pattern, so index them.
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_requester_id", "requester_id"),
        Index("ix_tickets_assignee_id", "assignee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        enum_column(TicketStatus, "ticket_status"), default=TicketStatus.OPEN
    )
    priority: Mapped[Priority] = mapped_column(
        enum_column(Priority, "priority"), default=Priority.MEDIUM
    )
    # RESTRICT: you can't delete a user who still has tickets. (We deactivate users instead.)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Nullable: a new ticket has no assignee. SET NULL: deleting a technician unassigns.
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Two foreign keys point at users, so each relationship must say which one it follows.
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    assets: Mapped[list["Asset"]] = relationship(secondary=ticket_assets, back_populates="tickets")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_ticket_id", "ticket_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # CASCADE: comments have no meaning without their ticket, so they go with it.
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    ticket: Mapped[Ticket] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (Index("ix_assets_assigned_user_id", "assigned_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_tag: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[AssetType] = mapped_column(enum_column(AssetType, "asset_type"))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[AssetStatus] = mapped_column(
        enum_column(AssetStatus, "asset_status"), default=AssetStatus.IN_STOCK
    )
    assigned_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at_column()

    assigned_user: Mapped[User | None] = relationship()
    tickets: Mapped[list[Ticket]] = relationship(secondary=ticket_assets, back_populates="assets")
