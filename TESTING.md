# Blood Hub: Automated Testing Specification

Blood Hub maintains an automated test suite covering unit rules, integration flows, and multi-threaded race conditions.

---

## Running Tests

Run all tests via Python's standard `unittest`:
```bash
python3 -m unittest discover -s tests -v
```

---

## Test Suites

1. **Unit Tests (`tests/unit/`)**:
   - `test_compatibility.py`: Validates ABO/Rh red cell and plasma compatibility matrix.
   - `test_eligibility.py`: Validates weight (>50kg), age (18-60), and 90-day cooldown rules.
   - `test_ranking.py`: Validates deterministic 0-100 score computation and exact-match priority.
   - `test_state_machines.py`: Enforces valid state transitions and asserts `StateTransitionError` on illegal moves.
   - `test_geospatial.py`: Verifies Haversine formula precision and location fuzzing bounds.

2. **Integration Tests (`tests/integration/`)**:
   - `test_workflow.py`: Exercises request creation, wave 1 dispatch, candidate ranking, offer generation, acceptance, assignment locking, and competing offer revocation.

3. **Concurrency Tests (`tests/concurrency/`)**:
   - `test_concurrency_race.py`: Spawns concurrent threads using `concurrent.futures.ThreadPoolExecutor` to simulate two donors clicking Accept at the exact same millisecond. Asserts strictly ONE winner and ONE loser with no orphaned assignments.
