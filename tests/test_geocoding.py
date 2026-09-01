"""Unit tests for Dynamic Geocoding Service."""

import unittest

from geocoding import clear_geocode_cache, geocode_city


class GeocodingServiceTests(unittest.TestCase):
    """Verify arbitrary city resolution and error handling."""

    def setUp(self):
        clear_geocode_cache()

    def test_geocode_pune(self):
        res = geocode_city("Pune")
        self.assertEqual(res["city"], "Pune")
        self.assertAlmostEqual(res["latitude"], 18.51957, delta=0.1)
        self.assertAlmostEqual(res["longitude"], 73.85535, delta=0.1)
        self.assertEqual(res["country"], "India")

    def test_geocode_multiple_arbitrary_cities(self):
        test_cities = ["Mumbai", "Delhi", "Jaipur", "Kochi", "Nagpur", "Ahmedabad", "Tokyo", "London"]
        for city in test_cities:
            res = geocode_city(city)
            self.assertIn("latitude", res)
            self.assertIn("longitude", res)
            self.assertTrue(-90 <= res["latitude"] <= 90)
            self.assertTrue(-180 <= res["longitude"] <= 180)
            self.assertTrue(len(res["country"]) > 0)

    def test_geocoding_cache_reuse(self):
        res1 = geocode_city("Pune")
        # Second call should return cached payload without error
        res2 = geocode_city("Pune")
        self.assertEqual(res1, res2)

    def test_empty_city_error(self):
        with self.assertRaises(ValueError):
            geocode_city("")
        with self.assertRaises(ValueError):
            geocode_city("   ")

    def test_unknown_city_not_found(self):
        with self.assertRaises(ValueError) as ctx:
            geocode_city("NonExistentCityXYZ998877112233")
        self.assertIn("City not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()


