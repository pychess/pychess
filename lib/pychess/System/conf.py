""" The task of this module is to provide easy saving/loading of configurations
    It also supports gconf like connection, so you get notices when a property
    has changed. """

# gconf's notify all seams to be broken
#try:
#    import gconf
#    import conf_gconf as confmodule
#except:
import conf_configParser as confmodule

"""Module for using gconf without having to care about types"""

def notify_add (key, func, *args):
    return confmodule.notify_add(key, func, args)

def notify_remove (conid):
    confmodule.notify_remove(conid)

def getStrict (key):
    assert hasKey (key)
    return confmodule.get(key)

def get (key, alternative):
    if hasKey (key):
        return confmodule.get(key)
    if callable(alternative):
        alternative = alternative()
    return alternative

def set (key, value):
    confmodule.set(key, value)

def hasKey (key):
    return confmodule.hasKey(key)

import sys, os
if sys.platform == "win32":
    username = os.environ["USERNAME"]
    del sys, os
else:
    from os import getuid
    from pwd import getpwuid
    userdata = getpwuid(getuid())
    realname = userdata.pw_gecos.split(",")[0]
    if realname:
        username = realname
    else: username = userdata.pw_name
    del getuid, getpwuid
    del sys, os
    del userdata, realname
