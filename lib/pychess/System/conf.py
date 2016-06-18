""" The task of this module is to provide easy saving/loading of configurations
    It also supports gconf like connection, so you get notices when a property
    has changed. """
from __future__ import absolute_import
import sys
import os
import atexit

from pychess.compat import RawConfigParser
from pychess.System.Log import log
from pychess.System.prefix import addUserConfigPrefix

configParser = RawConfigParser()
section = "General"
path = addUserConfigPrefix("config")
if os.path.isfile(path):
    configParser.readfp(open(path))
if not configParser.has_section(section):
    configParser.add_section(section)
atexit.register(lambda: configParser.write(open(path, "w")))

idkeyfuncs = {}
conid = 0


def notify_add(key, func, *args):
    """The signature for func must be self, client, *args, **kwargs"""
    assert isinstance(key, str)
    global conid
    idkeyfuncs[conid] = (key, func, args)
    conid += 1
    return conid - 1


def notify_remove(conid):
    del idkeyfuncs[conid]


def getStrict(key):
    assert hasKey(key)
    return get(key)


def get(key, alternative=None):
    if hasKey(key):
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
    if callable(alternative):
        alternative = alternative()
    return alternative


def set(key, value):
    try:
        configParser.set(section, key, str(value))
    except Exception as err:
        log.error(
            "Unable to save configuration '%s'='%s' because of error: %s %s" %
            (repr(key), repr(value), err.__class__.__name__, ", ".join(
                str(a) for a in err.args)))
    for key_, func, args in idkeyfuncs.values():
        if key_ == key:
            func(None, *args)


def hasKey(key):
    return configParser.has_option(section, key)


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
    else:
        username = userdata.pw_name
    del getuid, getpwuid
    del sys, os
    del userdata, realname
