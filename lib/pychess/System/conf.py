""" The task of this module is to provide easy saving/loading of configurations
    It also supports gconf like connection, so you get notices when a property
    has changed. """
from __future__ import absolute_import
import sys
import os

from . import conf_configParser as conf_Module
"""Module for using gconf without having to care about types"""


def notify_add(key, func, *args):
    """The signature for func must be self, client, *args, **kwargs"""
    assert isinstance(key, str)
    return conf_Module.notify_add(key, func, args)


def notify_remove(conid):
    conf_Module.notify_remove(conid)


def getStrict(key):
    assert hasKey(key)
    return conf_Module.get(key)


def get(key, alternative):
    if hasKey(key):
        return conf_Module.get(key)
    if callable(alternative):
        alternative = alternative()
    return alternative


def set(key, value):
    conf_Module.set(key, value)


def hasKey(key):
    return conf_Module.hasKey(key)


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
