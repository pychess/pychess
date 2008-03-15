from threading import Semaphore

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
        
        print >> self.connection.client, "showlist"
        
        # Variables
        self.variablesBackup = {}
        self.ivariablesBackup = {}
        self.variables = {}
        self.ivariables = {}
        self.varLock = Semaphore(0)
        
        self.connection.expect_fromplus (self.onVariables,
                "((?:Interface v|V)ariable settings) of (\w+):",
                "(?:\w*=\w+ *)*$")
        
        print >> self.connection.client, "variables"
        print >> self.connection.client, "ivariables"
        
        self.connection.connect("disconnecting", self.stop)
    
    def isReady (self):
        return self.listLock._Semaphore__value and self.varLock._Semaphore__value
    
    def stop (self, connection):
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
        for key, usedvalue in self.variables.iteritems():
            if usedvalue != self.variablesBackup[key]:
                self.setVariable(key, usedvalue)
        for key, usedvalue in self.ivariables.iteritems():
            if usedvalue != self.ivariablesBackup[key]:
                self.setVariable(key, usedvalue)
    
    # Lists
    
    def onUpdateLists (self, matchlist):
        self.publicLists.clear()
        self.personalLists.clear()
        for line in [m.group(0) for m in matchlist[1:] if m.group(0)]:
            name, _, public_personal = line.split()
            print >> self.connection.client, "showlist %s" % name
            if public_personal == "PUBLIC":
                self.publicLists[name] = set()
            else:
                self.personalLists[name] = set()
    
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
    
    def onUpdateListitems (self, matchlist):
        listName, itemCount = matchlist[0].groups()
        items = set()
        for match in matchlist[1:]:
            items.update(match.group().split())
        if listName in self.publicLists:
            self.publicLists[listName] = items
        else:
            self.personalLists[listName] = items
            if not listName in self.personalBackup:
                self.personalBackup[listName] = items
        # Unlock if people are waiting of the backup
        if not self.listLock._Semaphore__value and \
                len(self.personalLists) == len(self.personalBackup):
            self.listLock.release()
    
    # Variables
    
    def onVariables (self, matchlist):
        type, name = matchlist[0].groups()
        isIvars = "interface" in type.lower()
        for line in [m.group(0) for m in matchlist[1:] if m.group(0)]:
            for kv in line.split():
                k,v = kv.split("=")
                if isIvars:
                    self.ivariables[k] = v
                    if not k in self.ivariablesBackup:
                        self.ivariablesBackup[k] = v
                else:
                    self.variables[k] = v
                    if not k in self.variablesBackup:
                         self.variablesBackup[k] = v
        # Unlock if people are waiting of the backup and we've got the normal
        # variable backup set. The interface variables automatically reset
        if not self.varLock._Semaphore__value and self.variablesBackup:
            self.varLock.release()
    
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
        print >> self.connection.client, "+%s %s" % (listName, value)
        self.lists[listName].append(value)
    
    def removeFromList (self, listName, value):
        self.listLock.acquire()
        self.listLock.release()
        print >> self.connection.client, "-%s %s" % (listName, value)
        self.lists[listName].append(value)
    
    
    def getVariable (self, name):
        self.varLock.acquire()
        self.varLock.release()
        if name in self.variables:
            return self.variables[name]
        return self.ivariables[name]
    
    def setVariable (self, name, value):
        self.varLock.acquire()
        self.varLock.release()
        if name in self.variables:
            print >> self.connection.client, "set %s %s" % (name, value)
            self.variables[name] = value
        else:
            print >> self.connection.client, "iset %s %s" % (name, value)
            self.ivariables[name] = value
