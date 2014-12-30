import os, atexit
from pychess.System.Log import log
from pychess.Main import PY2, PY3

if PY3:
    from configparser import SafeConfigParser
else:
    from ConfigParser import SafeConfigParser

configParser = SafeConfigParser()
from pychess.System.prefix import addUserConfigPrefix

section = "General"
path = addUserConfigPrefix("config")
if os.path.isfile(path):
    configParser.readfp(open(path))
if not configParser.has_section(section):
    configParser.add_section(section)
if not configParser.has_section(section+"_Types"):
    configParser.add_section(section+"_Types")
atexit.register(lambda: configParser.write(open(path,"w")))

idkeyfuncs = {}
conid = 0

typeEncode = {
    str: repr(str),
    int: repr(int),
    float: repr(float),
    bool: repr(bool)
}
if PY2:
    typeEncode[unicode] = repr(unicode)

typeDecode = {
    repr(str): configParser.get,
    repr(int): configParser.getint,
    repr(float): configParser.getfloat,
    repr(bool): configParser.getboolean,
}
if PY2:
    typeDecode[repr(unicode)] = configParser.get

def notify_add (key, func, args):
    global conid
    idkeyfuncs[conid] = (key, func, args)
    conid += 1
    return conid

def notify_remove (conid):
    del idkeyfuncs[conid]

def get (key):
    decoder = typeDecode[configParser.get(section+"_Types", key)]
    return decoder(section, key)

def set (key, value):
    try:
        configParser.set (section, key, str(value))
        configParser.set (section+"_Types", key, typeEncode[type(value)])
    except Exception as e:
        log.error("Unable to save configuration '%s'='%s' because of error: %s %s"%
                (repr(key), repr(value), e.__class__.__name__, ", ".join(str(a) for a in e.args)))
    for key_, func, args in idkeyfuncs.values():
        if key_ == key:
            func (None, *args)

def hasKey (key):
    return configParser.has_option(section, key) and \
           configParser.has_option(section+"_Types", key)
