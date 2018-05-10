from pychess.ic import BLKCMD_SHOWLIST
from pychess.System import conf


class ListAndVarManager:
    def __init__(self, connection):
        self.connection = connection

        # Lists
        self.publicLists = {}
        self.personalLists = {}
        self.personalBackup = {}

        if self.connection.USCN:
            self.connection.expect_line(self.onUpdateList,
                                        "(?:\w+\s+is (?:PUBLIC|PERSONAL))|$")
        else:
            self.connection.expect_fromplus(
                self.onUpdateLists, "Lists:",
                "(?:\w+\s+is (?:PUBLIC|PERSONAL))|$")

        self.connection.expect_line(self.onUpdateEmptyListitems,
                                    "-- (\w+) list: 0 \w+ --")
        self.connection.expect_fromplus(self.onUpdateListitems,
                                        "-- (\w+) list: ([1-9]\d*) \w+ --",
                                        "(?:\w+ *)+$")

        self.connection.client.run_command("showlist")

        # Auto flag
        conf.notify_add('autoCallFlag', self.autoFlagNotify)

    def onUpdateLists(self, matchlist):
        self.publicLists.clear()
        self.personalLists.clear()
        for line in [m.group(0) for m in matchlist[1:] if m.group(0)]:
            name, _, public_personal = line.split()
            self.connection.client.run_command("showlist %s" % name)
            if public_personal == "PUBLIC":
                self.publicLists[name] = set()
            else:
                self.personalLists[name] = set()

    onUpdateLists.BLKCMD = BLKCMD_SHOWLIST

    def onUpdateList(self, match):
        name, _, public_personal = match.group(0).split()
        self.connection.client.run_command("showlist %s" % name)
        if public_personal == "PUBLIC":
            self.publicLists[name] = set()
        else:
            self.personalLists[name] = set()

    def onUpdateEmptyListitems(self, match):
        list_name = match.groups()[0]
        if list_name in self.publicLists:
            self.publicLists[list_name] = set()
        else:
            self.personalLists[list_name] = set()
            if list_name not in self.personalBackup:
                self.personalBackup[list_name] = set()

    onUpdateEmptyListitems.BLKCMD = BLKCMD_SHOWLIST

    def onUpdateListitems(self, matchlist):
        list_name, itemCount = matchlist[0].groups()
        items = set()
        for match in matchlist[1:]:
            items.update(match.group().split())
        if list_name in self.publicLists:
            self.publicLists[list_name] = items
        else:
            self.personalLists[list_name] = items
            self.personalBackup[list_name] = items

    onUpdateListitems.BLKCMD = BLKCMD_SHOWLIST

    def autoFlagNotify(self, *args):
        self.connection.client.run_command(
            "set autoflag %s" % int(conf.get('autoCallFlag')))
        # print 'notify flag', conf.get('autoCallFlag')

    def getList(self, list_name):
        if list_name in self.publicLists:
            return self.publicLists(list_name)
        elif list_name in self.personalLists:
            return self.personalLists[list_name]
        else:
            return []

    def addToList(self, list_name, value):
        self.connection.client.run_command("+%s %s" % (list_name, value))

    def removeFromList(self, list_name, value):
        self.connection.client.run_command("-%s %s" % (list_name, value))
