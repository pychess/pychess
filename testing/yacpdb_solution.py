import unittest

from pychess.Savers.yacpdb_solution import SolutionParseError, parse_solution


ISSUE_1862_FEN = "6k1/K2Np1r1/4p2Q/4P3/4B3/8/8/8 w - - 0 1"
ISSUE_1862_SOLUTION = """\
1.Qh6-h1 ! {- zugzwang}
    1...Rg7-g6
        2.Be4*g6 threat:
                3.Qh1-h7 #
    1...Rg7-f7
        2.Be4-g6 {- zugzwang}
            2...Rf7-f1 {(Rf~, Rh7)}
                3.Qh1-h7 #
            2...Rf7-g7
                3.Qh1-a8 #
            2...Kg8-g7
                3.Qh1-h7 #
    1...Kg8-f7
        2.Qh1-h5 +
            2...Kf7-g8
                3.Qh5-e8 #
            2...Rg7-g6
                3.Qh5*g6 #
"""


class YacpdbSolutionTest(unittest.TestCase):
    def test_issue_1862_compiles_to_authored_key_and_defences(self):
        tree = parse_solution(ISSUE_1862_SOLUTION, ISSUE_1862_FEN)

        self.assertEqual([node.uci for node in tree.real_children()], ["h6h1"])
        key = tree.real_children()[0]
        self.assertEqual(
            {node.uci for node in key.real_children()},
            {"g7g6", "g7f7", "g8f7"},
        )

    def test_issue_1862_threat_uses_null_ply(self):
        tree = parse_solution(ISSUE_1862_SOLUTION, ISSUE_1862_FEN)
        key = tree.real_children()[0]
        rg6 = next(node for node in key.real_children() if node.uci == "g7g6")
        bg6 = rg6.real_children()[0]

        self.assertEqual(bg6.uci, "e4g6")
        self.assertEqual(len(bg6.children), 1)
        self.assertEqual(bg6.children[0].kind, "threat")
        self.assertEqual(
            [node.uci for node in bg6.children[0].real_children()], ["h1h7"]
        )

    def test_issue_1862_all_authored_branches_are_normalized(self):
        tree = parse_solution(ISSUE_1862_SOLUTION, ISSUE_1862_FEN)
        key = tree.real_children()[0]
        rf7 = next(node for node in key.real_children() if node.uci == "g7f7")
        bg6 = rf7.real_children()[0]

        self.assertEqual(bg6.uci, "e4g6")
        replies = {node.uci: node for node in bg6.real_children()}
        self.assertEqual(set(replies), {"f7f1", "f7g7", "g8g7"})
        self.assertEqual(
            [node.uci for node in replies["f7f1"].real_children()], ["h1h7"]
        )
        self.assertEqual(
            [node.uci for node in replies["f7g7"].real_children()], ["h1a8"]
        )

    def test_try_is_excluded_from_default_playable_children(self):
        fen = "7k/8/8/8/8/8/8/K6Q w - - 0 1"
        solution = """\
1.Qh1-h2 ?
    but 1...Kh8-g8 !
1.Qh1-a8 !
"""
        tree = parse_solution(solution, fen)

        self.assertEqual([node.uci for node in tree.real_children()], ["h1a8"])
        self.assertEqual(
            {node.uci for node in tree.real_children(include_tries=True)},
            {"h1h2", "h1a8"},
        )

    def test_set_play_is_retained_but_not_playable_as_a_key(self):
        fen = "7k/8/8/8/8/8/8/K6Q w - - 0 1"
        solution = """\
1...Kh8-g8
    2.Qh1-a8 #
1.Qh1-h7 !
"""
        tree = parse_solution(solution, fen)

        self.assertEqual(tree.children[0].kind, "set")
        self.assertEqual(tree.children[0].real_children()[0].uci, "h8g8")
        self.assertEqual([node.uci for node in tree.real_children()], ["h1h7"])

    def test_illegal_authored_move_fails_instead_of_entering_tree(self):
        with self.assertRaisesRegex(SolutionParseError, "illegal"):
            parse_solution("1.Qh6-a6 !", ISSUE_1862_FEN)


class YacpdbSolutionNotationTest(unittest.TestCase):
    def test_compact_unnumbered_reply_on_same_line_is_retained(self):
        fen = "8/8/3R4/4p2Q/5k2/6N1/5K2/8 w - - 0 1"
        tree = parse_solution(
            "1.Rd6-d4+! e5*d4 2.Qh5-c5 #",
            fen,
        )

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "d6d4")
        self.assertEqual([node.uci for node in key.real_children()], ["e5d4"])
        self.assertEqual(
            [node.uci for node in key.real_children()[0].real_children()],
            ["h5c5"],
        )

    def test_short_san_and_knight_promotion_are_normalized(self):
        fen = "8/3P4/4k3/8/8/8/8/K7 w - - 0 1"
        tree = parse_solution("1.d8N+! Ke6-e5 2.Sd8-f7 #", fen)

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "d7d8n")
        self.assertEqual([node.uci for node in key.real_children()], ["e6e5"])
        self.assertEqual(
            [node.uci for node in key.real_children()[0].real_children()],
            ["d8f7"],
        )

    def test_german_piece_alias_is_checked_against_board(self):
        fen = "7k/8/8/8/8/8/1B6/K7 w - - 0 1"
        tree = parse_solution("1.Lb2-f6 !", fen)

        self.assertEqual([node.uci for node in tree.real_children()], ["b2f6"])

    def test_separate_threat_prefix_marks_previous_move(self):
        fen = "7k/8/8/8/8/8/1Q6/K7 w - - 0 1"
        tree = parse_solution("1.Qb2-b1 !\nthreat: 2.Qb1-h7 #", fen)

        key = tree.real_children()[0]
        self.assertTrue(key.declares_threat)
        self.assertEqual(key.children[0].kind, "threat")
        self.assertEqual(
            [node.uci for node in key.children[0].real_children()], ["b1h7"]
        )

    def test_slash_defences_are_siblings_with_shared_continuation(self):
        fen = "8/1p2PQp1/3k4/p6p/K1Pp1p2/1P5P/P2q4/8 w - - 0 1"
        tree = parse_solution(
            "1.e8N+!\n1...Kc6/Kc5 2.Qc7#",
            fen,
        )

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "e7e8n")
        defences = {node.uci: node for node in key.real_children()}
        self.assertEqual(set(defences), {"d6c6", "d6c5"})
        for defence in defences.values():
            self.assertEqual([node.uci for node in defence.real_children()], ["f7c7"])

    def test_slash_continuations_are_siblings_under_each_shared_parent(self):
        fen = "4Q3/4PPr1/6k1/6P1/5pPp/8/q5n1/5b1K w - - 0 1"
        tree = parse_solution(
            "1...Rg8 2.Qxg8#/fxg8Q#",
            fen,
        )

        set_play = tree.children[0]
        defence = set_play.real_children()[0]
        self.assertEqual(defence.uci, "g7g8")
        self.assertEqual(
            {node.uci for node in defence.real_children()},
            {"e8g8", "f7g8q"},
        )

    def test_incomplete_slash_alternative_is_rejected(self):
        fen = "6k1/K2Np1r1/4p2Q/4P3/4B3/8/8/8 w - - 0 1"
        with self.assertRaisesRegex(SolutionParseError, "unsupported solution syntax"):
            parse_solution("1.Qh6-h1/", fen)

    def test_comma_defences_are_siblings_with_shared_continuation(self):
        fen = "3b4/8/4RR2/8/8/8/5P1P/5K1k w - - 0 1"
        tree = parse_solution(
            "1.Rb6! Bc7,Be7\n2.Rd6",
            fen,
        )

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "e6b6")
        defences = {node.uci: node for node in key.real_children()}
        self.assertEqual(set(defences), {"d8c7", "d8e7"})
        for defence in defences.values():
            self.assertEqual([node.uci for node in defence.real_children()], ["b6d6"])

    def test_incomplete_comma_alternative_is_rejected(self):
        fen = "3b4/8/4RR2/8/8/8/5P1P/5K1k w - - 0 1"
        with self.assertRaisesRegex(SolutionParseError, "unsupported solution syntax"):
            parse_solution("1.Rb6! Bc7,", fen)

    def test_single_letter_thematic_labels_do_not_change_tree(self):
        fen = "3b4/8/4RR2/8/8/8/5P1P/5K1k w - - 0 1"
        tree = parse_solution(
            "1.Rb6[A]! Bc7[a],Be7[b]\n2.Rd6#[B]",
            fen,
        )

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "e6b6")
        defences = {node.uci: node for node in key.real_children()}
        self.assertEqual(set(defences), {"d8c7", "d8e7"})
        for defence in defences.values():
            self.assertEqual([node.uci for node in defence.real_children()], ["b6d6"])

    def test_non_thematic_bracket_annotation_is_still_rejected(self):
        fen = "3b4/8/4RR2/8/8/8/5P1P/5K1k w - - 0 1"
        with self.assertRaisesRegex(SolutionParseError, "unsupported solution syntax"):
            parse_solution("1.Rb6[+wPa3]!", fen)

    def test_parenthesized_threat_uses_null_ply(self):
        fen = "K7/8/8/4Q3/8/4R3/4rN2/1N2k3 w - - 0 1"
        tree = parse_solution(
            "1.Nd2! (2.Rxe2#)\n"
            "   1...Kxf2 2.Qg3#\n"
            "   1...Kxd2 2.Qc3#\n"
            "   1...Rxe3 2.Qxe3#",
            fen,
        )

        key = tree.real_children()[0]
        self.assertEqual(key.uci, "b1d2")
        self.assertTrue(key.declares_threat)
        threat = next(child for child in key.children if child.kind == "threat")
        self.assertEqual([node.uci for node in threat.real_children()], ["e3e2"])
        self.assertEqual(
            {node.uci for node in key.children if not node.is_null},
            {"e1f2", "e1d2", "e2e3"},
        )

    def test_parenthesized_threat_retains_slash_alternatives(self):
        fen = "8/4p3/B1Rq1p2/2pk1B2/N1R5/N7/KQ3B2/8 w - - 0 1"
        tree = parse_solution("1.Bb7[A]?? (2.Nb6#[A]/R6xc5#[B])", fen)

        key = tree.real_children(include_tries=True)[0]
        self.assertEqual(key.uci, "a6b7")
        self.assertTrue(key.declares_threat)
        threat = key.children[0]
        self.assertEqual(threat.kind, "threat")
        self.assertEqual(
            {node.uci for node in threat.real_children(include_tries=True)},
            {"a4b6", "c6c5"},
        )

    def test_unclosed_parenthesized_continuation_is_rejected(self):
        fen = "K7/8/8/4Q3/8/4R3/4rN2/1N2k3 w - - 0 1"
        with self.assertRaisesRegex(SolutionParseError, "unsupported solution syntax"):
            parse_solution("1.Nd2! (2.Rxe2#", fen)


if __name__ == "__main__":
    unittest.main()
