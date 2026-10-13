"""
seed_demo_accounts.py
---------------------
Idempotently provisions the three fixed-UUID demo accounts needed for
Quick Login buttons in the QuantumSafeKYC local development UI.

Safe to run multiple times — existing accounts are updated, not recreated.
Never deletes records or alters roles beyond ISSUER/HOLDER/ADMIN.

Usage:
    cd D:\QuantumSafeKYC\backend
    ..\.venv\Scripts\python.exe seed_demo_accounts.py
"""

import sys
import os

# Ensure backend is on sys.path so all imports resolve
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from app import app
from models import db, User
from auth_utils import hash_password

# -----------------------------------------------------------------------
# Demo account definitions — LOCAL DEVELOPMENT ONLY
# Passwords are deliberately visible here; these accounts are NOT for
# production. Never use real credentials.
# -----------------------------------------------------------------------
DEMO_ACCOUNTS = [
    {
        "user_uuid": "750bd462-f771-468f-9cf8-a5d27b02a665",
        "role": "ADMIN",
        "password": "IssuerPass@2025!",
        "label": "Quick ADMIN",
    },
    {
        "user_uuid": "813502d0-5aed-4e60-a2bc-371316a63c1d",
        "role": "ISSUER",
        "password": "IssuerPass@2025!",
        "label": "Quick ISSUER",
    },
    {
        "user_uuid": "f53bf005-7ab1-41e5-9dc7-388a4ffde14c",
        "role": "HOLDER",
        "password": "IssuerPass@2025!",
        "label": "Quick HOLDER",
    },
]


def seed():
    with app.app_context():
        print("=" * 60)
        print("  QuantumSafeKYC — Demo Account Seed (LOCAL DEV ONLY)")
        print("=" * 60)

        for acc in DEMO_ACCOUNTS:
            user = User.query.filter_by(user_uuid=acc["user_uuid"]).first()
            new_hash = hash_password(acc["password"])

            if user is None:
                user = User(
                    user_uuid=acc["user_uuid"],
                    password_hash=new_hash,
                    role=acc["role"],
                    status="ACTIVE",
                )
                db.session.add(user)
                action = "CREATED"
            else:
                user.password_hash = new_hash
                user.status = "ACTIVE"
                # Do NOT change role if already set — preserve any manual admin
                if user.role != acc["role"]:
                    print(f"  WARNING: {acc['label']} role in DB is '{user.role}', "
                          f"expected '{acc['role']}' — NOT overwriting role to preserve intent")
                action = "UPDATED"

            db.session.commit()
            print(f"  [{action}] {acc['label']}  uuid={acc['user_uuid'][:8]}..."
                  f"  role={user.role}  status={user.status}")

        print("\n  All demo accounts are ready.")
        print("  Password for all Quick Login buttons: IssuerPass@2025!")
        print("=" * 60)


if __name__ == "__main__":
    seed()
