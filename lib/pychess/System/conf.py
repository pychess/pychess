""" The task of this module is to provide easy saving/loading of configurations
    It also supports gconf like connection, so you get notices when a property
    has changed. """
import sys
import os
import atexit
from configparser import RawConfigParser

from pychess.System.Log import log
from pychess.System.prefix import addUserConfigPrefix

section = "General"
configParser = RawConfigParser(default_section=section)

for sect in ("FICS", "ICC"):
    if not configParser.has_section(sect):
        configParser.add_section(sect)

path = addUserConfigPrefix("config")
if os.path.isfile(path):
    configParser.readfp(open(path))
atexit.register(lambda: configParser.write(open(path, "w")))

idkeyfuncs = {}
conid = 0


def notify_add(key, func, *args, section=section):
    """The signature for func must be self, client, *args, **kwargs"""
    assert isinstance(key, str)
    global conid
    idkeyfuncs[conid] = (key, func, args, section)
    conid += 1
    return conid - 1


def notify_remove(conid):
    del idkeyfuncs[conid]


def get(key, fallback=None, section=section):
    try:
        return configParser.getint(section, key, fallback=fallback)
    except ValueError:
        pass

    try:
        return configParser.getboolean(section, key, fallback=fallback)
    except ValueError:
        pass

    try:
        return configParser.getfloat(section, key, fallback=fallback)
    except ValueError:
        pass

    return configParser.get(section, key, fallback=fallback)


def set(key, value, section=section):
    try:
        configParser.set(section, key, str(value))
        configParser.write(open(path, "w"))
    except Exception as err:
        log.error(
            "Unable to save configuration '%s'='%s' because of error: %s %s" %
            (repr(key), repr(value), err.__class__.__name__, ", ".join(
                str(a) for a in err.args)))
    for key_, func, args, section_ in idkeyfuncs.values():
        if key_ == key and section_ == section:
            func(None, *args)


def hasKey(key, section=section):
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
