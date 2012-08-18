import gtk
import gobject

from gtk.gdk import keyval_from_name

from BorderBox import BorderBox
from pychess.System import uistuff
from pychess.System.glock import glock_connect


class ConsoleWindow:
    def __init__ (self, widgets, connection):
        self.connection = connection
        self.window = None
        
        widgets["show_console_button"].connect("clicked", self.showConsole)
        glock_connect(connection.com, "consoleMessage",
                      self.onConsoleMessage, after=False)
        glock_connect(connection, "disconnected",
                      lambda c: self.window and self.window.hide())

    def showConsole(self, *widget):
        if not self.window:
            self.initUi()
        self.window.show_all()
    
    def initUi (self):
        self.window = gtk.Window()
        self.window.set_border_width(12)
        self.window.set_icon_name("pychess")
        self.window.set_title("FICS Console")
        self.window.connect("delete-event", lambda w,e: w.hide() or True)
        
        uistuff.keepWindowSize("consolewindow", self.window, defaultSize=(650,400))

        self.consoleView = ConsoleView(self.connection)
        self.window.add(self.consoleView)
        
        self.consoleView.enable()

    def onConsoleMessage(self, com, line):
        if not self.window:
            return
        if (line[0] not in ('<', '{')) and \
           (not line.endswith('available for matches.')) and \
           (not ('Blitz' in line and 'Std' in line and 'Wild' in line and 'Light' in line and 'Bug' in line)):
            self.consoleView.addMessage(line)
        

class ConsoleView (gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (gobject.SIGNAL_RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (gobject.SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self, connection):
        gtk.VPaned.__init__(self)
        self.connection = connection
        
        # Inits the read view
        self.readView = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_NONE)
        uistuff.keepDown(sw)
        sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.props.wrap_mode = gtk.WRAP_WORD
        self.readView.props.pixels_below_lines = 1
        self.readView.props.pixels_above_lines = 2
        self.readView.props.left_margin = 2
        #self.readView.get_buffer().create_tag("log",
        #        foreground = self.readView.get_style().fg[gtk.STATE_INSENSITIVE])
        self.pack1(BorderBox(sw,bottom=True), resize=True, shrink=True)
        
        # Create a 'log mark' in the beginning of the text buffer. Because we
        # query the log asynchronously and in chunks, we can use this to insert
        # it correctly after previous log messages, but before the new messages.   
        start = self.readView.get_buffer().get_start_iter()
        self.readView.get_buffer().create_mark("logMark", start)
        
        # Inits the write view
        self.writeView = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.add(self.writeView)
        self.writeView.props.wrap_mode = gtk.WRAP_WORD
        self.writeView.props.pixels_below_lines = 1
        self.writeView.props.pixels_above_lines = 2
        self.writeView.props.left_margin = 2
        self.pack2(BorderBox(sw,top=True), resize=True, shrink=True)
        
        # Forces are reasonable position for the panner.
        def callback (widget, event):
            widget.disconnect(handle_id)
            allocation = widget.get_allocation()
            self.set_position(int(max(0.79*allocation.height, allocation.height-60)))
        handle_id = self.connect("expose-event", callback)
        
        self.writeView.connect("key-press-event", self.onKeyPress)

    
    def addMessage (self, text):
        tb = self.readView.get_buffer()
        iter = tb.get_end_iter()
        # Messages have linebreak before the text. This is opposite to log
        # messages
        if tb.props.text:
            tb.insert(iter, "\n")
        tb = self.readView.get_buffer()
        tb.insert(iter, text)
    
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
                print >> self.connection.client, buffer.props.text
                self.emit("messageTyped", buffer.props.text)
                buffer.props.text = ""
                return True
