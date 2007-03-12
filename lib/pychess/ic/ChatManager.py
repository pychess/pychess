
import telnet
from gobject import *

names = "(\w+)(?:\(([CUHIFWM])\))?"

class ChatManager (GObject):
    
    __gsignals__ = {
        'channelReceive' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int, str)),
        'shoutReceive' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'kibitzReceive' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
        'personalReceive' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str))
    }
    
    def __init__ (self):
        GObject.__init__(self)
        self.channel = 4
        
        telnet.expect ( "%s tells you: (.*?)\n" % names, self.onPrivaetMessage )
        telnet.expect ( "%s\(\d+): (.*?)\n" % names, self.onChannelMessage )
    
    def start (self):
        print >> telnet.client, "set shout 0"
    
    def setChannel (self, channel):
        self.channel = channel
    
    def onPrivaetMessage (self, client, groups):
        name, title, message = groups
    
    def onChannelMessage (self, client, groups):
        name, title, channel, message = groups
    
    def tell (self, message):
        print >> telnet.client, "tell %d %s" % (self.channel, message)
