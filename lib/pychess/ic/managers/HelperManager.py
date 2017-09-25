import re

from gi.repository import GObject

from pychess.Utils.const import reprResult
from pychess.ic import GAME_TYPES_BY_SHORT_FICS_NAME, IC_STATUS_PLAYING, BLKCMD_GAMES, \
    GAME_TYPES, TITLES, TYPE_BLITZ, parse_title_hex, TYPE_ATOMIC, TYPE_WILD, \
    TYPE_STANDARD, TYPE_LIGHTNING, TYPE_CRAZYHOUSE, TYPE_LOSERS, TYPE_BUGHOUSE, \
    TYPE_SUICIDE, DEVIATION, STATUS, BLKCMD_WHO, IC_STATUS_NOT_AVAILABLE, \
    IC_STATUS_AVAILABLE, parseRating
from pychess.ic.FICSObjects import FICSPlayer, FICSGame
from pychess.ic.managers.BoardManager import parse_reason

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|WFM|TM|SR|TD|CA|CM|FA|NM|C|U|D|B|T|H|\*)"
titleslist_re = re.compile(titleslist)
titles = "((?:\(%s\))+)?" % titleslist
names = "([a-zA-Z]+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
whomatch = "(?:(?:([-0-9+]{1,4})([\^~:\#. &])%s))" % names
whomatch_re = re.compile(whomatch)
whoI = "([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])" * 8 + "(\d{1,4})([PE]?)"
re_whoI = re.compile(whoI)


class HelperManager(GObject.GObject):
    def __init__(self, helperconn, connection):
        GObject.GObject.__init__(self)

        self.helperconn = helperconn
        self.connection = connection

        # TODO: Examined games
        # 25 (Exam.    0 Friar          0 Friar     ) [ uu  0   0] W:  1
        # 28 ++++ TryMe       1737 Jack       [ su 30  20]  22:27 - 23:17 (29-30) W: 16
        # 2 2274 OldManII    ++++ Peshkin    [ bu  2  12]   2:34 -  1:47 (39-39) B:  3
        # 29 1622 Vman        1609 PopKid     [ sr 10  10]   1:14 -  5:10 (21-22) B: 18
        # 32 1880 Raskapov    1859 RoboDweeb  [ br  2  12]   1:04 -  1:26 ( 9-10) B: 34
        # 1 1878 Roberto     1881 baraka     [psr 45  30]  30:35 - 34:24 (22-22) W: 21
        #
        # 6 games displayed (of 23 in progress)
        self.helperconn.expect_fromto(
            self.on_game_list,
            "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(%s)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d:)?(\d+):(\d+)\s*-\s*(\d:)?(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)"
            %
            (ratings, ratings, "|".join(GAME_TYPES_BY_SHORT_FICS_NAME.keys())),
            "(\d+) games displayed.")

        if self.helperconn.FatICS or self.helperconn.USCN:
            self.helperconn.expect_line(self.on_player_who, "%s(?:\s{2,}%s)+" %
                                        (whomatch, whomatch))
            self.helperconn.expect_line(self.on_player_connect,
                                        "\[([A-Za-z]+) has connected\.\]")
            self.helperconn.expect_line(self.on_player_disconnect,
                                        "\[([A-Za-z]+) has disconnected\.\]")
        else:
            # New ivar pin
            # http://www.freechess.org/Help/HelpFiles/new_features.html
            self.helperconn.expect_fromto(self.on_player_whoI, whoI, "(\d+) Players Displayed.")
            self.helperconn.expect_line(self.on_player_connectI, "<wa> %s" % whoI)
            self.helperconn.expect_line(self.on_player_disconnectI, "<wd> ([A-Za-z]+)")

        self.helperconn.expect_line(
            self.on_game_add,
            "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) ([^ ]+) match\.\}$")
        self.helperconn.expect_line(
            self.on_game_remove,
            "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+ .+)\} (\*|1/2-1/2|1-0|0-1)$")
        self.helperconn.expect_line(self.on_player_unavailable,
                                    "%s is no longer available for matches." %
                                    names)
        self.helperconn.expect_fromto(
            self.on_player_available,
            "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)"
            % (names, ratings, ratings, ratings, ratings, ratings),
            "is now available for matches.")

        # FICS game types
        # b: blitz      l: lightning   u: untimed      e: examined game
        # s: standard   w: wild        x: atomic       z: crazyhouse
        # B: Bughouse   L: losers      S: Suicide
        if self.helperconn.FatICS or self.helperconn.USCN:
            self.helperconn.client.run_command("who")
        else:
            self.helperconn.client.run_command("who IbslwBzSLx")

        if self.helperconn.FatICS or self.helperconn.USCN:
            self.helperconn.client.run_command("games")
        else:
            self.helperconn.client.run_command("games /bslwBzSLx")

    def on_game_list(self, matchlist):
        games = []
        for match in matchlist[:-1]:
            if isinstance(match, str):
                if match:
                    parts0, parts1 = match.split("[")
                    gameno, wrating, wname, brating, bname = parts0.split()
                    private = parts1[0]
                    shorttype = parts1[1]
                    rated = parts1[2]
                    min = parts1[3:6]
                    inc = parts1[7:10]
                else:
                    continue
            else:
                gameno, wrating, wname, brating, bname, private, shorttype, rated, min, \
                    inc, whour, wmin, wsec, bhour, bmin, bsec, wmat, bmat, color, movno = match.groups()
            try:
                gametype = GAME_TYPES_BY_SHORT_FICS_NAME[shorttype]
            except KeyError:
                return

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
                if player.ratings[gametype.rating_type] != rating:
                    player.ratings[gametype.rating_type] = rating
                    player.emit("ratings_changed", gametype.rating_type, player)
            game = self.connection.games.get(game, emit=False)
            games.append(game)
        self.connection.games.emit("FICSGameCreated", games)
        # print(matchlist[-1].groups()[0], len(games))

    on_game_list.BLKCMD = BLKCMD_GAMES

    def on_game_add(self, match):
        gameno, wname, bname, rated, game_type = match.groups()
        if game_type not in GAME_TYPES:
            return
        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        game = FICSGame(wplayer,
                        bplayer,
                        gameno=int(gameno),
                        rated=(rated == "rated"),
                        game_type=GAME_TYPES[game_type])

        for player in (wplayer, bplayer):
            if player.status != IC_STATUS_PLAYING:
                player.status = IC_STATUS_PLAYING
            if player.game != game:
                player.game = game

        self.connection.games.get(game)

    def on_game_remove(self, match):
        gameno, wname, bname, comment, result = match.groups()
        result, reason = parse_reason(
            reprResult.index(result),
            comment,
            wname=wname)

        try:
            wplayer = self.connection.players.get(wname)
            wplayer.restore_previous_status()
            # no status update will be sent by
            # FICS if the player doesn't become available, so we restore
            # previous status first (not necessarily true, but the best guess)
        except KeyError:
            print("%s not in self.connections.players - creating" % wname)
            wplayer = FICSPlayer(wname)

        try:
            bplayer = self.connection.players.get(bname)
            bplayer.restore_previous_status()
        except KeyError:
            print("%s not in self.connections.players - creating" % bname)
            bplayer = FICSPlayer(bname)

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=int(gameno),
                        result=result,
                        reason=reason)
        if wplayer.game is not None:
            game.rated = wplayer.game.rated
        game = self.connection.games.get(game, emit=False)

        # Our played/observed game ends are handled in main connection to prevent
        # removing them by helper connection before latest move(style12) comes from server
        if game == self.connection.bm.theGameImPlaying or \
           game in self.connection.bm.gamesImObserving:
            return

        self.connection.games.game_ended(game)
        # Do this last to give anybody connected to the game's signals a chance
        # to disconnect from them first
        wplayer.game = None
        bplayer.game = None

    @staticmethod
    def parseTitles(titles):
        _titles = set()
        if titles:
            for title in titleslist_re.findall(titles):
                if title in TITLES:
                    _titles.add(TITLES[title])
        return _titles

    def on_player_connectI(self, match, set_online=True):
        # bslwBzSLx
        # gbtami 001411E1663P1483P1720P0P1646P0P0P1679P
        name, status, titlehex, blitz, blitzdev, std, stddev, light, lightdev, \
            wild, wilddev, bughouse, bughousedev, crazyhouse, crazyhousedev, \
            suicide, suicidedev, losers, losersdev, atomic, atomicdev = match.groups()
        player = self.connection.players.get(name)

        titles = parse_title_hex(titlehex)
        if not player.titles >= titles:
            player.titles |= titles

        for rating_type, elo, dev in \
                ((TYPE_BLITZ, blitz, blitzdev),
                 (TYPE_STANDARD, std, stddev),
                 (TYPE_LIGHTNING, light, lightdev),
                 (TYPE_ATOMIC, atomic, atomicdev),
                 (TYPE_WILD, wild, wilddev),
                 (TYPE_CRAZYHOUSE, crazyhouse, crazyhousedev),
                 (TYPE_BUGHOUSE, bughouse, bughousedev),
                 (TYPE_LOSERS, losers, losersdev),
                 (TYPE_SUICIDE, suicide, suicidedev)):
            rating = parseRating(elo)
            if player.ratings[rating_type] != rating:
                player.ratings[rating_type] = rating
                player.emit("ratings_changed", rating_type, player)
            player.deviations[rating_type] = DEVIATION[dev]

        # do last so rating info is there when notifications are generated
        status = STATUS[status]
        if player.status != status:
            player.status = status
        if set_online and not player.online:
            player.online = True

        return player

    def on_player_disconnectI(self, match):
        name = match.groups()[0]
        self.connection.players.player_disconnected(name)

    def on_player_whoI(self, matchlist):
        players = []
        for match in matchlist[:-1]:
            if isinstance(match, str):
                if match:
                    players.append(self.on_player_connectI(re_whoI.match(match)))
                else:
                    continue
            else:
                players.append(self.on_player_connectI(match))

        self.connection.players.emit("FICSPlayerEntered", players)
        # print(matchlist[-1].groups()[0], len(players))

    on_player_whoI.BLKCMD = BLKCMD_WHO

    def on_player_who(self, match):
        for blitz, status, name, titles in whomatch_re.findall(match.string):
            player = self.connection.players.get(name)
            if not player.online:
                player.online = True
            status = STATUS[status]
            if player.status != status:
                player.status = status
            titles = self.parseTitles(titles)
            if not player.titles >= titles:
                player.titles |= titles
            blitz = parseRating(blitz)
            if player.ratings[TYPE_BLITZ] != blitz:
                player.ratings[TYPE_BLITZ] = blitz
                player.emit("ratings_changed", TYPE_BLITZ, player)

    def on_player_connect(self, match):
        name = match.groups()[0]
        player = self.connection.players.get(name)
        player.online = True

    def on_player_disconnect(self, match):
        name = match.groups()[0]
        self.connection.players.player_disconnected(name)

    def on_player_unavailable(self, match):
        name, titles = match.groups()
        player = self.connection.players.get(name)
        titles = self.parseTitles(titles)
        if not player.titles >= titles:
            player.titles |= titles
        # we get here after players start a game, so we make sure that we don't
        # overwrite IC_STATUS_PLAYING
        if player.game is None and \
                player.status not in (IC_STATUS_PLAYING, IC_STATUS_NOT_AVAILABLE):
            player.status = IC_STATUS_NOT_AVAILABLE

    def on_player_available(self, matches):
        name, titles, blitz, std, wild, light, bughouse = matches[0].groups()
        player = self.connection.players.get(name)

        if not player.online:
            player.online = True
        if player.status != IC_STATUS_AVAILABLE:
            player.status = IC_STATUS_AVAILABLE
        titles = self.parseTitles(titles)
        if not player.titles >= titles:
            player.titles |= titles

        for rating_type, rating in ((TYPE_BLITZ, blitz), (TYPE_STANDARD, std),
                                    (TYPE_LIGHTNING, light), (TYPE_WILD, wild),
                                    (TYPE_BUGHOUSE, bughouse)):
            rating = parseRating(rating)
            if player.ratings[rating_type] != rating:
                player.ratings[rating_type] = rating
                player.emit("ratings_changed", rating_type, player)
