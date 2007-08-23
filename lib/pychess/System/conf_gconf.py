import gconf
from os.path import normpath

GDIR = '/apps/pychess/'
c = gconf.client_get_default()
c.add_dir(GDIR[:-1], gconf.CLIENT_PRELOAD_NONE)

def notify_add (key, func):
    key = normpath(GDIR+key)
    return c.notify_add(key, func)

def notify_remove (conid):
    c.notify_remove(conid)

def get (key):
    key = normpath(GDIR+key)
    value = c.get(key)
    if value.type == gconf.VALUE_BOOL:
        return v.get_bool()
    if value.type == gconf.VALUE_FLOAT:
        return v.get_float()
    if value.type == gconf.VALUE_INT:
        return v.get_int()
    if value.type == gconf.VALUE_STRING:
        return v.get_string()

def set (key, value):
    key = normpath(GDIR+key)
    typ = type(value)
    if typ == bool:
        c.set_bool(value)
    if typ == float:
        c.set_float(value)
    if typ == int:
        c.set_int(value)
    if typ == str:
        c.set_string(value)

def any (gen):
    for item in gen:
        if item:
            return True
    return False

def hasKey (key):
    key = normpath(GDIR+key)
    return any(key == entry.get_key() for entry in c.all_entries(GDIR))
