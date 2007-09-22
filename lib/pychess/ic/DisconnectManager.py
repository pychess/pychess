import telnet
from ICManager import ICManager

class DisconnectManager (ICManager):
    def disconnect (self):
        print >> telnet.client, "quit"
        telnet.disconnect()

dm = DisconnectManager()
