
class DisconnectManager:
    def __init__ (self, connection):
        self.connection = connection
    
    def disconnect (self):
        print >> self.connection.client, "quit"
        self.connection.disconnect()
