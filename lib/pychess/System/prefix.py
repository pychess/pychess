"""
This module provides some basic functions for accessing pychess datefiles in
system or user space
"""

import os
from os import mkdir
from os.path import isdir, join, dirname, abspath

################################################################################
# Locate files in system space                                                 #
################################################################################

prefixes = ("/usr/share", "/usr/local/share", "/usr/share/locale",
    "/usr/share/games", "/usr/local/share/games")

# Test if we are installed on the system, or are being run from tar/svn
if "site-packages" in __file__:
    for prefix in prefixes:
        if isdir (join (prefix, "pychess")):
            _prefix = join (prefix, "pychess")
            _installed = True
            break
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

pychessdir = join(os.environ["HOME"], ".pychess")
if not isdir(pychessdir):
    mkdir(pychessdir)

def addHomePrefix (subpath):
    return join(pychessdir, subpath)

def getHomePrefix ():
    return pychessdir
