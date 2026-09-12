#!/usr/bin/env python3
"""Operator bootstrap: create (or update the password of) one login-capable
user, so the dashboard's authenticated download route has something to log
into. This is NOT sample survey data -- BUILD_SPEC explicitly forbids that;
this is the one operational step a fresh, empty database still needs.

Usage:
    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=... python tools/seed_admin.py
    python tools/seed_admin.py --email you@example.com --password ... --role admin
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db.client import get_db  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    parser.add_argument("--name", default=os.environ.get("ADMIN_NAME", "Admin"))
    parser.add_argument("--role", default="admin", choices=["admin", "manager", "engineer", "viewer"])
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("--email/--password (or ADMIN_EMAIL/ADMIN_PASSWORD) are required")

    db = get_db()
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"email": args.email},
        {
            "$set": {
                "email": args.email,
                "display_name": args.name,
                "role": args.role,
                "password_hash": hash_password(args.password),
                "is_active": True,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    print(f"ok: {args.email} ({args.role})")


if __name__ == "__main__":
    asyncio.run(main())
