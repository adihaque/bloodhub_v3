#!/usr/bin/env python3
"""
Seed realistic development and testing data for Blood Hub.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bloodhub.core.database import SessionLocal
from bloodhub.models.models import create_all
from bloodhub.api.simulator import seed_simulator_data

def main():
    print("Initializing Blood Hub database schema...")
    create_all()
    db = SessionLocal()
    try:
        print("Seeding demo users, donors, requesters, and blood centers...")
        res = seed_simulator_data(db)
        print("Success:", res["message"])
        print("\nDemo Accounts Created:")
        print("  Requester: +8801711111111 (pass: requester123)")
        print("  Donor A (B+, 0.04km): +8801722222222 (pass: donor123)")
        print("  Donor B (B+, 1.1km):  +8801733333333 (pass: donor123)")
        print("  Donor C (O+, 2.1km):  +8801744444444 (pass: donor123)")
        print("  Admin:     +8801700000000 (pass: admin123)")
    finally:
        db.close()

if __name__ == "__main__":
    main()
