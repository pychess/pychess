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


if __name__ == "__main__":
    unittest.main()
