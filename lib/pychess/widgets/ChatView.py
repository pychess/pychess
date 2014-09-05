from time import strftime, gmtime, localtime
import random

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GObject

from pychess.System import glock
from pychess.System import uistuff
from BorderBox import BorderBox

class ChatView (Gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    
    def __init__ (self):
        GObject.GObject.__init__(self)
        
        # States for the color generator
        self.colors = {}
        self.startpoint = random.random()
        
        # Inits the read view
        self.readView = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.NONE)
        sw.set_size_request(-1, 20)
        uistuff.keepDown(sw)
        sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.props.wrap_mode = Gtk.WrapMode.WORD
        self.readView.props.pixels_below_lines = 1
        self.readView.props.pixels_above_lines = 2
        self.readView.props.left_margin = 2
        #self.readView.get_buffer().create_tag("log",
        #        foreground = self.readView.get_style().fg[Gtk.StateType.INSENSITIVE])
        self.pack1(BorderBox(sw,bottom=True), resize=True, shrink=True)
        
        # Create a 'log mark' in the beginning of the text buffer. Because we
        # query the log asynchronously and in chunks, we can use this to insert
        # it correctly after previous log messages, but before the new messages.   
        start = self.readView.get_buffer().get_start_iter()
        self.readView.get_buffer().create_mark("logMark", start)
        
        # Inits the write view
        self.writeView = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.NONE)
        sw.add(self.writeView)
        self.writeView.props.wrap_mode = Gtk.WrapMode.WORD
        self.writeView.props.pixels_below_lines = 1
        self.writeView.props.pixels_above_lines = 2
        self.writeView.props.left_margin = 2
        self.pack2(BorderBox(sw,top=True), resize=True, shrink=True)
        
        # Forces are reasonable position for the panner.
        def callback (widget, ctx):
            widget.disconnect(handle_id)
            allocation = widget.get_allocation()
            self.set_position(int(max(0.70*allocation.height, allocation.height-60)))        
        handle_id = self.connect("draw", callback)
        
        self.writeView.connect("key-press-event", self.onKeyPress)

    def _ensureColor(self, pref):
        """ Ensures that the tags for pref_normal and pref_bold are set in the text buffer """
        tb = self.readView.get_buffer()
        if not pref in self.colors:
            color = uistuff.genColor(len(self.colors) + 1, self.startpoint)
            self.colors[pref] = color
            color = [int(c * 255) for c in color]
            color = "#" + "".join([hex(v)[2:].zfill(2) for v in color])
            tb.create_tag(pref + "_normal", foreground=color)
            tb.create_tag(pref + "_bold", foreground=color, weight=Pango.Weight.BOLD)
    
    def clear (self):
        self.writeView.get_buffer().props.text = ""
        self.readView.get_buffer().props.text = ""
        tagtable = self.readView.get_buffer().get_tag_table()
        for i in xrange(len(self.colors)):
            tagtable.remove("%d_normal" % i)
            tagtable.remove("%d_bold" % i)
        self.colors.clear()
    
    def __addMessage (self, iter, time, sender, text):
        pref = sender.lower()
        tb = self.readView.get_buffer()
        # Calculate a color for the sender
        self._ensureColor(pref)
        # Insert time, name and text with different stylesd
        tb.insert_with_tags_by_name(iter, "(%s) "%time, pref+"_normal")
        tb.insert_with_tags_by_name(iter, sender+": ", pref+"_bold")
        tb.insert(iter, text)
        # This is used to buzz the user and add senders to a list of active participants
        self.emit("messageAdded", sender, text, self.colors[pref])
    
    def insertLogMessage (self, timestamp, sender, text):
        """ Takes a list of (timestamp, sender, text) pairs, and inserts them in
            the beginning of the document.
            All text will be in a gray color """
        glock.acquire()
        try:
            tb = self.readView.get_buffer()
            iter = tb.get_iter_at_mark(tb.get_mark("logMark"))
            time = strftime("%H:%M:%S", localtime(timestamp))
            self.__addMessage(iter, time, sender, text)
            tb.insert(iter, "\n")
        finally:
            glock.release()
    
    def addMessage (self, sender, text):
        glock.acquire()
        try:
            tb = self.readView.get_buffer()
            iter = tb.get_end_iter()
            # Messages have linebreak before the text. This is opposite to log
            # messages
            if tb.props.text: tb.insert(iter, "\n")
            self.__addMessage(iter, strftime("%H:%M:%S"), sender, text)
        finally:
            glock.release()
    
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
            if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                self.emit("messageTyped", buffer.props.text)
                buffer.props.text = ""
                return True
