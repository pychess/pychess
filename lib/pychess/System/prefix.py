"""
This module provides some basic functions for accessing pychess datefiles in
system or user space
"""

import os
import sys

################################################################################
# Locate files in system space                                                 #
################################################################################

# Test if we are installed on the system, frozen or are being run from tar/svn
if getattr(sys, "frozen", False):
    _prefix = os.path.join(os.path.dirname(sys.executable), "share", "pychess")
    _installed = True
else:
    home_local = os.path.expanduser("~") + "/.local"
    if sys.prefix in __file__:
        for sub in (
            "share",
            "games",
            "share/games",
            "local/share",
            "local/games",
            "local/share/games",
        ):
            _prefix = os.path.join(sys.prefix, sub, "pychess")
            if os.path.isdir(os.path.join(_prefix, "pieces")):
                _installed = True
                break
        else:
            raise Exception("can't find the pychess data directory")
    elif home_local in __file__:
        _prefix = os.path.join(home_local, "share", "pychess")
        if os.path.isdir(os.path.join(_prefix, "pieces")):
            _installed = True
        else:
            raise Exception("can't find the pychess data directory")
    else:
        _prefix = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        _installed = False


def addDataPrefix(subpath):
    return os.path.abspath(os.path.join(_prefix, subpath))


def getDataPrefix():
    return _prefix


def isInstalled():
    return _installed


################################################################################
# Locate files in user space                                                   #
################################################################################


def __get_user_dir(xdg_env_var, fallback_dir_path):
    return os.environ.get(
        xdg_env_var, os.path.join(os.path.expanduser("~"), fallback_dir_path)
    )


def get_user_data_dir():
    return __get_user_dir("XDG_DATA_HOME", ".local/share")


def get_user_config_dir():
    return __get_user_dir("XDG_CONFIG_HOME", ".config")


def get_user_cache_dir():
    return __get_user_dir("XDG_CACHE_HOME", ".cache")


pychess = "pychess"


def getUserDataPrefix():
    return os.path.join(get_user_data_dir(), pychess)


def addUserDataPrefix(subpath):
    return os.path.join(getUserDataPrefix(), subpath)


def getEngineDataPrefix():
    return os.path.join(getUserDataPrefix(), "engines")


def addEngineDataPrefix(subpath):
    return os.path.join(getEngineDataPrefix(), subpath)


def getUserConfigPrefix():
    return os.path.join(get_user_config_dir(), pychess)


def addUserConfigPrefix(subpath):
    return os.path.join(getUserConfigPrefix(), subpath)


def getUserCachePrefix():
    return os.path.join(get_user_cache_dir(), pychess)


def addUserCachePrefix(subpath):
    return os.path.join(getUserCachePrefix(), subpath)


for directory in (
    getUserDataPrefix(),
    getEngineDataPrefix(),
    getUserConfigPrefix(),
    getUserCachePrefix(),
):
    if not os.path.isdir(directory):
        os.makedirs(directory, mode=0o700)
