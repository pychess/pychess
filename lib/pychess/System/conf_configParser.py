import os, atexit
from pychess.System.Log import log
from ConfigParser import SafeConfigParser
configParser = SafeConfigParser()

section = "General"
path = os.path.join(os.environ["HOME"], ".pychessconf")
if os.path.isfile(path):
    configParser.readfp(open(path))
if not configParser.has_section(section):
    configParser.add_section(section)
if not configParser.has_section(section+"_Types"):
    configParser.add_section(section+"_Types")
atexit.register(lambda: configParser.write(open(path,"w")))

notifiers = {}
idkeyfuncs = {}
conid = 0

typeEncode = {
    str: repr(str),
    unicode: repr(unicode),
    int: repr(int),
    float: repr(float),
    bool: repr(bool)
}
typeDecode = {
    repr(str): configParser.get,
    repr(unicode): configParser.get,
    repr(int): configParser.getint,
    repr(float): configParser.getfloat,
    repr(bool): configParser.getboolean,
}

def notify_add (key, func):
    global conid
    if key in notifiers:
        notifiers[key].append(conid)
    else: notifiers[key] = [conid]
    idkeyfuncs[conid] = (key, func)
    conid += 1

def notify_remove (conid):
    key = idkeyfuncs[conid][0]
    del notifiers[key][conid]
    del idkeyfuncs[conid]

def get (key):
    decoder = typeDecode[configParser.get(section+"_Types", key)]
    return decoder(section, key)

def set (key, value):
    try:
        configParser.set (section, key, str(value))
        configParser.set (section+"_Types", key, typeEncode[type(value)])
    except Exception, e:
        log.error("Unable to save configuration '%s'='%s' because of error: %s %s"%
                (repr(key), repr(value), e.__class__.__name__, ", ".join(str(a) for a in e.args)))
    if key in notifiers:
        for key, func in [idkeyfuncs[id] for id in notifiers[key]]:
            func (None)

def hasKey (key):
    return configParser.has_option(section, key) and \
           configParser.has_option(section+"_Types", key)
