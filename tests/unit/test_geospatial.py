import unittest
from bloodhub.domain.geospatial import haversine_distance, fuzz_donor_location

class TestGeospatial(unittest.TestCase):
    def test_haversine_accuracy(self):
        # Distance between Square Hospital (Panthapath) and BSMMU (Shahbag) in Dhaka is ~2.1 km
        dist = haversine_distance(23.7533, 90.3817, 23.7388, 90.3957)
        self.assertAlmostEqual(dist, 2.15, delta=0.3)

    def test_haversine_same_point(self):
        dist = haversine_distance(23.8103, 90.4125, 23.8103, 90.4125)
        self.assertEqual(dist, 0.0)

    def test_location_fuzzing(self):
        orig_lat, orig_lon = 23.7533, 90.3817
        fuzzed_lat, fuzzed_lon = fuzz_donor_location(orig_lat, orig_lon, fuzz_radius_meters=1000.0)
        dist = haversine_distance(orig_lat, orig_lon, fuzzed_lat, fuzzed_lon)
        # Must be within 1.2 km of original point but not identical
        self.assertLessEqual(dist, 1.2)

if __name__ == '__main__':
    unittest.main()
