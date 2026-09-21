import unittest
from bloodhub.domain.compatibility import (
    get_compatible_donor_groups, is_compatible, normalize_blood_group
)

class TestBloodCompatibility(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_blood_group("b_positive"), "B+")
        self.assertEqual(normalize_blood_group("O-"), "O-")
        self.assertEqual(normalize_blood_group("AB+"), "AB+")

    def test_universal_donor_red_cells(self):
        # O- can donate red cells to every blood group
        all_groups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
        for g in all_groups:
            self.assertTrue(is_compatible(donor_group="O-", recipient_group=g, component="WHOLE_BLOOD"))

    def test_universal_recipient_red_cells(self):
        # AB+ can receive red cells from every blood group
        all_groups = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
        compat = get_compatible_donor_groups("AB+", component="WHOLE_BLOOD")
        for g in all_groups:
            self.assertIn(g, compat)

    def test_incompatible_combinations(self):
        # B+ cannot donate red cells to A+
        self.assertFalse(is_compatible(donor_group="B+", recipient_group="A+"))
        # A+ cannot donate red cells to O+
        self.assertFalse(is_compatible(donor_group="A+", recipient_group="O+"))
        # AB+ cannot donate red cells to B+
        self.assertFalse(is_compatible(donor_group="AB+", recipient_group="B+"))

    def test_plasma_compatibility(self):
        # In plasma, AB is the universal donor, O is universal recipient
        self.assertTrue(is_compatible(donor_group="AB+", recipient_group="O+", component="PLASMA"))
        self.assertTrue(is_compatible(donor_group="AB+", recipient_group="A+", component="PLASMA"))

if __name__ == '__main__':
    unittest.main()
