import os, atexit
from ast import literal_eval

from pychess.compat import SafeConfigParser
from pychess.System.Log import log

configParser = SafeConfigParser()
from pychess.System.prefix import addUserConfigPrefix

section = "General"
path = addUserConfigPrefix("config")
if os.path.isfile(path):
    configParser.readfp(open(path))
if not configParser.has_section(section):
    configParser.add_section(section)
atexit.register(lambda: configParser.write(open(path,"w")))

idkeyfuncs = {}
conid = 0


def notify_add (key, func, args):
    global conid
    idkeyfuncs[conid] = (key, func, args)
    conid += 1
    return conid

def notify_remove (conid):
    del idkeyfuncs[conid]

def get (key):
    try:
        return configParser.getint(section, key)
    except ValueError:
        pass

    try:
        return configParser.getboolean(section, key)
    except ValueError:
        pass

    try:
        return configParser.getfloat(section, key)
    except ValueError:
        pass

    return configParser.get(section, key)

def set (key, value):
    try:
        configParser.set (section, key, str(value))
    except Exception as e:
        log.error("Unable to save configuration '%s'='%s' because of error: %s %s"%
                (repr(key), repr(value), e.__class__.__name__, ", ".join(str(a) for a in e.args)))
    for key_, func, args in idkeyfuncs.values():
        if key_ == key:
            func (None, *args)

def hasKey (key):
    return configParser.has_option(section, key)
