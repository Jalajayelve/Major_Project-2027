"""Run with an interpreter containing pandas and scikit-learn; no inference."""
import unittest

from meridian.services.agent2_worker import retrieve_candidates


class CatalogTests(unittest.TestCase):
    def test_degree_filters_and_ranked_real_catalog_candidates(self):
        for degree, field in (("MS", "Computer Science"), ("MBA", "Business")):
            with self.subTest(degree=degree):
                rows = retrieve_candidates({"degree": degree, "field": field})
                self.assertGreater(len(rows), 0)
                self.assertLessEqual(len(rows), 20)
                self.assertTrue((rows.degree_type == degree).all())
                self.assertTrue((rows.similarity > 0).all())
                self.assertTrue(rows.similarity.is_monotonic_decreasing)
                self.assertTrue(rows.program_id.is_unique)

    def test_unknown_field_does_not_match_only_degree_token(self):
        rows = retrieve_candidates({"degree": "MS", "field": "zzzzunavailablefield"})
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
