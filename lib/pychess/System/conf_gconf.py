import gconf
from os.path import normpath
GDIR = '/apps/pychess/'

def notify_add (key, func):
    key = normpath(GDIR+key)
    return c.notify_add(key, func)

def get (key):
    key = normpath(GDIR+key)
    for func in _type2getfunc.values():
        try: return func (key)
        except: continue
    return None

def set (key, value):
    key = normpath(GDIR+key)
    func = _type2setfunc[type(value)]
    func (key, value)

def _getConf ():
    c = gconf.client_get_default()
    c.add_dir(GDIR[:-1], gconf.CLIENT_PRELOAD_NONE)
    return c

c = _getConf ()

_type2gvalue = {
    bool: int(gconf.VALUE_BOOL),
    float: int(gconf.VALUE_FLOAT),
    int: int(gconf.VALUE_INT),
    str: int(gconf.VALUE_STRING)
}

from gobject import GError

def _getList (key):
    for v in _type2gvalue.values():
        try:
            return c.get_list(key, v)
        except GError, e:
            if str(e).startswith("Type mismatch: Expected list of"):
                continue
            raise GError, e
    return []

_type2getfunc = {
    bool: c.get_bool,
    float: c.get_float,
    int: c.get_int,
    list: _getList,
    str: c.get_string
}
  
def _putList (key, list):
    typ = None
    for v in list:
        if typ == None:
            typ = type(v)
            continue
        if typ != type(v):
            raise AttributeError, "All members of list must be of same type"
        if not type(v) in _type2gvalue:
            raise AttributeError, "Members of list must be of simple types"
            
    if typ == None: return
    c.set_list(key, _type2gvalue[typ], list)

_type2setfunc = {
    bool: c.set_bool,
    float: c.set_float,
    int: c.set_int,
    list: _putList,
    str: c.set_string
}
