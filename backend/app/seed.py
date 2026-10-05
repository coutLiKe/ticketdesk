"""Demo data. Run with:  python -m app.seed

Safe to run repeatedly: every record is looked up first and only created if missing.
Demo users all share one well-known password, so NEVER run this against a real deployment.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Asset,
    AssetStatus,
    AssetType,
    Comment,
    Priority,
    Role,
    Ticket,
    TicketStatus,
    User,
)
from app.security import hash_password

DEMO_PASSWORD = "demo1234"

USERS = [
    # email, full name, role
    ("admin@ticketdesk.dev", "Ada Admin", Role.ADMIN),
    ("tom@ticketdesk.dev", "Tom Technician", Role.TECHNICIAN),
    ("tina@ticketdesk.dev", "Tina Technician", Role.TECHNICIAN),
    ("rita@ticketdesk.dev", "Rita Requester", Role.REQUESTER),
    ("raj@ticketdesk.dev", "Raj Requester", Role.REQUESTER),
    ("rosa@ticketdesk.dev", "Rosa Requester", Role.REQUESTER),
]

# tag, name, type, serial, assigned-to email (None = in stock), retired?
ASSETS = [
    ("LT-0001", "MacBook Pro 14", AssetType.LAPTOP, "C02AB1CD", "rita@ticketdesk.dev", False),
    ("LT-0002", "ThinkPad X1 Carbon", AssetType.LAPTOP, "PF3XY7Q2", "raj@ticketdesk.dev", False),
    ("LT-0003", "MacBook Air 13", AssetType.LAPTOP, "FVFH93K1", "rosa@ticketdesk.dev", False),
    ("LT-0004", "Dell Latitude 7440", AssetType.LAPTOP, "7QK2M44", None, False),
    ("MN-0001", "Dell UltraSharp 27", AssetType.MONITOR, "CN0P8821", "rita@ticketdesk.dev", False),
    ("MN-0002", "LG 34 Ultrawide", AssetType.MONITOR, "402NTAB9", "raj@ticketdesk.dev", False),
    ("PH-0001", "iPhone 15", AssetType.PHONE, "DX3L2PQ9", "rosa@ticketdesk.dev", False),
    ("DT-0001", "HP EliteDesk 800", AssetType.DESKTOP, "MXL1234ZZ", None, False),
    ("LT-0000", "Old ThinkPad T450", AssetType.LAPTOP, "PC0LD450", None, True),
]

# title, description, requester, status, priority, assignee, days ago, asset tags,
# comments as (author email, text, internal?)
TICKETS = [
    (
        "VPN keeps disconnecting",
        "My VPN drops every 10-15 minutes while I am working from home.",
        "rita@ticketdesk.dev",
        TicketStatus.IN_PROGRESS,
        Priority.HIGH,
        "tom@ticketdesk.dev",
        6,
        ["LT-0001"],
        [
            ("tom@ticketdesk.dev", "Can you tell me which VPN client version you have?", False),
            ("rita@ticketdesk.dev", "Version 5.2.1, on macOS 14.", False),
            ("tom@ticketdesk.dev", "Known bug in 5.2.1 on Sonoma. Pushing 5.2.4 to her.", True),
        ],
    ),
    (
        "Monitor flickers when docked",
        "The external monitor flickers every few seconds when connected to the dock.",
        "raj@ticketdesk.dev",
        TicketStatus.OPEN,
        Priority.MEDIUM,
        None,
        5,
        ["MN-0002", "LT-0002"],
        [],
    ),
    (
        "Cannot print to 3rd floor printer",
        "Jobs sit in the queue and never print. Other floors work fine.",
        "rosa@ticketdesk.dev",
        TicketStatus.RESOLVED,
        Priority.LOW,
        "tina@ticketdesk.dev",
        9,
        [],
        [
            ("tina@ticketdesk.dev", "Print server had a stuck job. Cleared the queue.", False),
            ("rosa@ticketdesk.dev", "Working again, thank you!", False),
        ],
    ),
    (
        "Need access to the shared finance drive",
        "I started in finance this week and cannot open the shared drive.",
        "raj@ticketdesk.dev",
        TicketStatus.CLOSED,
        Priority.MEDIUM,
        "tom@ticketdesk.dev",
        14,
        [],
        [
            ("tom@ticketdesk.dev", "Added you to the Finance-Read group.", False),
            ("raj@ticketdesk.dev", "I can see it now.", False),
        ],
    ),
    (
        "Laptop battery drains in an hour",
        "Battery went from 100% to 5% in about an hour of light browsing.",
        "rosa@ticketdesk.dev",
        TicketStatus.IN_PROGRESS,
        Priority.URGENT,
        "tina@ticketdesk.dev",
        3,
        ["LT-0003"],
        [
            ("tina@ticketdesk.dev", "Battery health shows 62%. Likely needs replacing.", True),
            ("tina@ticketdesk.dev", "We will swap the battery. Can you come by desk 12?", False),
        ],
    ),
    (
        "Request: install Docker Desktop",
        "I need Docker Desktop for a new project. My manager approved it.",
        "rita@ticketdesk.dev",
        TicketStatus.OPEN,
        Priority.LOW,
        None,
        2,
        ["LT-0001"],
        [],
    ),
    (
        "Email signature missing logo",
        "New signature template shows a broken image for the company logo.",
        "raj@ticketdesk.dev",
        TicketStatus.OPEN,
        Priority.LOW,
        None,
        1,
        [],
        [],
    ),
    (
        "Phone cannot connect to office Wi-Fi",
        "My phone says 'incorrect password' but other devices connect fine.",
        "rosa@ticketdesk.dev",
        TicketStatus.RESOLVED,
        Priority.MEDIUM,
        "tom@ticketdesk.dev",
        7,
        ["PH-0001"],
        [
            ("tom@ticketdesk.dev", "Device certificate had expired. Re-enrolled the phone.", False),
        ],
    ),
    (
        "Suspicious email, possible phishing",
        "I got an email asking me to confirm my payroll details. I did not click anything.",
        "rita@ticketdesk.dev",
        TicketStatus.IN_PROGRESS,
        Priority.URGENT,
        "admin@ticketdesk.dev",
        1,
        [],
        [
            ("admin@ticketdesk.dev", "Confirmed phishing. Blocking sender domain org-wide.", True),
            (
                "admin@ticketdesk.dev",
                "Thanks for reporting. Please delete it, nothing else needed.",
                False,
            ),
        ],
    ),
    (
        "Replace broken keyboard",
        "Several keys on my keyboard stopped working after a coffee spill.",
        "raj@ticketdesk.dev",
        TicketStatus.CLOSED,
        Priority.LOW,
        "tina@ticketdesk.dev",
        20,
        ["LT-0002"],
        [("tina@ticketdesk.dev", "Replaced the top case. Closing.", False)],
    ),
    (
        "Slow desktop after update",
        "The desktop at reception takes five minutes to start since last week's update.",
        "rosa@ticketdesk.dev",
        TicketStatus.OPEN,
        Priority.HIGH,
        "tom@ticketdesk.dev",
        4,
        ["DT-0001"],
        [],
    ),
    (
        "Add second monitor",
        "Could I get a second monitor? I work with large spreadsheets.",
        "rita@ticketdesk.dev",
        TicketStatus.RESOLVED,
        Priority.LOW,
        "tina@ticketdesk.dev",
        10,
        ["MN-0001"],
        [("tina@ticketdesk.dev", "Delivered a Dell 27 to your desk.", False)],
    ),
]


def seed(db: Session) -> dict[str, int]:
    """Create any missing demo records. Returns how many of each were newly created."""
    created = {"users": 0, "assets": 0, "tickets": 0, "comments": 0}
    now = datetime.now(UTC)
    password_hash = hash_password(DEMO_PASSWORD)  # hashed once: each hash is deliberately slow

    users: dict[str, User] = {}
    for email, full_name, role in USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=full_name, role=role, hashed_password=password_hash)
            db.add(user)
            created["users"] += 1
        users[email] = user

    assets: dict[str, Asset] = {}
    for tag, name, type_, serial, owner_email, retired in ASSETS:
        asset = db.scalar(select(Asset).where(Asset.asset_tag == tag))
        if asset is None:
            if retired:
                status = AssetStatus.RETIRED
            else:
                status = AssetStatus.ASSIGNED if owner_email else AssetStatus.IN_STOCK
            asset = Asset(
                asset_tag=tag,
                name=name,
                type=type_,
                serial_number=serial,
                status=status,
                assigned_user=users[owner_email] if owner_email else None,
            )
            db.add(asset)
            created["assets"] += 1
        assets[tag] = asset

    db.flush()  # assign ids so tickets can look tickets up by requester

    for title, description, requester, status, priority, assignee, days, tags, comments in TICKETS:
        exists = db.scalar(
            select(Ticket.id).where(
                Ticket.title == title, Ticket.requester_id == users[requester].id
            )
        )
        if exists:
            continue
        opened = now - timedelta(days=days)
        ticket = Ticket(
            title=title,
            description=description,
            requester=users[requester],
            status=status,
            priority=priority,
            assignee=users[assignee] if assignee else None,
            created_at=opened,
            updated_at=opened + timedelta(hours=2),
            assets=[assets[t] for t in tags],
        )
        for offset, (author, text, internal) in enumerate(comments, start=1):
            ticket.comments.append(
                Comment(
                    author=users[author],
                    body=text,
                    is_internal=internal,
                    created_at=opened + timedelta(minutes=30 * offset),
                )
            )
            created["comments"] += 1
        db.add(ticket)
        created["tickets"] += 1

    db.commit()
    return created


def main() -> None:
    with SessionLocal() as db:
        created = seed(db)
    print("Seed complete. Newly created:", ", ".join(f"{n} {k}" for k, n in created.items()))
    print(f"Demo logins (password for all: {DEMO_PASSWORD}):")
    for email, _, role in USERS:
        print(f"  {role.value:<10} {email}")


if __name__ == "__main__":
    main()
