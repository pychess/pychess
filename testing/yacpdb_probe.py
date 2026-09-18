import unittest
from unittest.mock import patch

from utilities.yacpdb_probe import (
    audit_solutions,
    classify,
    composer_query,
    debug_page,
    entry_fen,
    entry_id,
    exact_position_query,
    fetch_query,
    query_url,
    result_count,
    solution_failure_category,
)


class YacpdbProbeTest(unittest.TestCase):
    def test_composer_query_escapes_ql_string(self):
        self.assertEqual(
            composer_query('Doe, John "Jack"'),
            'Author("Doe, John \\"Jack\\"%")',
        )

    def test_exact_position_query_matches_yacpdb_matrix_search(self):
        self.assertEqual(
            exact_position_query(
                ["Ka7", "Qh6", "Be4", "Sd7", "Pe5"],
                ["Kg8", "Rg7", "Pe7", "Pe6"],
            ),
            'MatrixExtended("wKa7 wQh6 wBe4 wSd7 wPe5 '
            'bKg8 bRg7 bPe7 bPe6", false, false, "None") '
            "AND PCount(*) = 9",
        )

    def test_query_url_uses_gateway_page_parameter_after_first_page(self):
        first = query_url('Author("Loyd, Samuel%")', page=1)
        second = query_url('Author("Loyd, Samuel%")', page=2)

        self.assertNotIn("&p=", first)
        self.assertIn("&p=2", second)

    def test_result_count_accepts_numeric_string(self):
        self.assertEqual(result_count({"count": "948"}), 948)
        self.assertIsNone(result_count({"count": "not-a-number"}))

    @patch("utilities.yacpdb_probe.fetch_query_page")
    def test_fetch_query_all_pages_uses_count_and_collects_ids(self, fetch_page):
        fetch_page.side_effect = [
            ([{"id": 1}, {"id": 2}], {"count": 5}, 0),
            ([{"id": 3}, {"id": 4}], {"count": 5}, 0),
            ([{"id": 5}], {"count": 5}, 0),
        ]

        entries, metadata, pages, unusable = fetch_query(
            'Author("Loyd, Samuel%")', timeout=30, all_pages=True
        )

        self.assertEqual([entry["id"] for entry in entries], [1, 2, 3, 4, 5])
        self.assertEqual(metadata, {"count": 5})
        self.assertEqual(pages, 3)
        self.assertEqual(unusable, 0)
        self.assertEqual(
            [call.kwargs["page"] for call in fetch_page.call_args_list],
            [1, 2, 3],
        )

    @patch("utilities.yacpdb_probe.fetch_query_page")
    def test_fetch_query_counts_unusable_gateway_rows(self, fetch_page):
        fetch_page.side_effect = [
            ([{"id": 1}, {"id": 2}], {"count": 4}, 0),
            ([{"id": 3}], {"count": 4}, 1),
        ]

        entries, metadata, pages, unusable = fetch_query(
            'Author("Loyd, Samuel%")', timeout=30, all_pages=True
        )

        self.assertEqual([entry["id"] for entry in entries], [1, 2, 3])
        self.assertEqual(metadata, {"count": 4})
        self.assertEqual(pages, 2)
        self.assertEqual(unusable, 1)

    @patch("utilities.yacpdb_probe.fetch_query_page")
    def test_fetch_query_accepts_short_final_page_despite_stale_count(self, fetch_page):
        fetch_page.side_effect = [
            ([{"id": 1}, {"id": 2}], {"count": 4}, 0),
            ([{"id": 3}], {"count": 4}, 0),
            ([], {"count": 4}, 0),
        ]

        entries, metadata, pages, unusable = fetch_query(
            'Author("Loyd, Samuel%")', timeout=30, all_pages=True
        )

        self.assertEqual([entry["id"] for entry in entries], [1, 2, 3])
        self.assertEqual(metadata, {"count": 4})
        self.assertEqual(pages, 2)
        self.assertEqual(unusable, 0)
        self.assertEqual(
            [call.kwargs["page"] for call in fetch_page.call_args_list],
            [1, 2, 3],
        )

    @patch("utilities.yacpdb_probe.fetch_query_page")
    def test_fetch_query_detects_repeated_page(self, fetch_page):
        fetch_page.side_effect = [
            ([{"id": 1}, {"id": 2}], {"count": 3}, 0),
            ([{"id": 1}, {"id": 2}], {"count": 3}, 0),
        ]

        with self.assertRaisesRegex(RuntimeError, "repeated already-seen IDs"):
            fetch_query('Author("Loyd, Samuel%")', timeout=30, all_pages=True)

    @patch("utilities.yacpdb_probe.fetch_query_page")
    def test_fetch_query_rejects_premature_empty_page(self, fetch_page):
        fetch_page.side_effect = [
            ([{"id": 1}, {"id": 2}], {"count": 3}, 0),
            ([], {"count": 3}, 0),
        ]

        with self.assertRaisesRegex(RuntimeError, "empty before all 3"):
            fetch_query('Author("Loyd, Samuel%")', timeout=30, all_pages=True)

    @patch("utilities.yacpdb_probe.print")
    def test_debug_page_reports_page_accounting_and_ids(self, mock_print):
        debug_page(
            query='Author("Loyd, Samuel%")',
            page=10,
            entries=[{"id": 901}, {"id": 947}],
            metadata={"count": 948},
            unusable=0,
            cumulative_usable=947,
            cumulative_unusable=0,
        )

        output = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("page=10", output)
        self.assertIn("raw=2", output)
        self.assertIn("cumulative_usable=947", output)
        self.assertIn("accounted=947", output)
        self.assertIn("count=948", output)
        self.assertIn("first=901 last=947", output)
        self.assertIn("&p=10", output)

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

    def test_none_placeholder_is_not_a_candidate_solution(self):
        entry = {
            "id": 3,
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1"], "black": ["Kh8"]},
            "solution": "None",
        }

        self.assertEqual(classify(entry), ("missing-solution",))

    def test_twins_and_duplex_are_reported_and_excluded_from_core_candidates(self):
        base = {
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1"], "black": ["Kh8"]},
            "solution": "1.Ka1-b1",
        }
        twins = {**base, "twins": {"b": "rotate 180"}}
        duplex = {**base, "options": ["Duplex"]}

        self.assertEqual(classify(twins), ("has-twins",))
        self.assertEqual(classify(duplex), ("has-options", "has-duplex"))

    def test_entry_fen_infers_castling_rights_from_home_king_and_rooks(self):
        entry = {
            "algebraic": {
                "white": ["Ke1", "Ra1", "Rh1"],
                "black": ["Ke8", "Ra8", "Rh8"],
            }
        }

        self.assertEqual(entry_fen(entry), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

    def test_cooked_unsound_and_retro_records_are_not_core_candidates(self):
        base = {
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1"], "black": ["Kh8"]},
            "solution": "1.Ka1-b1",
        }

        self.assertEqual(classify({**base, "keywords": ["Cooked"]}), ("cooked",))
        self.assertEqual(classify({**base, "keywords": ["Unsound"]}), ("unsound",))
        self.assertEqual(classify({**base, "keywords": ["Retro"]}), ("retro",))

    def test_fairy_piece_is_not_candidate(self):
        entry = {
            "id": 2,
            "stipulation": "#2",
            "algebraic": {"white": ["Ka1", "Na2"], "black": ["Kh8"]},
            "solution": "1.Na2-b4",
        }

        self.assertEqual(classify(entry), ("non-orthodox-piece",))

    def test_entry_fen_builds_issue_1862_position(self):
        entry = {
            "algebraic": {
                "white": ["Ka7", "Qh6", "Be4", "Sd7", "Pe5"],
                "black": ["Kg8", "Rg7", "Pe7", "Pe6"],
            }
        }

        self.assertEqual(
            entry_fen(entry),
            "6k1/K2Np1r1/4p2Q/4P3/4B3/8/8/8 w - - 0 1",
        )

    def test_solution_failure_category_separates_syntax_and_legality(self):
        self.assertEqual(
            solution_failure_category("line 1: unsupported solution syntax: 'x'"),
            "unsupported-syntax",
        )
        self.assertEqual(
            solution_failure_category("authored move 'x' is illegal at ply 2"),
            "illegal-move",
        )

    def test_audit_solutions_counts_compiled_and_failed_candidates(self):
        base = {
            "stipulation": "#3",
            "algebraic": {
                "white": ["Ka7", "Qh6", "Be4", "Sd7", "Pe5"],
                "black": ["Kg8", "Rg7", "Pe7", "Pe6"],
            },
        }
        good = {
            **base,
            "id": 47462,
            "solution": "1.Qh6-h1 !",
        }
        unsupported = {
            **base,
            "id": 47463,
            "solution": "1.Qh1/Qh2",
        }

        counts, failures = audit_solutions([good, unsupported])

        self.assertEqual(counts["candidates"], 2)
        self.assertEqual(counts["compiled"], 1)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["unsupported-syntax"], 1)
        self.assertEqual(failures[0][:2], (47463, "unsupported-syntax"))

    def test_entry_id_accepts_numeric_string(self):
        self.assertEqual(entry_id({"id": "123"}), 123)
        self.assertIsNone(entry_id({"id": "not-an-id"}))


if __name__ == "__main__":
    unittest.main()
