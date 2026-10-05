"""Promote an existing user to admin. Run with:  python -m app.make_admin you@example.com

This is how the first admin is created in a real deployment (instead of the demo seed):
register normally through the app, then promote that account. No password is ever typed
into a command line.
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Role, User


def promote_to_admin(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise LookupError(f"No user with email {email!r}. Register in the app first.")
    user.role = Role.ADMIN
    user.is_active = True
    db.commit()
    return user


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.make_admin <email>")
    with SessionLocal() as db:
        try:
            user = promote_to_admin(db, sys.argv[1])
        except LookupError as error:
            sys.exit(str(error))
    print(f"{user.email} is now an admin.")


if __name__ == "__main__":
    main()
