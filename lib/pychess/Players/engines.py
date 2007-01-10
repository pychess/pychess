# engines.py takes care of getting name of, and initializing engines

from CECP import CECPEngine

# TODO: Use xml, like glchess.
# Will be needed when more info is needed for the preferences:
# * location
# * "uses to send feature" (should let us start earlier)

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
# availableEngines is a list of [(EngineClass, (extra, arguments ...)), ...]
# the CECPEngine class takes one argument - the path of the executable

for e,p in knownEngines:
    path = _testEngine(e)
    if path:
        availableEngines.append((p,(path,)))

###################

# PyChess Engine

import os, imp

if "PYTHONPATH" in os.environ:
    path = os.path.abspath(os.environ["PYTHONPATH"])
    path = os.path.join(path, "pychess/Players/PyChess.py")
else:
    path = os.path.dirname(imp.find_module("os")[1])
    path = os.path.join(path, "site-packages/pychess/Players/PyChess.py")

path = "env python "+path
availableEngines.append( (CECPEngine, (path,)) )

from ProtocolEngine import ProtocolEngine
from UCIProtocol import UCIProtocol
path = "/home/thomas/Programmering/python/skak/ShredderClassic/engines/ShredderClassicLinux"
availableEngines.append( (ProtocolEngine, (UCIProtocol, path)) )

path = "/home/thomas/Programmering/python/skak/fruit_21_linux/fruit_21_static"
availableEngines.append( (ProtocolEngine, (UCIProtocol, path)) )

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
    gotthose = [os.path.split(k[1][-1])[1] for k in engineDic.keys()]
    needthose = [os.path.split(a[-1])[1] for e,a in availableEngines if not (e,a) in engineDic]
    print "got %d engines. %s; Needs %s" % (
        len(engineDic), " ".join(gotthose), " ".join(needthose))
    diclock.release()

import thread
from pychess.Utils.const import *

def _getInfo (engine, args):
    en = engine(args, WHITE)
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
