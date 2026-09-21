import unittest
from datetime import date, timedelta
from bloodhub.domain.eligibility import check_donor_eligibility, calculate_age

class TestDonorEligibility(unittest.TestCase):
    def test_age_calculation(self):
        self.assertIsNone(calculate_age(None))
        self.assertEqual(calculate_age("invalid-date"), None)
        # 20 years old
        twenty_yrs_ago = (date.today() - timedelta(days=20*365 + 5)).strftime("%Y-%m-%d")
        age = calculate_age(twenty_yrs_ago)
        self.assertEqual(age, 20)

    def test_weight_threshold(self):
        # Weight below 50kg fails
        ok, reason = check_donor_eligibility("AVAILABLE", weight_kg=48.0)
        self.assertFalse(ok)
        self.assertIn("minimum platform threshold", reason)

        # Weight 50kg or above passes
        ok, reason = check_donor_eligibility("AVAILABLE", weight_kg=55.0)
        self.assertTrue(ok)

    def test_availability_and_assignment(self):
        # UNAVAILABLE fails
        ok, reason = check_donor_eligibility("UNAVAILABLE", weight_kg=65.0)
        self.assertFalse(ok)

        # Active assignment fails
        ok, reason = check_donor_eligibility("AVAILABLE", weight_kg=65.0, active_assignment_id="some-id")
        self.assertFalse(ok)
        self.assertIn("assigned to another active emergency", reason)

    def test_cooldown_interval(self):
        # Recent donation 30 days ago fails for whole blood (needs 90 days)
        recent_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        ok, reason = check_donor_eligibility("AVAILABLE", weight_kg=65.0, last_donation_date_str=recent_date)
        self.assertFalse(ok)
        self.assertIn("cooldown active", reason)

        # Past donation 100 days ago passes
        past_date = (date.today() - timedelta(days=100)).strftime("%Y-%m-%d")
        ok, reason = check_donor_eligibility("AVAILABLE", weight_kg=65.0, last_donation_date_str=past_date)
        self.assertTrue(ok)

if __name__ == '__main__':
    unittest.main()
