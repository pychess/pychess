from gi.repository import GLib, GObject

from pychess.ic import GAME_TYPES
from pychess.ic.icc import DG_PLAYERS_IN_MY_GAME, DG_KIBITZ, DG_PERSONAL_TELL, \
    DG_SHOUT, DG_CHANNEL_TELL, DG_PEOPLE_IN_MY_CHANNEL, DG_CHANNELS_SHARED
from pychess.ic.managers.ChatManager import ChatManager

CHANNEL_SHOUT = "shout"
CHANNEL_CSHOUT = "cshout"


class ICCChatManager(ChatManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_PLAYERS_IN_MY_GAME, self.on_icc_players_in_my_game)
        self.connection.expect_dg_line(DG_KIBITZ, self.on_icc_kibitz)
        self.connection.expect_dg_line(DG_PERSONAL_TELL, self.on_icc_personal_tell)
        self.connection.expect_dg_line(DG_SHOUT, self.on_icc_shout)
        self.connection.expect_dg_line(DG_CHANNEL_TELL, self.on_icc_channel_tell)
        self.connection.expect_dg_line(DG_PEOPLE_IN_MY_CHANNEL, self.on_icc_people_in_my_channel)
        self.connection.expect_dg_line(DG_CHANNELS_SHARED, self.on_icc_channels_shared)

        self.connection.client.run_command("set-2 %s 1" % DG_PLAYERS_IN_MY_GAME)
        self.connection.client.run_command("set-2 %s 1" % DG_KIBITZ)
        self.connection.client.run_command("set-2 %s 1" % DG_PERSONAL_TELL)
        self.connection.client.run_command("set-2 %s 1" % DG_SHOUT)
        self.connection.client.run_command("set-2 %s 1" % DG_CHANNEL_TELL)
        self.connection.client.run_command("set-2 %s 1" % DG_PEOPLE_IN_MY_CHANNEL)
        self.connection.client.run_command("set-2 %s 1" % DG_CHANNELS_SHARED)

        self.currentLogChannel = None

        self.connection.client.run_command("set Lang English")

        self.connection.client.run_command("set height 240")

        self.connection.client.run_command("inchannel %s" %
                                           self.connection.username)
        self.connection.client.run_command("help channel_list")
        self.observers = {}

        self.channels = [(CHANNEL_SHOUT, _("Shout")),
                         (CHANNEL_CSHOUT, _("Chess Shout"))]

        for id, channel in ICC_CHANNELS:
            self.channels.append((str(id), channel))
        GLib.idle_add(self.emit, 'channelsListed', self.channels)

    def on_icc_players_in_my_game(self, data):
        # gamenumber playername symbol kibvalue
        # O=observing
        # PW=playing white
        # PB=playing black
        # SW=playing simul and is white
        # SB=playing simul and is black
        # E=Examining
        # X=None (has left the table)

        gameno, name, symbol, kibvalue = data.split()

        ficsplayer = self.connection.players.get(name)
        rating = ficsplayer.getRatingByGameType(GAME_TYPES['standard'])
        if rating:
            name = "%s(%s)" % (name, rating)

        if gameno not in self.observers:
            observers = set()
            self.observers[gameno] = observers

        if symbol == "O":
            self.observers[gameno].add(name)
        elif symbol == "X" and name in self.observers[gameno]:
            self.observers[gameno].remove(name)

        obs_str = " ".join(list(self.observers[gameno]))
        self.emit('observers_received', gameno, obs_str)

    def on_icc_kibitz(self, data):
        # gamenumber playername titles kib/whi ^Y{kib string^Y}
        gameno, name, rest = data.split(" ", 2)
        titles, rest = rest.split("}", 1)
        kib_whi, text = rest[1:].split(" ", 1)
        text = text[2:-2]

        if kib_whi == "1":
            GLib.idle_add(self.emit, "kibitzMessage", name, int(gameno), text)
        else:
            GLib.idle_add(self.emit, "whisperMessage", name, int(gameno), text)

    def on_icc_personal_tell(self, data):
        # playername titles ^Y{tell string^Y} type
        name, rest = data.split(" ", 1)
        titles, rest = rest.split("}", 1)
        text, tell_type = rest[3:].split("}")
        isadmin = tell_type == "4"
        GLib.idle_add(self.emit, "privateMessage", name, "title", isadmin, text[:-1])

    def on_icc_shout(self, data):
        # playername titles type ^Y{shout string^Y}
        name, rest = data.split(" ", 1)
        titles, rest = rest.split("}", 1)
        shout_type, text = rest[1:].split("{")
        # print(name, shout_type, text)
        isadmin = shout_type == "3"  # announcements
        isme = name.lower() == self.connection.username.lower()
        GLib.idle_add(self.emit, "channelMessage", name, isadmin, isme, "shout", text[:-2])

    def on_icc_channel_tell(self, data):
        # channel playername titles ^Y{tell string^Y} type
        channel, name, rest = data.split(" ", 2)
        titles, rest = rest.split("}", 1)
        text, tell_type = rest[3:].split("}")
        isme = name.lower() == self.connection.username.lower()
        isadmin = tell_type == "4"
        GLib.idle_add(self.emit, "channelMessage", name, isadmin, isme, channel, text)

    def on_icc_people_in_my_channel(self, data):
        # channel playername come/go
        print(data)

    def on_icc_channels_shared(self, data):
        # playername channels
        print(data)


ICC_CHANNELS = (
    (0, "Admins only"),
    (1, "Newbie Help"),
    (2, "Experienced Help"),
    (3, "Simul"),
    (4, "SimulBot2"),
    (5, "Wild 5"),
    (7, "Wild 7"),
    (10, "Team-Setup"),
    (11, "Team Game Channel A"),
    (12, "Team Game Channel B"),
    (14, "Macintosh users channel"),
    (22, "Fischer-Random Chess"),
    (23, "Crazyhouse Channel"),
    (24, "BUGHOUSE Channel"),
    (25, "3 checks you win"),
    (26, "Giveaway Chess"),
    (27, "Atomic Channel"),
    (28, "Shatranj Channel"),
    (32, "STtourney channel"),
    (34, "Sports"),
    (43, "Chess theory"),
    (46, "Tomato TD"),
    (47, "Tomato tournament managers"),
    (49, "Flash TD"),
    (64, "Computer chess"),
    (65, "Canadian"),
    (66, "Australia"),
    (67, "British"),
    (68, "South Africa"),
    (69, "Singapore and Malaysia"),
    (70, "Greek"),
    (71, "Spanish"),
    (72, "French"),
    (73, "German"),
    (74, "Dutch"),
    (75, "Russian"),
    (76, "Italian"),
    (77, "Japanese"),
    (78, "Scandinavian(Denmark,Norway,Sweden)"),
    (79, "Icelandic"),
    (80, "Finnish"),
    (81, "Portuguese"),
    (82, "Catalan"),
    (83, "Hebrew"),
    (84, "Turkish"),
    (86, "ASCII art"),
    (88, "China"),
    (90, "Slow time controls"),
    (97, "Politics"),
    (100, "Admins and helpers only"),
    (101, "Music"),
    (103, "Religious Discussions/Debates"),
    (107, "Math and Science"),
    (110, "Philosophy"),
    (114, "Health and Medicine"),
    (116, "Wild 16 (Kriegspiel)"),
    (117, "Wild 17 (Losers Chess)"),
    (123, "Acrobot"),
    (129, "USCL (United States Chess League)"),
    (147, "Tomato senior managers group"),
    (165, "ICC Radio Broadcast and Chess Events"),
    (183, "Correspondence Chess"),
    (185, "Philippine"),
    (186, "Irish"),
    (220, "Query all the Tomato-type TD bots"),
    (221, "The 'Ask for a Tournament' Channel"),
    (222, "Slomato TD (Slow Tournaments)"),
    (223, "WildOne TD (Wild Tournaments)"),
    (224, "Cooly TD (Tournaments)"),
    (225, "LittlePer TD (Tournaments)"),
    (226, "Automato TD (Special Event Tournaments)"),
    (227, "Pear TD (Special Event Tournaments)"),
    (228, "Ketchup TD (Tournaments)"),
    (229, "Channel for Tournament Robots to interact"),
    (230, "Olive TD (Tournaments)"),
    (232, "Yenta TD (Special Event Tournaments)"),
    (250, "Lobby"),
    (271, "LatinTrivia Channel (Spanish)"),
    (272, "TriviaBot Channel"),
    (274, "Spam channel"),
    (280, "BettingBot"),
    (291, "Scholastic Chess Coaches"),
    (300, "Helpers and Administrators"),
    (302, "Busters"),
    (303, "Christian"),
    (333, "AtheistAgnostic"),
    (334, "Johns Hopkins CTY"),
    (335, "SimulBot"),
    (337, "Broadcast"),
    (338, "Relay coordination"),
    (340, "LeChessClub"),
    (345, "Team4545League"),
    (348, "Tomato Trainers group"),
    (394, "Tomato admins group"),
    (396, "Complain"),
    (397, "Politics-Reserved"),
    (399, "Events"),
)
