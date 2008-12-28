
from gobject import *
import threading
import re
from math import ceil
import time

from pychess.System.Log import log

titles = "(?:\([A-Z*]+\))*"
names = "([A-Za-z]+)"+titles
titlesC = re.compile(titles)
namesC = re.compile(names)

CHANNEL_SHOUT = "shout"
CHANNEL_CSHOUT = "cshout"

class ChatManager (GObject):
    
    __gsignals__ = {
        'channelMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, bool, bool, str, str)),
        'kibitzMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'privateMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str, bool, str)),
        'bughouseMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'announcement' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        
        'channelAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'channelRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'channelJoinError': (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        
        'channelLog' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, int, str, str)),
        'toldChannel' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, int)),
        
        'recievedChannels' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        'recievedNames' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_line_plus (self.onPrivateMessage,
                "%s(\*)?(?:\[(\d+)\])? (?:tells you|says): (.*)" % names)
        self.connection.expect_line_plus (self.onAnnouncement,
                "\s*\*\*ANNOUNCEMENT\*\* (.*)")
        self.connection.expect_line_plus (self.onChannelMessage,
                "%s(\*)?\((\d+)\): (.*)" % names)
        self.connection.expect_line_plus (self.onShoutMessage,
                "%s(\*)? (c-)?shouts: (.*)" % names)
        self.connection.expect_line_plus (self.onShoutMessage,
                "--> %s(\*)?:? (.*)" % names)
        
        self.connection.expect_fromto (self.onChannelList,
                "channels only for their designated topics.",
                "SPECIAL NOTE")
        
        self.connection.expect_line (lambda m: self.emit('channelAdd', m.groups()[0]),
                "\[(\d+)\] added to your channel list.")
        self.connection.expect_line (lambda m: self.emit('channelRemove', m.groups()[0]),
                "\[(\d+)\] removed to your channel list.")
        
        self.connection.expect_line (lambda m: self.emit('channelJoinError', *m.groups()),
                "Only (.+?) may join channel (\d+)\.")
        
        self.connection.expect_line (self.getNoChannelPlayers,
                "Channel \d+ is empty\.")
        self.connection.expect_fromto (self.getChannelPlayers,
                "Channel (\d+)(?: \"(\w+)\")?: (.+)",
                "(\d+) player(?: is|s are) in channel \d+\.")
        
        self.connection.expect_fromto (self.gotPlayerChannels,
                "%s is in the following channels:" % names,
                "(?!(?:\d+\s+)+)")
    
        #self.connection.expect_line (self.toldChannel,
        #        '\(told (\d+) players in channel (\d+) ".+"\)')
        #(told Chronatog)
        
        #Only chess advisers and admins may join channel 63.
        #Only (.+?) may sey send tells to channel (\d+).
        #Only admins may send tells to channel 0.
        #Only registered users may send tells to channels other than 4, 7 and 53.
        
        self.currentLogChannel = None
        self.connection.expect_line (self.onChannelLogStart,
                ":Channel (\d+|shout|c-shout) log for the last \d+ minutes:$")
        self.connection.expect_line (self.onChannelLogLine,
                ":\[(\d+):(\d+):(\d+)\] (?:(?:--> )?%s(?: shouts)?)\S* (.+)$" % names)
        self.connection.expect_line (self.onChannelLogBreak,
                ":Use \"tell chLog Next\" to print more.$")
        
        #TODO handling of this case is nessesary for console:
        #fics% tell 1 hi
        #You are not in channel 1, auto-adding you if possible.
        
        self.connection.lvm.setVariable("kibitz", "0")
        self.connection.lvm.setVariable("ctell", "1")
        self.connection.lvm.setVariable("tell", "1")
        self.connection.lvm.setVariable("height", "240")
        
        print >> self.connection.client, "inchannel lobais"
        print >> self.connection.client, "help channel_list"
        
        self.getChannelsLock = threading.Semaphore()
        self.getChannelsLock.acquire()
        self.channels = {}
    
    def getChannels(self):
        self.getChannelsLock.acquire()
        self.getChannelsLock.release()
        return self.channels
    
    def getJoinedChannels(self):
        channels = self.connection.lvm.getList("channel")
        if self.connection.lvm.getVariable("shout"):
            channels.add(CHANNEL_SHOUT)
        if self.connection.lvm.getVariable("cshout"):
            channels.add(CHANNEL_CSHOUT)
        return channels
    
    channelListItem = re.compile("((?:\d+,?)+)\s*(.*)")
    def onChannelList(self, matchlist):
        self.channels = [(CHANNEL_SHOUT, _("Shout")),
                         (CHANNEL_CSHOUT, _("Chess Shout"))]
        numbers = set(range(256)) #TODO: Use limits->Server->Channels
        for line in matchlist[1:-1]:
            match = self.channelListItem.match(line)
            if not match: continue
            ids, desc = match.groups()
            for id in ids.split(","):
                numbers.remove(int(id))
                self.channels.append((id, desc))
        for i in numbers:
            self.channels.append((str(i), _("Unofficial channel %d" % i)))
        self.getChannelsLock.release()
    
    def getNoChannelPlayers (self, match):
        channel = match.groups()[0]
        self.emit('recievedNames', channel, [])
    
    def getChannelPlayers(self, matchlist):
        channel, name, people = matchlist[0].groups()
        people += " " + " ".join(matchlist[1:-1])
        people = namesC.findall(titlesC.sub("",people))
        self.emit('recievedNames', channel, people)
    
    def gotPlayerChannels(self, matchlist):
        name = matchlist[0].groups()
        list = []
        for line in matchlist[1:-1]:
            list += line.split()
        
    
    def onPrivateMessage (self, matchlist):
        name, isadmin, gameno, text = matchlist[0].groups()
        text += " " + " ".join(matchlist[1:])
        text = self.entityDecode(text)
        self.emit("privateMessage", name, "title", isadmin, text)
    
    def onAnnouncement (self, matchlist):
        text = matchlist[0].groups()[0]
        text += " " + " ".join(matchlist[1:-1])
        text = self.entityDecode(text)
        self.emit("announcement", text)
    
    def onChannelMessage (self, matchlist):
        name, isadmin, channel, text = matchlist[0].groups()
        text += " " + " ".join(matchlist[1:])
        text = self.entityDecode(text)
        isme = name.lower() == self.connection.username.lower()
        self.emit("channelMessage", name, isadmin, isme, channel, text)
    
    def onShoutMessage (self, matchlist):
        if len(matchlist[0].groups()) == 4:
            name, isadmin, type, text = matchlist[0].groups()
        elif len(matchlist[0].groups()) == 3:
            name, isadmin, text = matchlist[0].groups()
            type = ""
        text += " " + " ".join(matchlist[1:])
        text = self.entityDecode(text)
        isme = name.lower() == self.connection.username.lower()
        # c-shout should be used ONLY for chess-related messages, such as
        # questions about chess or announcing being open for certain kinds of
        # chess matches. Use "shout" for non-chess messages.
        
        # t-shout is used to invite to tournaments
        if type == "c-":
            self.emit("channelMessage", name, isadmin, isme, CHANNEL_CSHOUT, text)
        else:
            self.emit("channelMessage", name, isadmin, isme, CHANNEL_SHOUT, text)
    
    def toldChannel (self, match):
        amount, channel = match.groups()
        self.emit("toldChannel", channel, int(amount))
    
    def onChannelLogStart (self, match):
        channel, = match.groups()
        self.currentLogChannel = channel
    
    def onChannelLogLine (self, match):
        if not self.currentLogChannel:
            log.warn("Recieved log line before channel was set")
            return
        h, m, s, handle, text = match.groups()
        time = self.convTime(int(h), int(m), int(s))
        text = self.entityDecode(text)
        self.emit("channelLog", self.currentLogChannel, time, handle, text)
    
    def onChannelLogBreak (self, match):
        print >> self.connection.client, "xtell chlog Next"
    
    
    def convTime (self, h, m, s):
        # Convert to timestamp
        tlist = [u for u in time.localtime()]
        tstamp = time.mktime(tlist[0:3]+[h, m, s, 0, 0, 0])
        # Difference to now in hours
        dif = (tstamp-time.time())/60./60.
        # As we know there is maximum 30 minutes in difference, we can guess when the
        # message was sent, without knowing the sending time zone
        return tstamp - ceil(dif)*60*60
    
    entityExpr = re.compile("&#x([a-f0-9]+);")
    def entityDecode (self, text):
        return self.entityExpr.sub(lambda m: unichr(int(m.groups()[0],16)), text)
    
    def entityEncode (self, text):
        buf = []
        for c in text:
            if not 32 <= ord(c) <= 127:
                c = "&#" + hex(ord(c))[1:] + ";"
            buf.append(c)
        return "".join(buf)
    
    
    def getChannelLog (self, channel, minutes=30):
        """ Channel can be channel_id, shout or c-shout """
        assert 1 <= minutes <= 120
        # Using the chlog bot
        print >> self.connection.client, "xtell chlog show %s -t %d" % (channel,minutes)
    
    def getPlayersChannels (self, player):
        print >> self.connection.client, "inchannel %s" % player
    
    def getPeopleInChannel (self, channel):
        if channel in (CHANNEL_SHOUT, CHANNEL_CSHOUT):
            people = self.connection.glm.getPlayerlist()
            self.emit('recievedNames', channel, people)
        print >> self.connection.client, "inchannel %s" % channel
    
    def joinChannel (self, channel):
        if channel in (CHANNEL_SHOUT, CHANNEL_CSHOUT):
            self.connection.lvm.setVariable(channel, True)
        print >> self.connection.client, "+channel %s" % channel
    
    def removeChannel (self, channel):
        if channel in (CHANNEL_SHOUT, CHANNEL_CSHOUT):
            self.connection.lvm.setVariable(channel, False)
        print >> self.connection.client, "-channel %s" % channel
    
    
    def mayTellChannel (self, channel):
        if self.connection.isRegistred() or channel in ("4", "7", "53"):
            return True
        return False
    
    def tellPlayer (self, player, message):
        message = self.entityEncode(message)
        print >> self.connection.client, "tell %s %s" % (player, message)
    
    def tellChannel (self, channel, message):
        message = self.entityEncode(message)
        if channel == CHANNEL_SHOUT:
            print >> self.connection.client, "shout %s" % message
        elif channel == CHANNEL_CSHOUT:
            print >> self.connection.client, "cshout %s" % message
        else:
            print >> self.connection.client, "tell %s %s" % (channel, message)
    
    def tellAll (self, message):
        message = self.entityEncode(message)
        print >> self.connection.client, "shout %s" % message
    
    def tellGame (self, gameno, message):
        message = self.entityEncode(message)
        print >> self.connection.client, "xkibitz %s %s" % (gameno, message)
    
    def tellOpponent (self, message):
        message = self.entityEncode(message)
        print >> self.connection.client, "say %s" % message
    
    def tellBughousePartner (self, message):
        message = self.stripChars(message)
        print >> self.connection.client, "ptell %s" % message
    
    def tellUser (self, player, message):
        IS_TD = False
        if IS_TD:
            MAX_COM_SIZE = 1024 #TODO: Get from limits
            for i in xrange(0,len(message),MAX_COM_SIZE):
                chunk = message[i:i+MAX_COM_SIZE]
                chunk = chunk.replace("\n", "\\n")
                chunk = self.entityEncode(chunk)
                print >> self.connection.client, "qell %s %s" % (player, chunk)
        else:
            for line in message.strip().split("\n"):
                self.tellPlayer(player, line)
