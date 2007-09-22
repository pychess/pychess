from gobject import GObject
from pychess.Utils.const import IC_CONNECTED
import telnet

class ICManager (GObject):
    def start (self):
        pass
    
    def stop (self):
        pass
    
    def __init__ (self):
        GObject.__init__(self)
        
        def onStatusChanged (client, signal):
            if signal == IC_CONNECTED:
                self.start()
            else:
                self.stop()
        telnet.connectStatus (onStatusChanged)
