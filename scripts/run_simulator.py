#!/usr/bin/env python3
"""
Blood Hub Interactive CLI Simulator
Allows testing dispatch waves, timeouts, donor accept/reject, and concurrency races from the terminal.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bloodhub.core.database import SessionLocal
from bloodhub.models.models import create_all
from bloodhub.api.simulator import (
    seed_simulator_data, trigger_test_request, get_simulator_state,
    simulate_donor_accept, simulate_wave_timeout, simulate_concurrent_accept_race
)

def print_status(db):
    state = get_simulator_state(db)
    print("\n--- Current Simulator State ---")
    print("Donors:")
    for d in state["donors"]:
        offer_str = f"[ALERT PENDING: {d['active_offer_id'][:8]}]" if d["active_offer_id"] else ""
        print(f"  {d['name']} ({d['blood_group']}) - Status: {d['status']} {offer_str}")
    print("\nRequests:")
    for r in state["requests"]:
        print(f"  {r['patient_name']} - {r['blood_group']} at {r['hospital_name']} | Status: {r['status']} (Wave {r['current_wave']}, Fulfilled: {r['units_fulfilled']}/{r['units_needed']})")
    print("--------------------------------\n")

def main():
    create_all()
    db = SessionLocal()
    print("==================================================")
    print("   BLOOD HUB - LOCAL DISPATCH SIMULATOR")
    print("==================================================")
    
    seed_simulator_data(db)
    print("✓ Environment initialized with seed data.")
    print_status(db)

    print("Step 1: Triggering Emergency Blood Request for B+ at Square Hospital...")
    res = trigger_test_request(db)
    print("✓ Request Triggered! Request ID:", res["request_id"])
    print_status(db)

    print("Step 2: Testing Simultaneous Acceptance (Concurrency Race Condition)...")
    race_res = simulate_concurrent_accept_race()
    print("✓ Race Executed!")
    print(f"  Strict Concurrency Guarantee Verified: {race_res['guarantee_verified']}")
    print(f"  Winners: {race_res['winners_count']} | Losers: {race_res['losers_count']}")
    if race_res["winner_details"]:
        print("  Winner:", race_res["winner_details"]["message"])
    if race_res["loser_details"]:
        print("  Loser Rejection:", race_res["loser_details"]["message"])

    print_status(db)
    db.close()
    print("Simulation completed successfully!")

if __name__ == "__main__":
    main()
