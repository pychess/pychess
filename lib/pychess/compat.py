""" Some Python2/Python3 compatibility support helpers """

import sys

basestring = str
cmp = lambda x, y: (x > y) - (x < y)
memoryview = memoryview
open = open
unichr = chr
unicode = lambda x: x
raw_input = input
filter = filter
strip = str.strip

import builtins
from html.entities import entitydefs

from io import StringIO
from configparser import RawConfigParser, SafeConfigParser
from queue import Queue, Empty, Full
from urllib.request import Request, urlopen, url2pathname, pathname2url
from urllib.parse import urlencode, urlparse, unquote
from urllib.error import HTTPError, URLError
