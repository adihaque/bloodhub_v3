import unittest
import concurrent.futures
from bloodhub.core.database import SessionLocal
from bloodhub.models.models import create_all, User, BloodRequest, DonorOffer, Assignment
from bloodhub.api.simulator import seed_simulator_data
from bloodhub.engine.dispatcher import start_dispatch
from bloodhub.engine.concurrency import atomic_accept_offer

class TestConcurrencyRace(unittest.TestCase):
    def setUp(self):
        create_all()
        self.db = SessionLocal()
        seed_simulator_data(self.db)

    def tearDown(self):
        self.db.close()

    def test_simultaneous_acceptance_strictly_one_winner(self):
        # Create a single-unit request
        requester = self.db.query(User).filter_by(phone="+8801711111111").first()
        req = BloodRequest(
            requester_id=requester.id,
            patient_name="Race Condition Test Patient",
            blood_group="B+",
            units_needed=1,
            units_fulfilled=0,
            urgency="CRITICAL_IMMEDIATE",
            hospital_name="Square Hospital",
            latitude=23.7533,
            longitude=90.3817,
            contact_phone="+8801711111111",
            status="ACTIVE"
        )
        self.db.add(req)
        self.db.commit()

        start_dispatch(self.db, req.id)

        # Get 2 active offers targeting this request
        offers = self.db.query(DonorOffer).filter(
            "request_id = ? AND status = 'OFFERED'", [req.id]
        ).all()
        self.assertGreaterEqual(len(offers), 2, "Need at least 2 active offers to test concurrency")

        offer1 = offers[0]
        offer2 = offers[1]

        results = []

        def worker(offer_id, donor_id, thread_label):
            thread_db = SessionLocal()
            try:
                outcome = atomic_accept_offer(thread_db, offer_id, donor_id)
                outcome["thread"] = thread_label
                results.append(outcome)
            finally:
                thread_db.close()

        # Run both acceptances concurrently in separate threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker, offer1.id, offer1.donor_id, "Thread-1")
            f2 = executor.submit(worker, offer2.id, offer2.donor_id, "Thread-2")
            concurrent.futures.wait([f1, f2])

        # Assertions
        winners = [r for r in results if r["success"] is True]
        losers = [r for r in results if r["success"] is False]

        self.assertEqual(len(winners), 1, "There must be EXACTLY ONE winner of the assignment")
        self.assertEqual(len(losers), 1, "The competing donor must receive a graceful conflict/revocation response")
        self.assertTrue("REVOKED" in losers[0]["message"] or "Already fulfilled" in losers[0]["message"] or losers[0]["code"] in ("OFFER_INVALID_STATE", "REQUEST_ALREADY_FULFILLED", "ALL_UNITS_CLAIMED"))

        # Database verification: strictly one active assignment
        assignments = self.db.query(Assignment).filter_by(request_id=req.id).all()
        self.assertEqual(len(assignments), 1)

if __name__ == '__main__':
    unittest.main()
