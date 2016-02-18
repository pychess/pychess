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
    strip = str.strip

    import builtins
    from html.entities import entitydefs

    from io import StringIO
    from configparser import RawConfigParser, SafeConfigParser
    from queue import Queue, Empty, Full
    from urllib.request import Request, urlopen, url2pathname, pathname2url
    from urllib.parse import urlencode, urlparse, unquote
    from urllib.error import HTTPError, URLError
else:
    basestring = basestring
    cmp = cmp
    memoryview = buffer
    unicode = unicode
    unichr = unichr
    raw_input = raw_input
    strip = unicode.strip
    
    import __builtin__ as builtins
    from htmlentitydefs import entitydefs
    from StringIO import StringIO
    from urlparse import urlparse
    from ConfigParser import RawConfigParser, SafeConfigParser
    from Queue import Queue, Empty, Full
    from urllib import urlencode, url2pathname, pathname2url, unquote
    from urllib2 import Request, urlopen, HTTPError, URLError

    from io import open
