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
