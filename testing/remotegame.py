import unittest
import random

from pychess.Savers.remotegame import (
    get_internet_game_providers,
    InternetGameLichess,
    InternetGameChessgames,
    InternetGameFicsgames,
    InternetGameChesstempo,
    InternetGameChess24,
    InternetGame365chess,
    InternetGameChesspastebin,
    InternetGameChessbomb,
    InternetGameThechessworld,
    InternetGameChessOrg,
    InternetGameEuropeechecs,
    InternetGameGameknot,
    InternetGameChessCom,
    InternetGameSchachspielen,
    InternetGameRedhotpawn,
    InternetGameChesssamara,
    InternetGame2700chess,
    InternetGameIccf,
    InternetGameSchacharena,
    InternetGameChesspuzzle,
    InternetGameChessking,
    InternetGameIdeachess,
    InternetGameChessdb,
    InternetGameChesspro,
    InternetGameFicgs,
    InternetGameChessbase,
    InternetGamePlayok,
    InternetGamePychess,
    InternetGameGeneric,
)

cplist = get_internet_game_providers()


class RemoteGameTestCase(unittest.TestCase):
    def executeTest(self, cp, links):
        # Check
        if cp is None or links is None or len(links) == 0:
            return
        print("\n%s" % cp.get_description())
        if cp.get_description() not in cplist:
            print("- Skipping unlisted chess provider")
            return
        if not cp.is_enabled():
            print("- Skipping disabled chess provider")
            return
        if cp.is_async():
            print("- Skipping asynchronous chess provider")
            return

        # Pick one link only to not overload the remote server
        url, expected = random.choice(links)
        print("- Target link: %s" % url)
        print("- Expecting data: %s" % expected)

        # Download link
        cp.reset()
        if not cp.assign_game(url):
            data = None
        else:
            try:
                data = cp.download_game()
                data = cp.sanitize(data)
            except Exception:
                data = None

        # Result
        ok = data is not None
        print("- Fetched data: %s" % ok)
        if ok:
            print(data)
        self.assertEqual(ok, expected)

    def testLichess(self):
        links = [
            (
                "http://lichess.org/CA4bR2b8/black/analysis#12",
                True,
            ),  # Game in advanced position
            ("https://lichess.org/CA4bR2b8", True),  # Canonical address
            ("CA4bR2b8", False),  # Short ID (possible via the generic function only)
            ("https://lichess.org/game/export/CA4bR2b8", True),  # Download link
            (
                "https://LICHESS.org/embed/CA4bR2b8/black?theme=brown",
                True,
            ),  # Embedded game
            ("http://fr.lichess.org/@/thibault", False),  # Not a game (user page)
            ("http://lichess.org/blog", False),  # Not a game (page)
            ("http://lichess.dev/ABCD1234", False),  # Not a game (wrong ID)
            ("https://lichess.org/9y4KpPyG", True),  # Variant game Chess960
            ("https://LICHESS.org/nGhOUXdP?p=0", True),  # Variant game with parameter
            (
                "https://lichess.org/nGhOUXdP?p=0#3",
                True,
            ),  # Variant game with parameter and anchor
            (
                "https://hu.lichess.org/study/hr4H7sOB?page=1",
                True,
            ),  # Study of one game with unused parameter
            ("https://lichess.org/study/76AirB4Y/C1NcczQl", True),  # Chapter of a study
            (
                "https://lichess.org/study/hr4H7sOB/fvtzEXvi.pgn#32",
                True,
            ),  # Chapter of a study with anchor
            ("https://lichess.org/STUDY/hr4H7sOB.pgn", True),  # Study of one game
            (
                "https://lichess.org/training/daily",
                False,
            ),  # Daily puzzle (TODO: needs fix)
            ("https://lichess.org/training/CP8zM", False),  # Puzzle (TODO: needs fix)
            (
                "https://lichess.org/training/1281301832",
                False,
            ),  # Not a puzzle (wrong ID)
            (
                "https://lichess.org/broadcast/2019-gct-zagreb-round-4/jQ1dbbX9",
                True,
            ),  # Broadcast
            (
                "https://lichess.org/broadcast/2019-pychess-round-1/pychess1",
                False,
            ),  # Not a broadcast (wrong ID)
            (
                "https://lichess.ORG/practice/basic-tactics/the-pin/9ogFv8Ac/BRmScz9t#t",
                True,
            ),  # Practice
            ("https://lichess.org/practice/py/chess/12345678/abcdEFGH", False),
        ]  # Not a practice (wrong ID)
        self.executeTest(InternetGameLichess(), links)

    def testChessgames(self):
        links = [
            (
                "http://www.chessgames.com/perl/chessgame?gid=1075462&comp=1",
                True,
            ),  # With computer analysis
            (
                "http://www.chessgames.com/perl/chessgame?gid=1075463",
                True,
            ),  # Without computer analysis
            (
                "http://www.CHESSGAMES.com/perl/chessgame?gid=1075463&comp=1#test",
                True,
            ),  # Without computer analysis but requested in URL
            ("http://www.chessgames.com/perl/chessgame?gid=1234567890", False),
        ]  # Not a game
        self.executeTest(InternetGameChessgames(), links)

    def testFicsgames(self):
        links = [
            (
                "https://www.ficsgames.org/cgi-bin/show.cgi?ID=451813954;action=save",
                True,
            ),  # Normal game
            (
                "https://www.ficsgames.org/cgi-bin/show.cgi?ID=qwertz;action=save",
                False,
            ),  # Invalid identifier (not numeric)
            (
                "https://www.ficsgames.org/cgi-bin/show.cgi?ID=0#anchor",
                False,
            ),  # Invalid identifier (null)
            ("https://www.ficsgames.org/about.html", False),
        ]  # Not a game
        self.executeTest(InternetGameFicsgames(), links)

    def testChesstempo(self):
        links = [
            ("https://chesstempo.com/gamedb/game/2046457", True),  # Game
            (
                "https://CHESSTEMPO.com/gamedb/game/2046457/foo/bar/123",
                True,
            ),  # Game with additional path
            (
                "https://www.chesstempo.com/gamedb/game/2046457?p=0#tag",
                True,
            ),  # Game with additional parameters
            ("https://en.chesstempo.com/chess-tactics/71360", True),  # Puzzle
            ("http://chesstempo.com/faq.html", False),
        ]  # Not a game
        self.executeTest(InternetGameChesstempo(), links)

    def testChess24(self):
        links = [
            ("https://chess24.com/en/game/DQhOOrJaQKS31LOiOmrqPg#anchor", True)
        ]  # Game with anchor
        self.executeTest(InternetGameChess24(), links)

    def test365chess(self):
        links = [
            (
                "https://www.365chess.com/view_game.php?g=4187437#anchor",
                True,
            ),  # Game 1/2-1/2 for special chars
            (
                "https://www.365chess.com/view_game.php?g=1234567890",
                False,
            ),  # Not a game
            ("https://www.365chess.com/game.php?gid=4230834&p=0", True),
        ]  # Game with additional parameter
        self.executeTest(InternetGame365chess(), links)

    def testChesspastebin(self):
        links = [
            (
                "https://www.chesspastebin.com/2018/12/29/anonymous-anonymous-by-george-2/",
                True,
            ),  # Game quite complete
            (
                "https://www.CHESSPASTEBIN.com/2019/04/14/unknown-unknown-by-alekhine-sapladi/",
                True,
            ),  # Game with no header
            (
                "https://www.chesspastebin.com/1515/09/13/marignan/",
                False,
            ),  # Not a game (invalid URL)
            ("https://www.chesspastebin.com", True),
        ]  # Game from homepage
        self.executeTest(InternetGameChesspastebin(), links)

    def testChessbomb(self):
        links = [
            (
                "https://www.chessbomb.com/arena/2019-katowice-chess-festival-im/04-Kubicka_Anna-Sliwicka_Alicja",
                True,
            ),  # Game
            ("https://www.chessbomb.com/arena/2019-bangkok-chess-open", False),
        ]  # Not a game (arena)
        self.executeTest(InternetGameChessbomb(), links)

    def testThechessworld(self):
        links = [
            (
                "https://thechessworld.com/articles/middle-game/typical-sacrifices-in-the-middlegame-sacrifice-on-e6/",
                True,
            ),  # 3 embedded games
            (
                "https://THECHESSWORLD.com/pgngames/middlegames/sacrifice-on-e6/Ivanchuk-Karjakin.pgn",
                True,
            ),  # Direct link
            ("https://thechessworld.com/help/about/", False),
        ]  # Not a game (about page)
        self.executeTest(InternetGameThechessworld(), links)

    def testChessOrg(self):
        links = [
            (
                "https://chess.org/play/19a8ffe8-b543-4a41-be02-e84e0f4d6f3a",
                True,
            ),  # Classic game
            (
                "https://CHESS.org/play/c28f1b76-aee0-4577-b8a5-eeda6a0e14af",
                True,
            ),  # Chess960
            (
                "https://chess.org/play/c28fffe8-ae43-4541-b802-eeda6a4d6f3a",
                False,
            ),  # Not a game (unknown ID)
            ("https://chess.org", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChessOrg(), links)

    def testEuropeechecs(self):
        links = [
            (
                "https://www.europe-echecs.com/art/championnat-d-europe-f-minin-2019-7822.html",
                True,
            ),  # Embedded games
            (
                "https://www.EUROPE-ECHECS.com/embed/doc_a2d179a4a201406d4ce6138b0b1c86d7.pgn",
                True,
            ),  # Direct link
            ("https://www.europe-echecs.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameEuropeechecs(), links)

    def testGameknot(self):
        links = [
            ("https://gameknot.com/analyze-board.pl?bd=22792465#tag", True),  # Game
            (
                "https://GAMEKNOT.com/chess.pl?bd=22792465&p=1",
                False,
            ),  # Not a game (wrong path)
            (
                "https://gameknot.com/analyze-board.pl?bd=1234567890&p=1",
                False,
            ),  # Not a game (unknown ID)
            (
                "https://gameknot.com/analyze-board.pl?bd=bepofr#tag",
                False,
            ),  # Not a game (not numeric ID)
            ("https://gameknot.com", False),  # Not a game (homepage)
            ("https://gameknot.com/chess-puzzle.pl?pz=224260", True),  # Puzzle
            (
                "https://gameknot.com/chess-puzzle.pl?pz=224541&next=2",
                True,
            ),  # Puzzle with parameters
            (
                "https://gameknot.com/chess-puzzle.pl?pz=224571",
                True,
            ),  # Puzzle with analysis
            (
                "https://gameknot.com/chess-puzzle.pl?pz=ABC",
                False,
            ),  # Random puzzle but rejected by PyChess (wrong format)
            ("https://gameknot.com/chess-puzzle.pl?pz=0#tag", False),
        ]  # Random puzzle but rejected by PyChess (wrong format)
        self.executeTest(InternetGameGameknot(), links)

    def testChessCom(self):
        links = [
            ("https://www.CHESS.com/live/game/3638784952#anchor", True),  # Live game
            ("3638784952", False),  # Short ID (possible via the generic function only)
            ("https://chess.com/live#g=3638784952", True),  # Another syntax
            (
                "https://chess.com/de/live/game/3635508736?username=rikikits",
                True,
            ),  # Live game Chess960
            (
                "https://www.chess.com/live/game/1936591455",
                True,
            ),  # Live game CrazyHouse
            (
                "https://www.chess.com/analysis/game/live/3874372792",
                True,
            ),  # Live analysis
            (
                "https://www.chess.com/analysis/game/live/4119932192",
                True,
            ),  # Live game with promotion to Queen
            ("https://www.chess.com/daily/game/223897998", True),  # Daily game
            ("https://www.chess.com/DAILY/game/224478042", True),  # Daily game
            (
                "https://www.chess.com/daily/game/225006782",
                False,
            ),  # Daily game Chess960 (TODO: needs fix)
            (
                "https://www.chess.com/daily/GAME/205389002",
                False,
            ),  # Daily game Chess960 (TODO: needs fix)
            (
                "https://chess.com/live/game/13029832074287114",
                False,
            ),  # Not a game (wrong ID)
            ("https://www.chess.com", False),  # Not a game (homepage)
            ("https://www.chess.com/puzzles/problem/41839", True),  # Puzzle
            (
                "https://www.chess.com/analysis?fen=invalidfen",
                False,
            ),  # Position to analyze (no FEN)
            (
                "https://www.chess.com/analysis?fen=r1b1k3%2F2p2pr1%2F1pp4p%2F8%2F2p5%2F2N5%2FPPP2PPP%2F3RR1K1+b+-+-+3+17&flip=false",
                True,
            ),
        ]
        self.executeTest(InternetGameChessCom(), links)

    def testSchachspielen(self):
        links = [
            (
                "https://www.schach-spielen.eu/analyse/2jcpl1vs/black#test",
                True,
            ),  # Best game ever with anchor
            (
                "http://schach-SPIELEN.eu/game/2jcpl1vs?p=1",
                True,
            ),  # Best game ever with parameter
            ("https://www.schach-spielen.eu/game/8kcevvdy/white", True),  # Chess960
            (
                "https://www.schach-spielen.eu/game/IENSUIEN",
                False,
            ),  # Not a game (wrong ID)
            (
                "https://www.schach-spielen.eu/about/8kcevvdy",
                False,
            ),  # Not a game (bad URL)
            ("https://www.schach-SPIELEN.eu", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameSchachspielen(), links)

    def testRedhotpawn(self):
        links = [
            (
                "https://www.redhotpawn.com/chess/chess-game-history.php?gameid=13264954",
                True,
            ),  # Game in progress (at the time of the initial test)
            (
                "https://www.redhotpawn.com/chess/chess-game-HISTORY.php?gameid=13261506&arg=0#anchor",
                True,
            ),  # Game draw
            (
                "https://www.redhotpawn.com/chess/chess-game-history.php?gameid=13238354",
                True,
            ),  # Game stalemate
            (
                "https://REDHOTPAWN.com/chess/chess-GAME-analysis.php?gameid=13261541&arg=0#anchor",
                True,
            ),  # Game mate
            (
                "https://www.redhotpawn.com/chess/chess-game-history.php?gameid=1234567890",
                False,
            ),  # Not a game (wrong ID)
            (
                "https://www.redhotpawn.com/chess/view-game.php?gameid=13238354",
                False,
            ),  # Not a game (wrong path in URL)
            (
                "https://www.redhotpawn.com/chess/chess-game-analysis.php?id=13238354",
                False,
            ),  # Not a game (wrong parameter in URL)
            ("https://www.redhotpawn.com", False),  # Not a game (homepage)
            (
                "https://www.redhotpawn.com/chess-puzzles/chess-puzzle-solve.php?puzzleid=7470",
                True,
            ),  # Puzzle
            (
                "https://www.redhotpawn.com/chess-puzzles/chess-puzzle-serve.php",
                True,
            ),  # Puzzle through a random link
            (
                "https://www.redhotpawn.com/chess-puzzles/chess-puzzle-solve.php?puzzleid=1234567890",
                False,
            ),
        ]  # Not a puzzle (wrong ID)
        self.executeTest(InternetGameRedhotpawn(), links)

    def testChesssamara(self):
        links = [
            (
                "https://chess-SAMARA.ru/68373335-igra-Firudin1888-vs-Pizyk",
                True,
            ),  # Game
            (
                "https://chess-samara.ru/view/pgn.html?gameid=68373335",
                False,
            ),  # Game in direct link but handled by the generic extractor
            (
                "https://chess-samara.ru/1234567890123-pychess-vs-pychess",
                False,
            ),  # Not a game (wrong ID)
            ("https://chess-samara.ru", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChesssamara(), links)

    @unittest.skip("You need to be a Premium Member to have access to this feature.")
    def test2700chess(self):
        links = [
            (
                "https://2700CHESS.com/games/dominguez-perez-yu-yangyi-r19.6-hengshui-chn-2019-05-18",
                True,
            ),  # Game
            (
                "https://2700chess.com/games/download?slug=dominguez-perez-yu-yangyi-r19.6-hengshui-chn-2019-05-18#tag",
                True,
            ),  # Game with direct link
            (
                "https://2700chess.COM/games/pychess-r1.1-paris-fra-2019-12-25",
                False,
            ),  # Not a game (wrong ID)
            ("https://2700chess.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGame2700chess(), links)

    def testIccf(self):
        links = [
            ("https://www.iccf.COM/game?id=154976&param=foobar", True),  # Game
            (
                "https://www.iccf.com/GetPGN.aspx?id=154976",
                False,
            ),  # Game in direct link but handled by the generic extractor
            ("https://www.iccf.com/game?id=abc123", False),  # Not a game (wrong ID)
            (
                "https://www.iccf.com/officials?id=154976",
                False,
            ),  # Not a game (invalid path)
            ("https://www.iccf.com", False),  # Not a game (homepage)
            ("https://ICCF.com/event?id=13581#tag", True),  # Event
            (
                "https://www.iccf.com/GetEventPGN.aspx?id=13581",
                False,
            ),  # Event in direct link but handled by the generic extractor
            ("https://www.iccf.com/event?id=abc123", False),
        ]  # Not an event (wrong ID)
        self.executeTest(InternetGameIccf(), links)

    def testSchacharena(self):
        self.executeTest(
            InternetGameSchacharena(), []
        )  # No canonical name for the games

    def testChesspuzzle(self):
        links = [
            (
                "https://chesspuzzle.net/Puzzle/23476",
                False,
            ),  # Puzzle from the quiz (TODO: needs fix)
            (
                "https://CHESSPUZZLE.net/Solution/32881",
                False,
            ),  # Puzzle from the solution (TODO: needs fix)
            ("https://chesspuzzle.net/Puzzle", False),  # Not a puzzle (random link)
            (
                "https://chesspuzzle.net/Puzzle/123456789",
                False,
            ),  # Not a puzzle (wrong ID)
            ("https://chesspuzzle.net", False),
        ]  # Not a puzzle (homepage)
        self.executeTest(InternetGameChesspuzzle(), links)

    def testChessking(self):
        # The direct PGN links are returned as 'application/octet-stream'
        links = [
            ("https://play.chessking.COM/games/4318271", True),  # Game of type G
            ("https://CHESSKING.com/games/ff/9859108", True),  # Game of type F
            (
                "https://play.chessking.com/games/1234567890",
                False,
            ),  # Not a game (ID too long)
            ("https://play.chessking.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChessking(), links)

    def testIdeachess(self):
        links = [
            (
                "http://www.ideachess.com/chess_tactics_puzzles/checkmate_n/37431",
                True,
            ),  # Mate EN
            ("http://fr.ideachess.com/echecs_tactiques/mat_n/37431", True),  # Mate FR
            (
                "http://it.ideachess.com/scacchi_tattica/scacco_matto_n/37431",
                True,
            ),  # Mate IT
            (
                "http://de.ideachess.com/chess_tactics_puzzles/checkmate_n/37431",
                True,
            ),  # Mate DE
            (
                "http://es.ideachess.com/chess_tactics_puzzles/checkmate_n/37431",
                True,
            ),  # Mate ES
            (
                "http://nl.ideachess.com/chess_tactics_puzzles/checkmate_n/37431",
                True,
            ),  # Mate NL
            (
                "http://ru.ideachess.com/chess_tactics_puzzles/checkmate_n/37431",
                True,
            ),  # Mate RU
            (
                "http://www.ideachess.com/chess_tactics_puzzles/tactics_n/32603",
                True,
            ),  # Tactics EN
            (
                "http://fr.ideachess.com/echecs_tactiques/tactiques_n/32603",
                True,
            ),  # Tactics FR
            (
                "http://it.ideachess.com/scacchi_tattica/tattica_n/32603",
                True,
            ),  # Tactics IT
            (
                "http://de.ideachess.com/chess_tactics_puzzles/tactics_n/32603",
                True,
            ),  # Tactics DE
            (
                "http://es.ideachess.com/chess_tactics_puzzles/tactics_n/32603",
                True,
            ),  # Tactics ES
            (
                "http://nl.ideachess.com/chess_tactics_puzzles/tactics_n/32603",
                True,
            ),  # Tactics NL
            (
                "http://ru.ideachess.com/chess_tactics_puzzles/tactics_n/32603",
                True,
            ),  # Tactics RU
            (
                "http://www.ideachess.com/chess_tactics_puzzles/checkmate_n/123457890",
                False,
            ),  # Not a mate (wrong ID)
            (
                "http://www.ideachess.com/chess_tactics_puzzles/tactics_n/123457890",
                False,
            ),  # Not a tactics (wrong ID)
            ("http://www.ideachess.com", False),
        ]  # Not a puzzle (homepage)
        self.executeTest(InternetGameIdeachess(), links)

    def testChessdb(self):
        links = [
            (
                "https://CHESS-DB.COM/public/game.jsp?id=623539.1039784.81308416.30442",
                True,
            ),  # Game
            (
                "https://chess-db.com/public/game.jsp?id=623539.2900084.7718912.30537",
                False,
            ),  # Game but website bug with escaping '
            (
                "https://chess-db.com/public/game.jsp?id=123456.1234567.1234567.123456789",
                False,
            ),  # Not a game (unknown game)
            (
                "https://chess-db.com/public/game.jsp?id=ABC123",
                False,
            ),  # Not a game (wrong ID)
            (
                "https://chess-db.com/play.jsp?id=623539.1039784.81308416.30442",
                False,
            ),  # Not a game (wrong path)
            ("https://chess-db.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChessdb(), links)

    def testChesspro(self):
        links = [
            (
                "https://chessPRO.ru/details/grand_prix_moscow19_day8",
                True,
            ),  # Article with game and no header
            (
                "https://chesspro.ru/details/grand_prix_moscow19_day11",
                False,
            ),  # Article without game
            ("https://chesspro.ru", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChesspro(), links)

    def testFicgs(self):
        links = [
            ("http://FICGS.com/game_95671.html", True),  # Game
            (
                "http://www.ficgs.com/game_1234567890.html",
                False,
            ),  # Not a game (wrong ID)
            ("http://www.ficgs.com/view_95671.html", False),  # Not a game (wrong path)
            ("http://www.ficgs.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameFicgs(), links)

    def testChessbase(self):
        links = [
            (
                "http://live.chessbase.com/watch/5th-EKA-IIFL-Investment-2019",
                False,
            ),  # Games (TODO: needs fix)
            (
                "http://live.chessbase.com/replay/5th-eka-iifl-investment-2019/3?anno=False",
                False,
            ),  # Games for round 3 (TODO: needs fix)
            (
                "https://liveserver.chessbase.com:6009/pgn/5th-eka-iifl-investment-2019/all.pgn#fake-tag",
                False,
            ),  # Not a game (direct PGN link)
            ("http://live.chessbase.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGameChessbase(), links)

    def testPlayok(self):
        links = [
            ("http://www.playok.com/p/?g=ch484680868", True),  # Game
            ("https://PLAYOK.com/p/?g=ch484680868.txt", True),  # Game (direct link)
            ("https://PLAYOK.com/p/?g=ch999999999#tag", False),  # Game (wrong ID)
            ("http://www.playok.com", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGamePlayok(), links)

    def testPychess(self):
        links = [
            ("http://pychess.org/DGN5Ps2k#tag", True),  # Crazyhouse
            ("http://pychess-variants.herokuapp.com/uWbgRNfw", True),  # Chess
            ("http://PYCHESS.org/4XTiOuKB", True),  # Chess960
            ("http://pychess.ORG/b8aZwvoJ", True),  # Placement
            ("https://pychess.org/drtDbEhd#tag", False),  # Shogi (unsupported)
            ("https://pychess.ORG/tALxtipo", True),  # Makruk
            ("https://pychess.org/2CKjayxv?param", True),  # Cambodian
            ("https://PYCHESS.ORG/4x0kQ8kY", True),  # Sittuyin
            ("https://pychess.org/7cqV5j2N", True),  # Seirawan
            ("http://pychess.org", False),
        ]  # Not a game (homepage)
        self.executeTest(InternetGamePychess(), links)

    def testGeneric(self):
        links = [
            (
                "https://thechessworld.com/pgngames/middlegames/sacrifice-on-e6/Ivanchuk-Karjakin.pgn",
                True,
            )
        ]  # Game with UTF-8 BOM
        self.executeTest(InternetGameGeneric(), links)


if __name__ == "__main__":
    unittest.main()
