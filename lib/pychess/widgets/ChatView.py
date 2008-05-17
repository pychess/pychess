from time import strftime, gmtime, localtime
import random

import gtk
from gtk.gdk import keyval_from_name
import pango
import gobject

from pychess.System import uistuff
from BorderBox import BorderBox

class ChatView (gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (gobject.SIGNAL_RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (gobject.SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self):
        gtk.VPaned.__init__(self)
        
        self.colors = {}
        self.startpoint = random.random()
        self.readView = gtk.TextView()
        self.writeView = gtk.TextView()
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_NONE)
        uistuff.keepDown(sw)
        sw.add(self.readView)
        self.readView.set_editable(False)
        #self.readView.set_size_request(-1,400)
        self.readView.props.wrap_mode = gtk.WRAP_WORD
        self.readView.props.pixels_below_lines = 1
        self.readView.props.pixels_above_lines = 2
        self.readView.props.left_margin = 2
        #self.readView.get_buffer().create_tag("log",
        #        foreground = self.readView.get_style().fg[gtk.STATE_INSENSITIVE])
        self.pack1(BorderBox(sw,bottom=True), resize=True, shrink=True)
        
        start = self.readView.get_buffer().get_start_iter()
        self.readView.get_buffer().create_mark("logMark", start)
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.add(self.writeView)
        #self.writeView.set_size_request(-1,20)
        self.writeView.props.wrap_mode = gtk.WRAP_WORD
        self.writeView.props.pixels_below_lines = 1
        self.writeView.props.pixels_above_lines = 2
        self.writeView.props.left_margin = 2
        self.pack2(BorderBox(sw,top=True), resize=True, shrink=True)
        
        def callback (widget, allocation):
            widget.disconnect(handle_id)
            self.set_position(int(max(0.79*allocation.height, allocation.height-60)))
        handle_id = self.connect("size-allocate", callback)
        
        self.writeView.connect("key-press-event", self.onKeyPress)
    
    def clear (self):
        self.writeView.get_buffer().props.text = ""
        self.readView.get_buffer().props.text = ""
        tagtable = self.readView.get_buffer().get_tag_table()
        for i in xrange(len(self.colors)):
            tagtable.remove("%d_normal" % i)
            tagtable.remove("%d_bold" % i)
        self.colors.clear()
    
    def appendLogMessage (self, timestamp, sender, text):
        """ Takes a list of (timestamp, sender, text) pairs, and inserts them in
            the beginning of the document.
            All text will be in a gray color """
        tb = self.readView.get_buffer()
        iter = tb.get_iter_at_mark(tb.get_mark("logMark"))
        tt = localtime(timestamp)
        tb.insert(iter, "(%s) %s: %s\n" % (strftime("%T",tt), sender, text))
    
    def addMessage (self, sender, text):
        pref = sender.lower()
        tb = self.readView.get_buffer()
        end = tb.get_end_iter()
        
        if not pref in self.colors:
            color = uistuff.genColor(len(self.colors)+1, self.startpoint)
            self.colors[pref] = color
            color = [int(c*255) for c in color]
            color = "#"+"".join([hex(v)[2:].zfill(2) for v in color])
            tb.create_tag(pref+"_normal", foreground=color)
            tb.create_tag(pref+"_bold", foreground=color, weight=pango.WEIGHT_BOLD)
        
        if tb.props.text:
            tb.insert(end, "\n")
        tb.insert_with_tags_by_name(end, "(%s) "%strftime("%T"), pref+"_normal")
        tb.insert_with_tags_by_name(end, sender+": ", pref+"_bold")
        tb.insert(end, text)
        
        self.emit("messageAdded", sender, text, self.colors[pref])
    
    def disable (self, message):
        """ Sets the write field insensitive, in cases where the channel is
            read only. Use the message to give the user a propriate
            exlpanation """
        self.writeView.set_sensitive(False)
        self.writeView.props.buffer.set_text(message)
    
    def enable (self):
        self.writeView.props.buffer.set_text("")
        self.writeView.set_sensitive(True)
    
    def onKeyPress (self, widget, event):
        if event.keyval in map(keyval_from_name,("Return", "KP_Enter")):
            if not event.state & gtk.gdk.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                self.emit("messageTyped", buffer.props.text)
                buffer.props.text = ""
                return True
