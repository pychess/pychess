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

infoFound = False

from threading import Condition, Lock
diclock = Lock()
infocond = Condition()

engineDic = {}
def _addToDic (key, value):
    diclock.acquire()
    engineDic[key] = value
    if len(engineDic) == len(availableEngines):
        infocond.acquire()
        global infoFound
        infoFound = True
        infocond.notify()
        infocond.release()
    diclock.release()

import thread

def _getInfo (engine, args):
    en = engine(args, "white")
    info = {"name":repr(en), "canAnalyze":en.canAnalyze()}
    _addToDic((engine,args), info)
    en.__del__()

for engine, args in availableEngines:
    thread.start_new(_getInfo, (engine,args))

def getInfo ((engine,args)):
    if infoFound:
        return engineDic[(engine,args)]
    else:
        infocond.acquire()
        while not infoFound:
            infocond.wait()
        return engineDic[(engine,args)]
