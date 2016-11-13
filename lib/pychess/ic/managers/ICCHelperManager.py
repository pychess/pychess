from gi.repository import GObject

from pychess.ic.FICSObjects import FICSGame
from pychess.ic.managers.HelperManager import HelperManager
from pychess.ic import parseRating, GAME_TYPES_BY_SHORT_FICS_NAME, IC_STATUS_PLAYING, TYPE_BLITZ
from pychess.ic.icc import DG_PLAYER_ARRIVED, DG_PLAYER_ARRIVED_SIMPLE, \
    DG_PLAYER_LEFT, DG_MY_GAME_RESULT, DG_RATING_TYPES, DG_BLITZ

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
            "(\d+) %s (\w+)\s+%s (\w+)\s+(%s)(u|r)\s*(\d+)\s+(\d+)\s*(W|B):\s*(\d+)"
            %
            (ratings, ratings, "|".join(GAME_TYPES_BY_SHORT_FICS_NAME.keys())),
            "(\d+) games displayed \(.+\).")

        self.helperconn.expect_line(self.on_icc_player_arrived, "%s (.+)" % DG_PLAYER_ARRIVED_SIMPLE)
        self.helperconn.expect_line(self.on_icc_player_left, "%s (.+)" % DG_PLAYER_LEFT)
        self.helperconn.expect_line(self.on_icc_blitz, "%s (.+)" % DG_BLITZ)

        self.connection.expect_line(self.on_icc_my_game_result, "%s (.+)" % DG_MY_GAME_RESULT)

        self.helperconn.client.run_command("set-2 %s 1" % DG_PLAYER_ARRIVED_SIMPLE)
        self.helperconn.client.run_command("set-2 %s 1" % DG_PLAYER_ARRIVED)
        self.helperconn.client.run_command("set-2 %s 1" % DG_PLAYER_LEFT)
        self.helperconn.client.run_command("set-2 %s 1" % DG_BLITZ)
        for rating in DG_RATING_TYPES:
            self.helperconn.client.run_command("set-2 %s 1" % rating)

        # Unfortunately we can't maintain a list of games
        # From https://www.chessclub.com/user/resources/formats/formats.txt
        # Here is the list of verbose DGs:
        # DG_PLAYER_ARRIVED DG_PLAYER_LEFT
        # DG_GAME_STARTED DG_GAME_RESULT DG_EXAMINED_GAME_IS_GONE
        # DG_PEOPLE_IN_MY_CHANNEL DG_CHANNELS_SHARED DG_SEES_SHOUTS
        # Currently, only TDs like Tomato can use these.
        self.helperconn.client.run_command("games")
        self.helperconn.client.run_command("set-2 %s 1" % DG_MY_GAME_RESULT)

    def on_icc_game_list(self, matchlist):
        games = []
        for match in matchlist[:-1]:
            if isinstance(match, str):
                if match:
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
                continue
                # TODO:
                # return

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
        # print(matchlist[-1].groups()[0], len(games))

    def on_icc_my_game_result(self, match):
        # gamenumber become-examined game_result_code score_string2 description-string ECO
        # TODO:
        parts = match.groups()[0].split()
        print("my_game_result", parts)

    on_icc_my_game_result.BLKCMD = DG_MY_GAME_RESULT

    def on_icc_player_arrived(self, match):
        name = match.groups()[0].split()[0]
        player = self.connection.players.get(name)
        player.online = True

    on_icc_player_arrived.BLKCMD = DG_PLAYER_ARRIVED_SIMPLE

    def on_icc_player_left(self, match):
        name = match.groups()[0].split()[0]
        self.connection.players.player_disconnected(name)

    on_icc_player_left.BLKCMD = DG_PLAYER_LEFT

    def on_icc_blitz(self, match):
        # playername rating annotation
        # 0 no rating, 1 provisional, 2 established
        name, blitz, annotation = match.groups()[0].split()
        player = self.connection.players.get(name)
        if player.ratings[TYPE_BLITZ] != blitz:
            player.ratings[TYPE_BLITZ] = blitz
            player.emit("ratings_changed", TYPE_BLITZ, player)

    on_icc_blitz.BLKCMD = DG_BLITZ
