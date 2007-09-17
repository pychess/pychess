# -*- coding: UTF-8 -*-

import os.path

import gtk, pango, gobject

from pychess.System import glock
from pychess.System.Log import log
from pychess.System.Log import DEBUG, LOG, WARNING, ERROR
from pychess.System.prefix import addDataPrefix

notebook = gtk.Notebook()
task2book = {}

destroy_funcs = []
def add_destroy_notify (func):
    destroy_funcs.append(func)

width = height = -1

ready = False
def ensureReady ():
    global ready
    if ready:
        return
    else: ready = True
    
    global w
    w = gtk.Window()
    w.set_title(_("PyChess - Log Viewer"))
    iconpath = addDataPrefix("glade/16.png")
    w.set_icon(gtk.gdk.pixbuf_new_from_file(iconpath))
    
    notebook.show()
    w.add(notebook)
    
    tv = gtk.TextView()
    pango_ctx = tv.get_pango_context()
    font_desc = tv.get_style().font_desc
    font_desc.set_family("Monospace")
    metrics = pango_ctx.get_metrics(font_desc)
    
    global width, height
    width = pango.PIXELS(metrics.get_approximate_char_width())*80
    height = pango.PIXELS(metrics.get_ascent()+metrics.get_descent())*24
    for c in notebook.get_children():
        c.set_size_request(width, height)
    
    def _destroy_notify (widget, *args):
    	[func() for func in destroy_funcs]
    	return True
    w.connect("delete-event", _destroy_notify)
    
def newMessage (task, message, type):
    if not task in task2book:
        view = gtk.TextView ()
        view.set_editable(False)
        vp = gtk.Viewport()
        vp.set_shadow_type(gtk.SHADOW_NONE)
        vp.add(view)
        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        if width > -1:
            scroll.set_size_request(width, height)
        scroll.add(vp)
        
        def changed (vadjust):
            if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
                vadjust.set_value(vadjust.upper-vadjust.page_size)
                vadjust.need_scroll = True
        scroll.get_vadjustment().connect("changed", changed)
        
        def value_changed (vadjust):
            vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - \
            		vadjust.upper) < vadjust.step_increment
        scroll.get_vadjustment().connect("value-changed", value_changed)
        
        notebook.append_page (scroll, gtk.Label(task))
        notebook.show_all()
        textbuffer = view.get_buffer()
        textbuffer.create_tag(str(DEBUG), family='Monospace')
        textbuffer.create_tag(str(LOG), family='Monospace', weight=pango.WEIGHT_BOLD)
        textbuffer.create_tag(str(WARNING), family='Monospace', foreground="red")
        textbuffer.create_tag(str(ERROR), family='Monospace', weight=pango.WEIGHT_BOLD, foreground="red")
        task2book[task] = textbuffer
    else: textbuffer = task2book[task]
    
    textbuffer.insert_with_tags_by_name(
            textbuffer.get_end_iter(), message, str(type))

#
# Add early messages and connect for new
#

def addMessages (messages):
    for task, message, type in messages:
        newMessage (task, message, type)

glock.acquire()
try:
    addMessages(log.messages)
    log.messages = None
finally:
    glock.release()

log.connect ("logged", lambda log, messages: addMessages(messages))

#
# External functions
#

def show ():
    ensureReady ()
    w.show_all()
    
def hide ():
    w.hide()


