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
atexit.register(lambda: configParser.write(open(path,"w")))

notifiers = {}
idkeyfuncs = {}
conid = 0

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
    cp = configParser
    for func in (cp.getboolean, cp.getint, cp.getfloat):
        try: return func (section, key)
        except ValueError: continue
    return cp.get(section, key)

def set (key, value):
    try:
        configParser.set (section, key, str(value))
    except Exception, e:
        log.error("Unable to save configuration '%s'='%s' because of error: %s %s"%
                (repr(key), repr(value), e.__class__.__name__, ", ".join(str(a) for a in e.args)))
    if key in notifiers:
        for key, func in [idkeyfuncs[id] for id in notifiers[key]]:
            func (None)

def hasKey (key):
    return configParser.has_option(section, key)
