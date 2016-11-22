from gi.repository import GObject

from pychess.ic.managers.FingerManager import FingerManager, FingerObject


class ICCFingerManager(FingerManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

    def on_icc_finger(self, data):
        finger = FingerObject()
        # TODO
        self.emit("fingeringFinished", finger)

    def finger(self, user):
        self.connection.client.run_command("yfinger %s" % user)
