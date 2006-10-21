import gobject

statusbar = None

def status (message, idle_add=False):
    if not statusbar: return
    def func():
        statusbar.pop(0)
        if message:
            statusbar.push(0,message)
    if idle_add:
        gobject.idle_add(func)
    else: func()
