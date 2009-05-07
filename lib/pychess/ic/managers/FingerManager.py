
from threading import RLock
from gobject import *
from time import time
from pychess.Utils.const import *
from pychess.Utils.Rating import Rating
from pychess.System.Log import log
import re

types = "(?:blitz|standard|lightning|wild|bughouse|crazyhouse|suicide|losers|atomic)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\-]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|TM|SR|TD|SR|CA|C|U|D|B|T|\*)"
titles = "((?:\(%s\))+)?" % titleslist
names = "(\w+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
# FIXME: Needs support for day, hour, min, sec
times = "[, ]*".join("(?:(\d+) %s)?" % s for s in ("days", "hrs", "mins", "secs"))
# "73 days, 5 hrs, 55 mins"
# ('73', '5', '55', None)

type2Type = {
    "blitz": TYPE_BLITZ,
    "standard": TYPE_STANDARD,
    "lightning": TYPE_LIGHTNING,
    "wild": TYPE_WILD,
    "bughouse": TYPE_BUGHOUSE,
    "crazyhouse": TYPE_CRAZYHOUSE,
    "suicide": TYPE_SUICIDE,
    "losers": TYPE_LOSERS,
    "atomic": TYPE_ATOMIC
}

class FingerObject:
    
    def __init__ (self, name = ""):
        self.__fingerTime = time()
        
        self.__name = name
        self.__status = None
        self.__upTime = 0
        self.__idleTime = 0
        self.__busyMessage = ""
        self.__lastSeen = 0 
        self.__totalTimeOnline = 0
        self.__created = 0 # Since field from % of life online
        self.__email = ""
        self.__adminLevel = ""
        self.__timeseal = False
        self.__notes = [""]*10
        self.__gameno = ""
        self.__color = WHITE
        self.__opponent = ""
        self.__silence = False
        self.__titles = None
       
        self.__rating = {}
    
    def getName (self):
        """ Returns the name of the user, without any title sufixes """
        return self.__name
    
    def getStatus (self):
        """ Returns the current user-status as a STATUS constant """
        return self.__status
    
    def getUpTime(self):
        """ Returns the when the user logged on
            Not set when status == STATUS_OFFLINE """
        return self.__upTime + time() - self.__fingerTime

    def getIdleTime(self):
        """ Returns the when the last time the user did something active
            Not set when status == STATUS_OFFLINE """
        return self.__idleTime + time() - self.__fingerTime

    def getBusyMessage(self):
        """ Returns the userset idle message
            This is set when status == STATUS_BUSY or sometimes when status ==
            STATUS_PLAYING """ 
        return self.__busyMessage

    def getLastSeen(self):
        """ Returns when the user logged off
            This is only set when status == STATUS_OFFLINE
            This is not set, if the user has never logged on """
        return self.__lastSeen

    def getTotalTimeOnline(self):
        """ Returns how many seconds the user has been on FICS since the account
            was created.
            This is not set, if the user has never logged on """
        return self.__totalTimeOnline + time() - self.__fingerTime
    
    def getCreated(self):
        """ Returns when the account was created """
        return self.__created
    
    def getEmail(self):
        """ Returns the email adress of the user.
            This will probably only be set for the logged in user """
        return self.__email

    def getAdminLevel(self):
        """ Returns the admin level as a string
            Only set for admins. """
        return self.__adminLevel

    def getTimeseal(self):
        """ Returns True if the user is using timeseal for fics connection """
        return self.__timeseal
    
    def getNotes(self):
        """ Returns a list of the ten finger notes """
        return self.__notes
    
    def getGameno(self):
        """ Returns the gameno of the game in which user is currently playing
            This is only set when status == STATUS_PLAYING """
        return self.__gameno
    
    def getColor(self):
        """ If status == STATUS_PLAYING getColor returns the color witch the
            player has got in the game.
            Otherwise always WHITE is returned """
        return self.__color
    
    def getOpponent(self):
        """ Returns the opponent of the user in his current game
            This is only set when status == STATUS_PLAYING """
        return self.__opponent

    def getSilence(self):
        """ Return True if the user is playing in silence
            This is only set when status == STATUS_PLAYING """
        return self.__silence
    
    def getRating(self, type=None):
        if type == None:
            return self.__rating
        return self.__rating[type]
    
    def getTitles(self):
        return self.__titles    
    
    def setName(self, value):
        self.__name = value
    
    def setStatus(self, value):
        self.__status = value

    def setUpTime(self, value):
        """ Use relative seconds """
        self.__upTime = value

    def setIdleTime(self, value):
        """ Use relative seconds """
        self.__idleTime = value

    def setBusyMessage(self, value):
        """ Use relative seconds """
        self.__busyMessage = value

    def setLastSeen(self, value):
        """ Use relative seconds """
        self.__lastSeen = value

    def setTotalTimeOnline(self, value):
        """ Use relative seconds """
        self.__totalTimeOnline = value

    def setCreated(self, value):
        """ Use relative seconds """
        self.__created = value

    def getStatus(self):
        return self.__status
    
    def setEmail(self, value):
        self.__email = value

    def setAdminLevel(self, value):
        self.__adminLevel = value

    def setTimeseal(self, value):
        self.__timeseal = value
    
    def setNote(self, index, note):
        self.__notes[index] = note
    
    def setGameno(self, value):
        self.__gameno = value
    
    def setColor(self, value):
        self.__color = value
    
    def setOpponent(self, value):
        self.__opponent = value

    def setSilence(self, value):
        self.__silence = value
    
    def setRating(self, type, rating):
        self.__rating[type] = rating

    def setTitles(self, titles):
        self.__titles = titles

class FingerManager (GObject):
    
    __gsignals__ = {
        'fingeringFinished' : (SIGNAL_RUN_FIRST, None, (object,)),
        'ratingAdjusted' : (SIGNAL_RUN_FIRST, None, (str, str)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        fingerLines = (
            "(?P<never>%s has never connected\.)" % names,
            "Last disconnected: (?P<last>.+)",
            "On for: (?P<uptime>.+?) +Idle: (?P<idletime>.+)",
            "%s is in (?P<silence>silence) mode\." % names,
            "\(playing game (?P<gameno>\d+): (?P<p1>\S+?)%s vs. (?P<p2>\S+?)%s\)" % (titles,titles),
            "\(%s (?P<busymessage>.+?)\)" % names,
            "%s has not played any rated games\." % names,
            "rating +RD +win +loss +draw +total +best",
            "(?P<gametype>%s) +(?P<ratings>.+)" % types,
            "Email *: (?P<email>.+)",
            "Total time online: (?P<tto>.+)",
            "% of life online:  [\d\.]+  \(since (?P<created>.+?)\)", 
            "Timeseal [ \\d] : (?P<timeseal>Off|On)",
            "Admin Level: (?P<adminlevel>.+)",
            "(?P<noteno>\d+): *(?P<note>.*)",
            "$"
        )
        
        self.connection.expect_fromplus (self.onFinger,
                "Finger of %s:" % names,
                "$|".join(fingerLines))
                
        self.connection.lvm.setVariable("nowrap", True)
        
        # We don't use this. Rather we use BoardManagers "gameEnded", after
        # which we do a refinger. This is to ensure not only rating, but also
        # wins/looses/draws are updated
        #self.connection.expect(self.onRatingAdjust,
        #        "%s rating adjustment: (\d+) --> (\d+)" % types
        # Notice if you uncomment this: The expression has to be compiled with
        # re.IGNORECASE, or the first letter of 'type' must be capital
    
        
    
    def parseDate (self, date):
        # Tue Mar 11, 10:56 PDT 2008
        return 1
    
    def parseShortDate (self, date):
        # 24-Oct-2007
        return 1
    
    def parseTime (self, time):
        # 3 days, 2 hrs, 53 mins
        return 1
    
    def onFinger (self, matchlist):
        finger = FingerObject()
        name = matchlist[0].groups()[0]
        finger.setName(name)
        if matchlist[0].groups()[1]:
            titles = re.findall(titleslist, matchlist[0].groups()[1])
            finger.setTitles(titles)
        for match in matchlist[1:]:
            if not match.group():
                continue
            groupdict = match.groupdict()
            if groupdict["never"] != None:
                finger.setStatus(IC_STATUS_OFFLINE)
            elif groupdict["last"] != None:
                finger.setStatus(IC_STATUS_OFFLINE)
                finger.setLastSeen(self.parseDate(groupdict["last"]))
            elif groupdict["uptime"] != None:
                finger.setStatus(IC_STATUS_ACTIVE)
                finger.setUpTime(self.parseTime(groupdict["uptime"]))
                finger.setIdleTime(self.parseTime(groupdict["idletime"]))
            elif groupdict["silence"] != None:
                finger.setSilence(True)
            elif groupdict["gameno"] != None:
                finger.setStatus(IC_STATUS_PLAYING)
                finger.setGameno(groupdict["gameno"])
                if groupdict["p1"].lower() == self.connection.getUsername().lower():
                    finger.setColor(WHITE)
                    finger.setOpponent(groupdict["p2"])
                else:
                    finger.setColor(BLACK)
                    finger.setOpponent(groupdict["p1"])
            elif groupdict["busymessage"] != None:
                finger.setStatus(IC_STATUS_BUSY)
                finger.setBusyMessage(groupdict["busymessage"])
            elif groupdict["gametype"] != None:
                type = type2Type[groupdict["gametype"].lower()]
                ratings = groupdict["ratings"].split()
                del ratings[5] # We don't need the totals field
                if len(ratings) == 5:
                    rating = Rating(type, *map(float,ratings))
                else:
                    bestTime = self.parseShortDate(ratings[6][1:-1])
                    args = map(float,ratings[:6]) + [bestTime]
                    rating = Rating(type, *args)
                finger.setRating(type, rating)
            elif groupdict["email"] != None:
                finger.setEmail(groupdict["email"])
            elif groupdict["tto"] != None:
                finger.setTotalTimeOnline(self.parseTime(groupdict["tto"]))
            elif groupdict["created"] != None:
                finger.setTotalTimeOnline(self.parseDate(groupdict["created"]))
            elif groupdict["timeseal"] != None:
                finger.setTimeseal(groupdict["timeseal"] == "On")
            elif groupdict["adminlevel"] != None:
                finger.setAdminLevel(groupdict["adminlevel"])
            elif groupdict["noteno"] != None:
                finger.setNote(int(groupdict["noteno"])-1, groupdict["note"])
            else:
                log.debug("Ignored fingerline: %s" % repr(match.group()))
        
        self.emit ("fingeringFinished", finger)
    
    def onRatingAdjust (self, match):
        # Notice: This is only recived for us, not for other persons we finger
        type, old, new = match.groups()
        self.emit("ratingAdjusted", type, new)
    
    def finger (self, user):
        print >> self.connection.client, "finger %s /sbl" % user
    
    def setFingerNote (self, note, message):
        assert 1 <= note <= 10
        print >> self.connection.client, "set %d %s" % (note, message)
    
    def setBusyMessage (self, message):
        """ Like set busy is really busy right now. """
        self.connection.lvm.setVariable("busy", message)
