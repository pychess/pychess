from gi.repository import GObject

from pychess.ic.FICSObjects import FICSGame
from pychess.ic.managers.HelperManager import HelperManager
from pychess.ic import parseRating, GAME_TYPES_BY_SHORT_FICS_NAME, IC_STATUS_PLAYING
from pychess.ic.icc import DG_PLAYER_ARRIVED_SIMPLE, DG_PLAYER_LEFT, DG_WHO_AM_I, DG_TOURNEY

ratings = "([\d\+\- ]{1,4})"


class ICCHelperManager(HelperManager):
    def __init__(self, helperconn, connection):
        GObject.GObject.__init__(self)

        self.helperconn = helperconn
        self.connection = connection

        # 1267      guest2504            1400 KQkr(C)              20u  5  12       W:  1
        # 1060      guest7400            1489 DeadGuyKai            bu  3   0       W: 21
        # 791 1506 PlotinusRedux             guest3090             bu  2  12       W: 21
        # 47 2357 *IM_Danchevski       2683 *GM_Morozevich       Ex: scratch      W: 35
        # 101      Replayer2                 Replayer2            Ex: scratch      W:  1
        # 117 2760 *GM_Topalov          2823 *GM_Caruana          Ex: StLouis16 %0 W: 29
        # 119 1919 stansai              2068 Agrimont             Ex: continuation W: 53
        # 456 games displayed (282 played, 174 examined).
        self.helperconn.expect_fromto(
            self.on_icc_game_list,
            "(\d+) %s (\w+)(?:(.+))?\s+%s (\w+)(?:(.+))?\s+(%s)(u|r)\s*(\d+)\s+(\d+)\s*(W|B):\s*(\d+)"
            %
            (ratings, ratings, "|".join(GAME_TYPES_BY_SHORT_FICS_NAME.keys())),
            "(\d+) games displayed \(.+\).")

        self.helperconn.expect_dg_line(DG_PLAYER_ARRIVED_SIMPLE, self.on_icc_player_arrived_simple)
        self.helperconn.expect_dg_line(DG_PLAYER_LEFT, self.on_icc_player_left)
        self.helperconn.expect_dg_line(DG_WHO_AM_I, self.on_icc_who_am_i)
        self.helperconn.expect_dg_line(DG_TOURNEY, self.on_icc_tourney)

        self.helperconn.client.run_command("set-2 %s 1" % DG_PLAYER_ARRIVED_SIMPLE)
        self.helperconn.client.run_command("set-2 %s 1" % DG_PLAYER_LEFT)
        self.helperconn.client.run_command("set-2 %s 1" % DG_WHO_AM_I)
        self.helperconn.client.run_command("set-2 %s 1" % DG_TOURNEY)

        # Unfortunately we can't maintain a list of games
        # From https://www.chessclub.com/user/resources/formats/formats.txt
        # Here is the list of verbose DGs:
        # DG_PLAYER_ARRIVED DG_PLAYER_LEFT
        # DG_GAME_STARTED DG_GAME_RESULT DG_EXAMINED_GAME_IS_GONE
        # DG_PEOPLE_IN_MY_CHANNEL DG_CHANNELS_SHARED DG_SEES_SHOUTS
        # Currently, only TDs like Tomato can use these.
        self.helperconn.client.run_command("games *19")

    def on_icc_game_list(self, matchlist):
        games = []
        for match in matchlist[:-1]:
            if isinstance(match, str):
                if match:
                    try:
                        parts = match.split()
                        index = 0

                        gameno = parts[index]
                        index += 1

                        if parts[index].isdigit():
                            wrating = parts[index]
                            index += 1
                        else:
                            wrating = "----"

                        wname = parts[index]
                        index += 1

                        if parts[index].isdigit():
                            brating = parts[index]
                            index += 1
                        else:
                            brating = "----"

                        bname = parts[index]
                        index += 1

                        if parts[index] == "Ex:":
                            shorttype = "e"
                            rated = ""
                            min = "0"
                            inc = "0"
                        else:
                            rated = parts[index][-1]
                            shorttype = parts[index][:-1]
                            index += 1
                            min = parts[index]
                            index += 1
                            inc = parts[index]
                        private = ""
                    except IndexError:
                        # malformed game line
                        continue
                else:
                    continue
            else:
                continue
                # TODO
                # gameno, wrating, wname, brating, bname, private, shorttype, rated, min, \
                # inc, whour, wmin, wsec, bhour, bmin, bsec, wmat, bmat, color, movno = match.groups()
            try:
                gametype = GAME_TYPES_BY_SHORT_FICS_NAME[shorttype]
            except KeyError:
                # TODO:
                print("key error in GAME_TYPES_BY_SHORT_FICS_NAME: %s" % shorttype)
                continue

            wplayer = self.connection.players.get(wname)
            bplayer = self.connection.players.get(bname)
            game = FICSGame(wplayer,
                            bplayer,
                            gameno=int(gameno),
                            rated=(rated == "r"),
                            private=(private == "p"),
                            minutes=int(min),
                            inc=int(inc),
                            game_type=gametype)

            for player, rating in ((wplayer, wrating), (bplayer, brating)):
                if player.status != IC_STATUS_PLAYING:
                    player.status = IC_STATUS_PLAYING
                if player.game != game:
                    player.game = game
                rating = parseRating(rating)
                if gametype.rating_type in player.ratings and \
                        player.ratings[gametype.rating_type] != rating:
                    player.ratings[gametype.rating_type] = rating
                    player.emit("ratings_changed", gametype.rating_type, player)
            game = self.connection.games.get(game, emit=False)
            games.append(game)

        self.connection.games.emit("FICSGameCreated", games)

    def on_icc_player_arrived_simple(self, data):
        name = data.split()[0]
        player = self.connection.players.get(name)
        player.online = True

    def on_icc_player_left(self, data):
        name = data.split()[0]
        self.connection.players.player_disconnected(name)

    def on_icc_who_am_i(self, data):
        name, titles = data.split(" ", 1)
        self.connection.username = name

    def on_icc_tourney(self, data):
        # index bitfield description join-command watch-command info-command confirm-text
        # 42 0 {Cooly Over 1500 Sunday Top Player Luton Blitz 5 0 rated Rating: 1500..3000 manager bigcol - 7 rounds Tournament Current round:1 Players:8, Latejoin allowed until round: 4} {tell Cooly latejoin & tell 224 Hi, i am in} {} {tell Cooly info} {Do you want to join the Cooly tournament}
        # 59 0 {Tomato U1600 Scheduled Swiss Blitz 2 5 rated Rating: 0..1599 manager Duguesclin - 7 rounds Tournament Current round:1 Players:13, Latejoin allowed until round: 4} {tell Tomato latejoin & tell 46 Hi, i am in} {} {tell Tomato info} {Do you want to join the Tomato tournament}
        # 64 0 {Yenta The STC Sunday Swiss Luton Standard 45 5 rated manager alonzob - 3 rounds Tournament Current round:2 Players:9, Latejoin allowed until round: 2} {tell Yenta latejoin & tell 232 Hi, i am in} {} {tell Yenta info} {Do you want to join the Yenta tournament}
        # 96 6 {} {} {} {} {}
        # 97 6 {[AUDIO] LIVE commentary with GM Ronen Har-Zvi and GM Alex Yermolinsky} {tell webcast listen} {} {} {}
        # 98 6 {[AUDIO] LIVE Espanol con el GM Jordi Magem (ESP)} {tell webcast espanol} {} {} {}
        # 99 6 {LIVE COVERAGE FIDE World Chess Championship 2016 - Game 7} {} {} {finger WorldChamp16} {}
        # 101 6 {LIVE GM Sergey Karjakin(2772) - GM Magnus Carlsen(2853)} {} {observe 1} {} {}
        # 319 6 {Nov 18-- [VIDEO] GM Ronen Har-Zvi analyzes game 6 of the World Chess Championship Match 2016} {} {https://webcast.chessclub.com/icc/i/WC16/Game5/GOTD.html} {https://www20.chessclub.com/article/fide-wc-match-2016-game-6} {}
        # 320 6 {Nov 20 -- [VIDEO] Attack with LarryC! Making Book with the Rook} {https://webcast.chessclub.com/icc/i/LarryC/2011_09_21/Attack_LarryC.html} {} {http://www.chessclub.com/chessfm/index/larryc/index.html} {}

        # TODO
        pass
