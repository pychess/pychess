import unittest

from utilities.yacpdb_probe import classify, composer_query, entry_id


class YacpdbProbeTest(unittest.TestCase):
    def test_composer_query_escapes_ql_string(self):
        self.assertEqual(
            composer_query('Doe, John "Jack"'),
            'Author("Doe, John \\"Jack\\"%")',
        )

    def test_direct_mate_with_orthodox_position_and_solution_is_candidate(self):
        entry = {
            "id": 1862,
            "stipulation": "#3",
            "algebraic": {
                "white": ["Ka7", "Qh6", "Be4", "Sd7", "Pe5"],
                "black": ["Kg8", "Rg7", "Pe7", "Pe6"],
            },
            "solution": "1.Qh6-h1 !\n  1...Rg7-g6\n    2.Be4*g6",
        }

        self.assertEqual(classify(entry), ("candidate",))

    def test_options_are_reported_without_rejecting_core_candidate(self):
        entry = {
            "id": 1,
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1"], "black": ["Kh8"]},
            "solution": "1.Ka1-b1",
            "options": ["Some option"],
        }

        self.assertEqual(classify(entry), ("candidate", "has-options"))

    def test_fairy_piece_is_not_candidate(self):
        entry = {
            "id": 2,
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1", "Na2"], "black": ["Kh8"]},
            "solution": "1.Na2-b4",
        }

        self.assertEqual(classify(entry), ("non-orthodox-piece",))

    def test_entry_id_accepts_numeric_string(self):
        self.assertEqual(entry_id({"id": "123"}), 123)
        self.assertIsNone(entry_id({"id": "not-an-id"}))


if __name__ == "__main__":
    unittest.main()
