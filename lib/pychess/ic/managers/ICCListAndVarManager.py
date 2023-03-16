from pychess.System import conf
from pychess.ic.managers.ListAndVarManager import ListAndVarManager


class ICCListAndVarManager(ListAndVarManager):
    def __init__(self, connection):
        self.connection = connection

        self.publicLists = {}
        self.personalLists = {}
        self.personalBackup = {}

        # Auto flag
        conf.notify_add("autoCallFlag", self.autoFlagNotify)

    def autoFlagNotify(self, *args):
        self.connection.client.run_command(
            "set autoflag %s" % int(conf.get("autoCallFlag"))
        )
        # print 'notify flag', conf.get('autoCallFlag')
