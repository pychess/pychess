from __future__ import absolute_import

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango

from .BorderBox import BorderBox
from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.widgets import insert_formatted
from pychess.widgets.Background import set_textview_color


class ConsoleWindow (object):
    def __init__ (self, widgets, connection):
        self.connection = connection

        self.window = Gtk.Window()
        self.window.set_border_width(12)

        # ChatWindow uses this to check is_active() so don't touch this!
        self.window.set_icon_name("pychess")

        self.window.set_title("%s Console" % connection.ics_name)
        self.window.connect("delete-event", lambda w,e: w.hide() or True)

        uistuff.keepWindowSize("consolewindow", self.window, defaultSize=(700,400))

        self.consoleView = ConsoleView(self.connection)
        self.window.add(self.consoleView)

        widgets["show_console_button"].connect("clicked", self.showConsole)
        connection.com.connect("consoleMessage", self.onConsoleMessage)
        connection.connect("disconnected", self.onDisconnected)

    @idle_add
    def onDisconnected(self, conn):
        if self.window:
            self.window.hide()

    def showConsole(self, *widget):
        self.window.show_all()
        self.window.present()
        self.consoleView.writeView.grab_focus()

        # scroll to the bottom
        adj = self.consoleView.sw.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    @staticmethod
    def filter_unprintable(s):
        return ''.join([c for c in s if ord(c) > 31 or ord(c) == 9])

    def onConsoleMessage(self, com, lines):
        for line in lines:
            line = self.filter_unprintable(line.line)
            if line and not line.startswith('<'):
                self.consoleView.addMessage(line, False)


class ConsoleView (Gtk.VPaned):
    __gsignals__ = {
        'messageAdded' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,object)),
        'messageTyped' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        # Inits the read view
        self.readView = Gtk.TextView()
        fontdesc = Pango.FontDescription("Monospace 10")
        self.readView.modify_font(fontdesc)

        self.textbuffer = self.readView.get_buffer()

        set_textview_color(self.readView)

        self.textbuffer.create_tag("text")
        self.textbuffer.create_tag("mytext", weight=Pango.Weight.BOLD)

        self.sw = sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.NONE)
        uistuff.keepDown(sw)
        sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.set_cursor_visible(False)
        self.readView.props.wrap_mode = Gtk.WrapMode.WORD
        self.pack1(sw, resize=True, shrink=True)

        # Inits the write view
        self.history = []
        self.pos = 0
        self.writeView = Gtk.Entry()
        #self.writeView.set_width_chars(80)
        self.pack2(self.writeView, resize=True, shrink=True)

        # Forces are reasonable position for the panner.
        def callback (widget, context):
            widget.disconnect(handle_id)
            allocation = widget.get_allocation()
            self.set_position(int(max(0.79*allocation.height, allocation.height-60)))
        handle_id = self.connect("draw", callback)

        self.writeView.connect("key-press-event", self.onKeyPress)

    @idle_add
    def addMessage (self, text, my):
        tb = self.readView.get_buffer()
        iter = tb.get_end_iter()
        # Messages have linebreak before the text. This is opposite to log
        # messages
        if tb.props.text:
            tb.insert(iter, "\n")
        tb = self.readView.get_buffer()
        tag = "mytext" if my else "text"
        insert_formatted(self.readView, iter, text, tag=tag)

        # scroll to the bottom but only if we are not scrolled up to read back
        adj = self.sw.get_vadjustment()
        if adj.get_value() >= adj.get_upper() - adj.get_page_size() - 1e-12:
            iter = tb.get_end_iter()
            self.readView.scroll_to_iter(iter, 0.00, False, 1.00, 1.00)

    def onKeyPress (self, widget, event):
        if event.keyval in map(Gdk.keyval_from_name,("Return", "KP_Enter")):
            if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                self.connection.client.run_command(buffer.props.text)
                self.emit("messageTyped", buffer.props.text)
                self.addMessage(buffer.props.text, True)

                # Maintain variables backup, it will be restored to fics on quit
                for var in self.connection.lvm.variablesBackup:
                    if buffer.props.text == "set %s" % var:
                        if self.connection.lvm.variablesBackup[var] == 0:
                            self.connection.lvm.variablesBackup[var] = 1
                        else:
                            self.connection.lvm.variablesBackup[var] = 0
                    elif buffer.props.text in ("set %s 1" % var, "set %s on" % var, "set %s true" % var):
                        self.connection.lvm.variablesBackup[var] = 1
                    elif buffer.props.text in ("set %s 0" % var, "set %s off" % var, "set %s false" % var):
                        self.connection.lvm.variablesBackup[var] = 0
                    elif buffer.props.text.startswith("set %s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.variablesBackup[var] = parts[2]

                # Maintain lists backup, it will be restored to fics on quit
                for list in self.connection.lvm.personalBackup:
                    if buffer.props.text.startswith("addlist %s " % var) or buffer.props.text.startswith("+%s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.personalBackup[var].add(parts[2])
                    if buffer.props.text.startswith("sublist %s " % var) or buffer.props.text.startswith("-%s " % var):
                        parts = buffer.props.text.split()
                        if len(parts) == 3 and parts[2]:
                            self.connection.lvm.personalBackup[var].discard(parts[2])

                self.history.append(buffer.props.text)
                buffer.props.text = ""
                self.pos = len(self.history)
                return True

        elif event.keyval == Gdk.keyval_from_name("Up"):
            if self.pos > 0:
                buffer = self.writeView.get_buffer()
                self.pos -= 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True

        elif event.keyval == Gdk.keyval_from_name("Down"):
            buffer = self.writeView.get_buffer()
            if self.pos == len(self.history)-1:
                self.pos += 1
                buffer.props.text = ""
            elif self.pos < len(self.history):
                self.pos += 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True
