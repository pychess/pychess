
from gobject import *

names = "(\w+)(?:\(([CUHIFWM])\))?"

class ChatManager (GObject):
    
    __gsignals__ = {
        'channelMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'shoutMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str, str)),
        'kibitzMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'personalMessage' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_line_plus (self.onPrivateMessage,
                "%s tells you: (.*)" % names)
        #self.connection.expect_line_plus (self.onChannelMessage,
        #        "%s\(\d+\): (.*)" % names)
        #self.connection.expect_line_plus (self.onShoutMessage,
        #        "%s (c-)?shouts: (.*)" % names)
        
        print >> self.connection.client, "set kibitz 0"
        print >> self.connection.client, "set shout 0"
        
    def onPrivateMessage (self, matchlist):
        name, title, text = matchlist[0].groups()
        text = self.parseLines(text, matchlist[1:-1])
        print "Private message from %s: %s" % (name, text)
        print "Last line:", matchlist[-1].group()
        self.tellPlayer(name,
            "Automessage: I'm sorry, my chess client has yet to support chat.")
        #self.emit("personalMessage", name, text)
    
    def onChannelMessage (self, matchlist):
        channel, text = matchlist[0].groups()
        text = self.parseLines(text, matchlist[1:-1])
        self.emit("channelMessage", channel, text)
    
    def onShoutMessage (self, matchlist):
        name, title, type, text = matchlist[0].groups()
        text = self.parseLines(text, matchlist[1:-1])
        # c-shout should be used ONLY for chess-related messages, such as
        # questions about chess or announcing being open for certain kinds of
        # chess matches. Use "shout" for non-chess messages.
        type = type == "c-" and "chess", "other"
        self.emit("shoutMessage", name, type, text)
    
    def parseLines (self, start, lines):
        for line in lines:
            # Remember to remove the prefix: '\   '
            start += " " + line[4:]
        return start
    
    
    def tellPlayer (self, player, message):
        print >> self.connection.client, "tell %s %s" % (player, message)
    
    def tellChannel (self, channel, message):
        print >> self.connection.client, "tell %s %s" % (channel, message)
    
    def tellAll (self, message):
        print >> self.connection.client, "shout %s" % message
    
    def tellGame (self, gameno, message):
        print >> self.connection.client, "xkibitz %s %s" % (gameno, message)
