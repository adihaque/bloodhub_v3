import unittest
from bloodhub.domain.ranking import calculate_candidate_score

class TestCandidateRanking(unittest.TestCase):
    def test_exact_match_priority(self):
        score_exact = calculate_candidate_score(
            donor_blood_group="B+",
            recipient_blood_group="B+",
            distance_km=2.0,
            max_radius_km=5.0
        )
        score_compat = calculate_candidate_score(
            donor_blood_group="O+",
            recipient_blood_group="B+",
            distance_km=2.0,
            max_radius_km=5.0
        )
        # Exact match should receive higher points than compatible alternative
        self.assertGreater(score_exact["total_score"], score_compat["total_score"])
        self.assertEqual(score_exact["breakdown"]["compatibility_points"], 40.0)
        self.assertEqual(score_compat["breakdown"]["compatibility_points"], 25.0)

    def test_distance_proximity_scaling(self):
        # Donor closer to hospital receives more proximity points
        score_near = calculate_candidate_score("B+", "B+", distance_km=1.0, max_radius_km=10.0)
        score_far = calculate_candidate_score("B+", "B+", distance_km=8.0, max_radius_km=10.0)
        self.assertGreater(score_near["breakdown"]["proximity_points"], score_far["breakdown"]["proximity_points"])

if __name__ == '__main__':
    unittest.main()

    def test_dynamic_reweighting(self):
        class MockConfig:
            compatibility_exact_pts = 60.0
            compatibility_compatible_pts = 10.0
            proximity_weight_pts = 20.0
            reliability_weight_pts = 10.0
            interval_weight_pts = 5.0
            intent_regular_bonus = 5.0
            intent_when_needed_bonus = 0.0

        cfg = MockConfig()
        score = calculate_candidate_score("B+", "B+", distance_km=2.0, max_radius_km=10.0, config=cfg)
        self.assertEqual(score["breakdown"]["compatibility_points"], 60.0)
        self.assertEqual(score["breakdown"]["intent_points"], 5.0)

    def test_donation_intent_bonus(self):
        score_reg = calculate_candidate_score("B+", "B+", distance_km=1.0, max_radius_km=10.0, donation_intent="REGULAR")
        score_later = calculate_candidate_score("B+", "B+", distance_km=1.0, max_radius_km=10.0, donation_intent="DONATE_LATER")
        self.assertGreater(score_reg["breakdown"]["intent_points"], score_later["breakdown"]["intent_points"])
