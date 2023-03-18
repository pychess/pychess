from time import strftime

from gi.repository import GLib, Gtk, Gdk, GObject, Pango

from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix
from pychess.widgets import insert_formatted
from pychess.ic import FICS_COMMANDS, FICS_HELP


__title__ = _("Console")

__icon__ = addDataPrefix("glade/panel_terminal.svg")

__desc__ = _("Command line interface to the chess server")


class Sidepanel:
    def load(self, widgets, connection, lounge):
        self.connection = connection
        self.consoleView = ConsoleView(self.connection)
        self.consoleView.show_all()
        __widget__ = self.consoleView

        connection.com.connect("consoleMessage", self.onConsoleMessage)

        return __widget__

    @staticmethod
    def filter_unprintable(s):
        return "".join([c for c in s if ord(c) > 31 or ord(c) == 9 or c == "\n"])

    def scroll_to_bottom(self):
        tb_iter = self.consoleView.textbuffer.get_end_iter()
        self.consoleView.readView.scroll_to_iter(tb_iter, 0.00, True, 0.00, 1.00)

    def onConsoleMessage(self, com, lines, ini_lines=None):
        need_scroll = False
        if ini_lines is not None:
            for line in ini_lines:
                self.consoleView.addMessage(line, False)
                need_scroll = True

        for line in lines:
            line = self.filter_unprintable(line.line)
            if (
                line
                and (not line.startswith("<"))
                and (not line.startswith("{Game"))
                and (not line.endswith("available for matches."))
                and line[-12:-5] != "), Bug("
            ):
                self.consoleView.addMessage(line, False)
                need_scroll = True

        if need_scroll:
            # scroll to the bottom but only if we are not scrolled up to read back
            adj = self.consoleView.sw.get_vadjustment()
            if adj.get_value() >= adj.get_upper() - adj.get_page_size() - 1e-12:
                GLib.idle_add(self.scroll_to_bottom)


TYPE_COMMAND, TYPE_HELP, TYPE_USER = 0, 1, 2


class ConsoleView(Gtk.Box):
    __gsignals__ = {
        "messageAdded": (GObject.SignalFlags.RUN_FIRST, None, (str, str, object)),
        "messageTyped": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, connection):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.connection = connection
        self.connection.players.connect("FICSPlayerEntered", self.on_player_entered)
        self.connection.players.connect("FICSPlayerExited", self.on_player_exited)

        # Inits the read view
        self.readView = Gtk.TextView()
        fontdesc = Pango.FontDescription("Monospace 10")
        self.readView.modify_font(fontdesc)

        self.textbuffer = self.readView.get_buffer()
        self.textbuffer.create_tag("text")
        self.textbuffer.create_tag("mytext", weight=Pango.Weight.BOLD)

        self.sw = Gtk.ScrolledWindow()
        self.sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        uistuff.keepDown(self.sw)
        self.sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.set_cursor_visible(False)
        self.readView.props.wrap_mode = Gtk.WrapMode.WORD
        self.pack_start(self.sw, True, True, 0)

        # Inits entry
        self.history = []
        self.pos = 0

        self.liststore = Gtk.ListStore(str, int)
        for command in FICS_COMMANDS:
            self.liststore.append([command, TYPE_COMMAND])
        for command in FICS_HELP:
            self.liststore.append([command, TYPE_HELP])

        completion = Gtk.EntryCompletion()
        completion.set_model(self.liststore)
        completion.set_text_column(0)

        completion.set_minimum_key_length(2)
        completion.set_popup_set_width(False)

        def match(completion, entrystr, iter, data):
            modelstr = completion.get_model()[iter][0].lower()
            modeltype = completion.get_model()[iter][1]
            parts = entrystr.split()
            if len(parts) == 1 and modeltype == TYPE_COMMAND:
                return modelstr.startswith(entrystr)
            elif len(parts) == 2:
                if parts[0] == "help":
                    return modelstr.startswith(parts[1]) and modeltype == TYPE_HELP
                else:
                    return (
                        parts[0] in FICS_COMMANDS
                        and modelstr.startswith(parts[1].lower())
                        and modeltype == TYPE_USER
                    )

        completion.set_match_func(match, None)

        def on_match_selected(completion, treemodel, treeiter):
            modelstr = treemodel[treeiter][0]
            modeltype = treemodel[treeiter][1]
            entry = completion.get_entry()
            parts = entry.get_text().split()
            if len(parts) == 1 and modeltype == TYPE_COMMAND:
                entry.set_text(modelstr)
                entry.set_position(-1)
                return True
            elif len(parts) == 2:
                entry.set_text(f"{parts[0]} {modelstr}")
                entry.set_position(-1)
                return True

        completion.connect("match-selected", on_match_selected)

        self.entry = Gtk.Entry()
        self.entry.set_completion(completion)

        self.pack_start(self.entry, False, True, 0)

        self.entry.connect("key-press-event", self.onKeyPress)

    def on_player_entered(self, players, new_players):
        for player in new_players:
            self.liststore.append([player.name, TYPE_USER])

    def on_player_exited(self, players, player):
        for row in self.liststore:
            if row[0] == player.name:
                self.liststore.remove(row.iter)
                break

    def addMessage(self, text, my):
        tag = "mytext" if my else "text"
        text_buffer = self.readView.get_buffer()
        tb_iter = text_buffer.get_end_iter()
        # Messages have linebreak before the text. This is opposite to log
        # messages
        if text_buffer.props.text:
            text_buffer.insert(tb_iter, "\n")
        time = strftime("%H:%M:%S")
        text_buffer.insert_with_tags_by_name(tb_iter, "(%s) " % time, tag)
        insert_formatted(self.readView, tb_iter, text, tag=tag)

    def onKeyPress(self, widget, event):
        if event.keyval in list(map(Gdk.keyval_from_name, ("Return", "KP_Enter"))):
            if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                buffer = self.entry.get_buffer()
                if buffer.props.text.startswith("pas"):
                    # don't log password changes
                    self.connection.client.telnet.sensitive = True
                self.connection.client.run_command(buffer.props.text, show_reply=True)
                self.emit("messageTyped", buffer.props.text)
                self.addMessage(buffer.props.text, True)

                self.history.append(buffer.props.text)
                buffer.props.text = ""
                self.pos = len(self.history)
                return True

        elif event.keyval == Gdk.keyval_from_name("Up"):
            if self.pos > 0:
                buffer = self.entry.get_buffer()
                self.pos -= 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True

        elif event.keyval == Gdk.keyval_from_name("Down"):
            buffer = self.entry.get_buffer()
            if self.pos == len(self.history) - 1:
                self.pos += 1
                buffer.props.text = ""
            elif self.pos < len(self.history):
                self.pos += 1
                buffer.props.text = self.history[self.pos]
            widget.grab_focus()
            return True
