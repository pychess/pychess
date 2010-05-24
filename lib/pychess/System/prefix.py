"""
This module provides some basic functions for accessing pychess datefiles in
system or user space
"""

import os
import sys
from os import makedirs
from os.path import isdir, join, dirname, abspath

################################################################################
# Locate files in system space                                                 #
################################################################################

# Test if we are installed on the system, or are being run from tar/svn
if "site-packages" in __file__ or "dist-packages" in __file__:
    for sub in ("share", "games", "share/games",
                "local/share", "local/games", "local/share/games"):
        _prefix = join (sys.prefix, sub, "pychess")
        if isdir(_prefix):
            _installed = True
            break
    else:
        raise Exception("can't find the pychess data directory")
else:
    _prefix = abspath (join (dirname (__file__), "../../.."))
    _installed = False

def addDataPrefix (subpath):
    return abspath (join (_prefix, subpath))

def getDataPrefix ():
    return _prefix

def isInstalled ():
    return _installed

################################################################################
# Locate files in user space                                                   #
################################################################################

# The glib.get_user_*_dir() XDG functions below require pygobject >= 2.18
try:
    from glib import get_user_data_dir, get_user_config_dir, get_user_cache_dir
except ImportError:
    def __get_user_dir (xdg_env_var, fallback_dir_path):
        try:
            directory = os.environ[xdg_env_var]
        except KeyError:
            directory = join(os.environ["HOME"], fallback_dir_path)
        return directory
    def get_user_data_dir ():
        return __get_user_dir("XDG_DATA_HOME", ".local/share")
    def get_user_config_dir ():
        return __get_user_dir("XDG_CONFIG_HOME", ".config")
    def get_user_cache_dir ():
        return __get_user_dir("XDG_CACHE_HOME", ".cache")

pychess = "pychess"
def getUserDataPrefix ():
    return join(get_user_data_dir(), pychess)
def addUserDataPrefix (subpath):
    return join(getUserDataPrefix(), subpath)
def getUserConfigPrefix ():
    return join(get_user_config_dir(), pychess)
def addUserConfigPrefix (subpath):
    return join(getUserConfigPrefix(), subpath)
def getUserCachePrefix ():
    return join(get_user_cache_dir(), pychess)
def addUserCachePrefix (subpath):
    return join(getUserCachePrefix(), subpath)

for directory in (getUserDataPrefix(), getUserConfigPrefix(), getUserCachePrefix()):
    if not isdir(directory):
        makedirs(directory, mode=0700)
