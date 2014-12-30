""" Some Python2/Python3 compatibility support helpers """

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    unichr = chr

    import builtins
    from urllib.parse import urlparse
    from configparser import SafeConfigParser
    from queue import Queue, Empty, Full
    from urllib.request import urlopen, url2pathname
    from urllib.parse import urlencode
else:
    unichr = unichr
    
    import __builtin__ as builtins
    from urlparse import urlparse
    from ConfigParser import SafeConfigParser
    from Queue import Queue, Empty, Full
    from urllib import urlopen, urlencode, url2pathname
