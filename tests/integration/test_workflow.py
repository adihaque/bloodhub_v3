import unittest
from bloodhub.core.database import SessionLocal
from bloodhub.models.models import create_all, User, BloodRequest, DonorOffer, Assignment
from bloodhub.api.simulator import seed_simulator_data
from bloodhub.engine.dispatcher import start_dispatch, progress_wave
from bloodhub.engine.concurrency import atomic_accept_offer

class TestEndToEndWorkflow(unittest.TestCase):
    def setUp(self):
        create_all()
        self.db = SessionLocal()
        seed_simulator_data(self.db)

    def tearDown(self):
        self.db.close()

    def test_request_dispatch_and_acceptance(self):
        # 1. Fetch seeded requester
        requester = self.db.query(User).filter_by(phone="+8801711111111").first()
        self.assertIsNotNone(requester)

        # 2. Create Blood Request for B+ at Square Hospital
        req = BloodRequest(
            requester_id=requester.id,
            patient_name="Integration Test Patient",
            blood_group="B+",
            component="WHOLE_BLOOD",
            units_needed=1,
            units_fulfilled=0,
            urgency="URGENT",
            hospital_name="Square Hospital",
            latitude=23.7533,
            longitude=90.3817,
            contact_phone="+8801711111111",
            status="ACTIVE"
        )
        self.db.add(req)
        self.db.commit()

        # 3. Start Wave 1 Dispatch
        wave1 = start_dispatch(self.db, req.id)
        self.assertIsNotNone(wave1)
        self.assertEqual(wave1.wave_number, 1)
        self.assertGreater(wave1.candidate_count, 0)

        # 4. Check that offers were emitted
        offers = self.db.query(DonorOffer).filter_by(request_id=req.id).all()
        self.assertEqual(len(offers), wave1.candidate_count)
        self.assertTrue(all(o.status == "OFFERED" for o in offers))

        # 5. One donor accepts
        winning_offer = offers[0]
        res = atomic_accept_offer(self.db, offer_id=winning_offer.id, donor_id=winning_offer.donor_id)
        self.assertTrue(res["success"])
        self.assertEqual(res["code"], "ASSIGNED_SUCCESS")

        # 6. Verify assignment created and other offers revoked
        self.db.refresh(req)
        self.assertEqual(req.status, "ASSIGNED")
        self.assertEqual(req.units_fulfilled, 1)

        assignment = self.db.query(Assignment).filter_by(request_id=req.id).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.donor_id, winning_offer.donor_id)

        # Competing offers must be REVOKED
        other_offers = self.db.query(DonorOffer).filter("request_id = ? AND id != ?", [req.id, winning_offer.id]).all()
        for off in other_offers:
            self.assertEqual(off.status, "REVOKED")

if __name__ == '__main__':
    unittest.main()
