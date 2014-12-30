import atexit
from threading import Semaphore


from pychess.ic import BLKCMD_SHOWLIST, BLKCMD_VARIABLES, BLKCMD_IVARIABLES
from pychess.System import conf


class ListAndVarManager:
    def __init__ (self, connection):
        self.connection = connection
        
        # Lists
        self.publicLists = {}
        self.personalLists = {}
        self.personalBackup = {}
        self.listLock = Semaphore(0)
        
        self.connection.expect_fromplus (self.onUpdateLists,
                "Lists:",
                "(?:\w+\s+is (?:PUBLIC|PERSONAL))|$")
        
        self.connection.expect_line (self.onUpdateEmptyListitems,
                "-- (\w+) list: 0 \w+ --")
        self.connection.expect_fromplus (self.onUpdateListitems,
                "-- (\w+) list: ([1-9]\d*) \w+ --",
                "(?:\w+ *)+$")
        
        self.connection.client.run_command("showlist")
        
        # Variables
        self.variablesBackup = {}
        self.variables = {}
        self.ivariables = {}
        self.varLock = Semaphore(0)
        
        self.connection.expect_fromplus (self.onIVariables,
                "(Interface variable settings of \w+):",
                "(?:\w+=(?:\w+|\?) *)*$")

        self.connection.expect_fromplus (self.onVariables,
                "(Variable settings of \w+):",
                "(?:\w+=(?:\w+|\?) *)*$")
        
        # The order of next two is important to FatICS !
        self.connection.client.run_command("ivariables")
        self.connection.client.run_command("variables")
        
        # Auto flag
        conf.notify_add('autoCallFlag', self.autoFlagNotify)
        
        atexit.register(self.stop)

    def isReady (self):
        # FatICS showlist output is not well formed yet
        if self.connection.FatICS:
            return self.varLock._Semaphore__value
        else:
            return self.listLock._Semaphore__value and self.varLock._Semaphore__value
    
    def stop (self):
        if not self.isReady():
            return

        # Restore personal lists
        for listName in self.personalLists.keys():
            backup = self.personalBackup[listName]
            inuse = self.personalLists[listName]
            # Remove which are in use but not in backup
            for item in inuse-backup:
                self.removeFromList(listName, item)
            # Add which are in backup but not in use:
            for item in backup-inuse:
                self.addToList(listName, item)
        
        # Restore variables
        for key, usedvalue in self.variables.items():
            if key in self.variablesBackup and usedvalue != self.variablesBackup[key]:
                self.setVariable(key, self.variablesBackup[key])
    
    # Lists
    
    def onUpdateLists (self, matchlist):
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
    
    def onUpdateEmptyListitems (self, match):
        listName = match.groups()[0]
        if listName in self.publicLists:
            self.publicLists[listName] = set()
        else:
            self.personalLists[listName] = set()
            if not listName in self.personalBackup:
                self.personalBackup[listName] = set()
        # Unlock if people are waiting of the backup
        if not self.listLock._Semaphore__value and \
                len(self.personalLists) == len(self.personalBackup):
            self.listLock.release()
    onUpdateEmptyListitems.BLKCMD = BLKCMD_SHOWLIST
    
    def onUpdateListitems (self, matchlist):
        listName, itemCount = matchlist[0].groups()
        items = set()
        for match in matchlist[1:]:
            items.update(match.group().split())
        if listName in self.publicLists:
            self.publicLists[listName] = items
        else:
            self.personalLists[listName] = items
            self.personalBackup[listName] = items
        # Unlock if people are waiting of the backup
        if not self.listLock._Semaphore__value and \
                len(self.personalLists) == len(self.personalBackup):
            self.listLock.release()
    onUpdateListitems.BLKCMD = BLKCMD_SHOWLIST

    # Interface variables

    def onIVariables (self, matchlist):
        name = matchlist[0]
        for line in [m.group(0) for m in matchlist[1:] if m.group(0)]:
            for kv in line.split():
                k,v = kv.split("=")
                self.ivariables[k] = v
    onIVariables.BLKCMD = BLKCMD_IVARIABLES
    
    # Variables
    
    def onVariables (self, matchlist):
        name = matchlist[0]
        for line in [m.group(0) for m in matchlist[1:] if m.group(0)]:
            for kv in line.split():
                k,v = kv.split("=")
                self.variables[k] = v
                if k not in self.variablesBackup:
                    self.variablesBackup[k] = v
        # Unlock if people are waiting of the backup and we've got the normal
        # variable backup set. The interface variables automatically reset
        if not self.varLock._Semaphore__value and self.variablesBackup:
            self.varLock.release()
    onVariables.BLKCMD = BLKCMD_VARIABLES
    
    def autoFlagNotify(self, *args):
        self.setVariable('autoflag', int(conf.get('autoCallFlag',False)))
        #print 'notify flag', conf.get('autoCallFlag',False)
    
    # User methods
    
    def getList (self, listName):
        self.listLock.acquire()
        self.listLock.release()
        if listName in self.publicLists:
            return self.publicLists(listName)
        return self.personalLists[listName]
    
    def addToList (self, listName, value):
        self.listLock.acquire()
        self.listLock.release()
        self.connection.client.run_command("+%s %s" % (listName, value))
        #self.lists[listName].append(value)
    
    def removeFromList (self, listName, value):
        self.listLock.acquire()
        self.listLock.release()
        self.connection.client.run_command("-%s %s" % (listName, value))
        #self.lists[listName].append(value)
    
    
    def getVariable (self, name):
        self.varLock.acquire()
        self.varLock.release()
        if name in self.variables:
            return self.variables[name]
        return self.ivariables[name]
    
    def setVariable (self, name, value):
        self.varLock.acquire()
        self.varLock.release()
        if name in self.ivariables:
            self.connection.client.run_command("iset %s %s" % (name, value))
            self.ivariables[name] = value
        else:
            self.connection.client.run_command("set %s %s" % (name, value))
            self.variables[name] = value
