""" Some Python2/Python3 compatibility support helpers """

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    basestring = str
    cmp = lambda x, y: (x > y) - (x < y)
    memoryview = memoryview
    open = open
    unichr = chr
    unicode = lambda x: x
    raw_input = input

    import builtins
    from html.entities import entitydefs

    from io import StringIO
    from urllib.parse import urlparse
    from configparser import SafeConfigParser
    from queue import Queue, Empty, Full
    from urllib.request import urlopen, url2pathname
    from urllib.parse import urlencode
else:
    basestring = basestring
    cmp = cmp
    memoryview = buffer
    unicode = unicode
    unichr = unichr
    raw_input = raw_input
    
    import __builtin__ as builtins
    from htmlentitydefs import entitydefs
    from cStringIO import StringIO
    from urlparse import urlparse
    from ConfigParser import SafeConfigParser
    from Queue import Queue, Empty, Full
    from urllib import urlopen, urlencode, url2pathname

    from io import open

