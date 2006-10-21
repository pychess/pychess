# engines.py takes care of getting name of, and initializing engines

from CECP import CECPEngine

knownEngines = (
    ("gnuchess", CECPEngine),
    ("crafty", CECPEngine),
    ("faile", CECPEngine),
    ("phalanx", CECPEngine),
    ("sjeng", CECPEngine),
)

import os

def _testEngine (engine):
    for dir in os.environ["PATH"].split(":"):
        path = os.path.join(dir, engine)
        if os.path.isfile(path):
            return path
    return False

availableEngines = []
for e,p in knownEngines:
    path = _testEngine(e)
    if path:
        availableEngines.append((p,(path,)))

###################

# Other engines
from PyChess import PyChessEngine
availableEngines.append((PyChessEngine,()))

###################

namesFound = False

from threading import Condition, Lock
diclock = Lock()
namecond = Condition()

engineDic = {}
def _addToDic (key, value):
    diclock.acquire()
    engineDic[key] = value
    if len(engineDic) == len(availableEngines):
        namecond.acquire()
        global namesFound
        namesFound = True
        namecond.notify()
        namecond.release()
    diclock.release()

import thread

def _getName (engine, args):
    en = engine(args, "white")
    en.wait() # Wait for engine to init
    _addToDic((engine,args), repr(en))
    en.__del__()

for engine, args in availableEngines:
    thread.start_new(_getName, (engine,args))

def getName ((engine,args)):
    if namesFound:
        return engineDic[(engine,args)]
    else:
        namecond.acquire()
        while not namesFound:
            namecond.wait()
        return engineDic[(engine,args)]
