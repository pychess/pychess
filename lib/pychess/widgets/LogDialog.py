# -*- coding: UTF-8 -*-

import os.path
import time
import codecs

import gtk, pango, gobject

from pychess.System import glock, uistuff
from pychess.System.Log import log
from pychess.System.Log import LOG_DEBUG, LOG_LOG, LOG_WARNING, LOG_ERROR
from pychess.System.prefix import addDataPrefix

def rawreplace(error):
    symbols = (ur"\x%02x" % ord(s)
        for s in error.object[error.start:error.end])
    return u"".join(symbols), error.end
codecs.register_error("rawreplace", rawreplace)

class InformationWindow:
    
    @classmethod
    def _init (cls):
        cls.tagToIter = {}
        cls.tagToPage = {}
        cls.pathToPage = {}
        cls.tagToTime = {}
        
        cls.window = gtk.Window()
        cls.window.set_title(_("PyChess Information Window"))
        cls.window.set_border_width(12)
        uistuff.keepWindowSize("logdialog", cls.window, (640,480))
        mainHBox = gtk.HBox()
        mainHBox.set_spacing(6)
        cls.window.add(mainHBox)
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        mainHBox.pack_start(sw, expand=False)
        cls.treeview = gtk.TreeView(gtk.TreeStore(str))
        cls.treeview.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=0))
        cls.treeview.set_headers_visible(False)
        cls.treeview.get_selection().set_mode(gtk.SELECTION_BROWSE)
        sw.add(cls.treeview)
        cls.pages = gtk.Notebook()
        cls.pages.set_show_tabs(False)
        cls.pages.set_show_border(False)
        mainHBox.pack_start(cls.pages)
        
        mainHBox.show_all()
        
        def selectionChanged (selection):
            treestore, iter = selection.get_selected()
            if iter:
                child = cls.pathToPage[treestore.get_path(iter)]["child"]
                cls.pages.set_current_page(cls.pages.page_num(child))
        cls.treeview.get_selection().connect("changed", selectionChanged)
    
    @classmethod
    def show (cls):
        cls.window.show()
    
    @classmethod
    def hide (cls):
        cls.window.hide()
    
    @classmethod
    def newMessage (cls, tag, timestamp, message, importance):
        textview = cls._getPageFromTag(tag)["textview"]
        
        if not tag in cls.tagToTime or timestamp-cls.tagToTime[tag] >= 1:
            t = time.strftime("%T",time.localtime(timestamp))
            textview.get_buffer().insert_with_tags_by_name(
                textview.get_buffer().get_end_iter(),
                "\n%s\n------------------------------------------------------------\n"%t,
                str(LOG_LOG))
            cls.tagToTime[tag] = timestamp
        
        if type(message) == str:
            message = unicode(message, "utf-8", 'rawreplace')
        textview.get_buffer().insert_with_tags_by_name(
            textview.get_buffer().get_end_iter(), message, str(importance))
    
    @classmethod
    def _createPage (cls, parrentIter, tag):
        name = tag[-1]
        iter = cls.treeview.get_model().append(parrentIter, (name,))
        cls.tagToIter[tag] = iter
        
        widgets = uistuff.GladeWidgets("findbar.glade")
        frame = widgets["frame"]
        frame.unparent()
        frame.show_all()
        
        uistuff.keepDown(widgets["scrolledwindow"])
        textview = widgets["textview"]
        tb = textview.get_buffer()
        tb.create_tag(str(LOG_DEBUG), family='Monospace')
        tb.create_tag(str(LOG_LOG), family='Monospace', weight=pango.WEIGHT_BOLD)
        tb.create_tag(str(LOG_WARNING), family='Monospace', foreground="red")
        tb.create_tag(str(LOG_ERROR), family='Monospace', weight=pango.WEIGHT_BOLD, foreground="red")
        
        
        findbar = widgets["findbar"]
        findbar.hide()
        # Make searchEntry and "out of label" share height with the buttons
        widgets["prevButton"].connect("size-allocate", lambda w, alloc:
                widgets["searchEntry"].set_size_request(-1, alloc.height) or
                widgets["outofLabel"].set_size_request(-1, alloc.height-2))
        
        # Make "out of label" more visually distinct
        uistuff.makeYellow(widgets["outofLabel"])
        widgets["outofLabel"].hide()
        
        widgets["closeButton"].connect("clicked", lambda w:
                                       widgets["findbar"].hide())
        
        # Connect showing/hiding of the findbar
        cls.window.connect("key-press-event", cls.onTextviewKeypress, widgets)
        widgets["findbar"].connect("key-press-event", cls.onFindbarKeypress)
        
        widgets["searchEntry"].connect("changed", cls.onSearchChanged, widgets)
        
        widgets["prevButton"].connect("clicked", lambda w: cls.searchJump(-1, widgets))
        widgets["nextButton"].connect("clicked", lambda w: cls.searchJump(1, widgets))
        
        
        
        
        cls.pages.append_page(frame)
        page = {"child": frame, "textview":textview}
        cls.tagToPage[tag] = page
        cls.pathToPage[cls.treeview.get_model().get_path(iter)] = page
    
    @classmethod
    def _getPageFromTag (cls, tag):
        if type(tag) == list:
            tag = tuple(tag)
        elif type(tag) != tuple:
            tag = (tag,)
        
        if tag in cls.tagToPage:
            return cls.tagToPage[tag]
        
        for i in xrange(len(tag)-1):
            subtag = tag[:-i-1]
            if subtag in cls.tagToIter:
                newtag = subtag+(tag[len(subtag)],)
                iter = cls.tagToIter[subtag]
                cls._createPage(iter, newtag)
                return cls._getPageFromTag(tag)
        
        cls._createPage(None, tag[:1])
        return cls._getPageFromTag(tag)
    
    @classmethod
    def onSearchChanged (cls, searchEntry, widgets):
        pattern = searchEntry.get_text()
        widgets["outofLabel"].props.visible = bool(pattern)
        if not pattern:
            return
        
        text = widgets["textview"].get_buffer().props.text.lower()
        
        widgets["outofLabel"].hits = []
        widgets["outofLabel"].searchCurrent = -1
        i = -len(pattern)
        while True:
            i = text.find(pattern, i+len(pattern))
            if i != -1:
                widgets["outofLabel"].hits.append(i)
            else: break
        
        cls.searchJump(1, widgets)
        
    @classmethod
    def searchJump (cls, count, widgets):
        if not hasattr(widgets["outofLabel"], "hits"):
            return
        amount = len(widgets["outofLabel"].hits)
        if not amount:
            widgets["outofLabel"].set_text("0 %s 0" % _("of"))
        else:
            widgets["outofLabel"].searchCurrent += count
            current = widgets["outofLabel"].searchCurrent % amount
            widgets["outofLabel"].set_text("%d %s %d" % (current+1, _("of"), amount))
            goto = widgets["outofLabel"].hits[current]
            iter0 = widgets["textview"].get_buffer().get_iter_at_offset(goto)
            length = len(widgets["searchEntry"].get_text())
            iter1 = widgets["textview"].get_buffer().get_iter_at_offset(goto+length)
            widgets["textview"].get_buffer().select_range(iter0, iter1)
            widgets["textview"].scroll_to_iter(iter0, 0.2)
    
    @classmethod
    def onTextviewKeypress (cls, textview, event, widgets):
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.keyval in (ord("f"), ord("F")):
                widgets["findbar"].props.visible = not widgets["findbar"].props.visible
                if widgets["findbar"].props.visible:
                    signal = widgets["searchEntry"].connect_after("expose-event",
                            lambda w,e: w.grab_focus() or
                            widgets["searchEntry"].disconnect(signal))
    
    @classmethod
    def onFindbarKeypress (cls, findbar, event):
        if gtk.gdk.keyval_name(event.keyval) == "Escape":
            findbar.props.visible = False
    
    
uistuff.cacheGladefile("findbar.glade")

################################################################################
# Add early messages and connect for new                                       #
################################################################################

InformationWindow._init()

def addMessages (messages):
    for task, timestamp, message, type in messages:
        InformationWindow.newMessage (task, timestamp, message, type)

glock.acquire()
try:
    addMessages(log.messages)
    log.messages = None
finally:
    glock.release()

log.connect ("logged", lambda log, messages: addMessages(messages))

################################################################################
# External functions                                                           #
################################################################################

destroy_funcs = []
def add_destroy_notify (func):
    destroy_funcs.append(func)
def _destroy_notify (widget, *args):
    [func() for func in destroy_funcs]
    return True
InformationWindow.window.connect("delete-event", _destroy_notify)

def show ():
    InformationWindow.show()

def hide ():
    InformationWindow.hide()

if __name__ == "__main__":
    show()
    InformationWindow.window.connect("delete-event", gtk.main_quit)
    gtk.main()
