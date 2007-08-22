section = "General"

import os
from ConfigParser import SafeConfigParser
configParser = SafeConfigParser()

path = os.path.join(os.environ["HOME"], ".pychessconf")
if os.path.isfile(path):
    configParser.readfp(open(path))
else:
    configParser.add_section(section)

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
    for func in (cp.getboolean, cp.getint, cp.getfloat, cp.get):
        try: return func (section, key)
        except: continue
    return 0

def set (key, value):
    configParser.set (section, key, str(value))
    if key in notifiers:
        for key, func in [idkeyfuncs[id] for id in notifiers[key]]:
            func (None)

import atexit
atexit.register(lambda: configParser.write(open(path,"w")))
