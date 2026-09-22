"""
One-time admin seed for the SINGLE analyst login.

The password is passed at runtime and hashed with bcrypt before storage — it is
never written into the codebase or .env. Any pre-existing users are removed, so
exactly one credential can ever log in.

Usage (inside the backend container):
    python -m scripts.seed_user <email> <password>
"""

import sys

import bcrypt

from app.db import SessionLocal
from app.models import User


def main():
    if len(sys.argv) != 3:
        print("usage: python -m scripts.seed_user <email> <password>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    password = sys.argv[2]

    db = SessionLocal()
    try:
        removed = db.query(User).delete()  # enforce a single user
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.add(User(email=email, password_hash=pw_hash))
        db.commit()
        total = db.query(User).count()
        print(f"removed {removed} existing user(s); seeded {email}; total users = {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
