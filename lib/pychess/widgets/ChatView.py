from time import strftime, localtime
import random

from gi.repository import Gtk, Gdk, Pango, GObject

from pychess.System import uistuff
from pychess.widgets import insert_formatted
from pychess.Utils.IconLoader import load_icon
from pychess.ic.ICGameModel import ICGameModel


class ChatView(Gtk.Box):
    __gsignals__ = {
        'messageAdded': (GObject.SignalFlags.RUN_FIRST, None,
                         (str, str, object)),
        'messageTyped': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
    }

    def __init__(self, gamemodel=None):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.gamemodel = gamemodel

        # States for the color generator
        self.colors = {}
        self.startpoint = random.random()

        # Inits the read view
        self.readView = Gtk.TextView()

        self.sw = Gtk.ScrolledWindow()
        self.sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        self.sw.add(self.readView)
        self.readView.set_editable(False)
        self.readView.set_cursor_visible(False)
        self.readView.props.wrap_mode = Gtk.WrapMode.WORD
        self.readView.props.pixels_below_lines = 1
        self.readView.props.pixels_above_lines = 2
        self.readView.props.left_margin = 2

        if isinstance(self.gamemodel, ICGameModel):
            self.refresh = Gtk.Image()
            self.refresh.set_from_pixbuf(load_icon(16, "view-refresh",
                                                   "stock-refresh"))
            label = _("Observers")
            self.obs_btn = Gtk.Button()
            self.obs_btn.set_image(self.refresh)
            self.obs_btn.set_label(label)
            self.obs_btn_cid = self.obs_btn.connect("clicked", self.on_obs_btn_clicked)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            # Inits the observers view
            self.obsView = Gtk.TextView()
            self.obsView.set_cursor_visible(False)

            self.obsView.set_editable(False)
            self.obsView.props.wrap_mode = Gtk.WrapMode.WORD
            self.obsView.props.pixels_below_lines = 1
            self.obsView.props.pixels_above_lines = 2
            self.obsView.props.left_margin = 2

            text_buffer = self.obsView.get_buffer()
            iter = text_buffer.get_end_iter()
            anchor1 = text_buffer.create_child_anchor(iter)
            self.obsView.add_child_at_anchor(self.obs_btn, anchor1)
            self.button_tag = text_buffer.create_tag("observers")
            text_buffer.insert_with_tags_by_name(iter, " ", "observers")
            text_buffer.insert(iter, "\n")

            if not self.gamemodel.offline_lecture:
                vbox.pack_start(self.obsView, False, True, 0)
            vbox.pack_start(self.sw, True, True, 0)

            self.pack_start(vbox, True, True, 0)
        else:
            self.pack_start(self.sw, True, True, 0)

        # Create a 'log mark' in the beginning of the text buffer. Because we
        # query the log asynchronously and in chunks, we can use this to insert
        # it correctly after previous log messages, but before the new messages.
        start = self.readView.get_buffer().get_start_iter()
        self.readView.get_buffer().create_mark("logMark", start)

        # Inits the write view
        self.writeView = Gtk.Entry()

        box = Gtk.Box()
        self.pack_start(self.writeView, False, False, 0)
        box.add(self.writeView)

        if self.gamemodel is not None and self.gamemodel.offline_lecture:
            label = _("Go on")
            self.go_on_btn = Gtk.Button()
            self.go_on_btn.set_label(label)
            self.go_on_btn_cid = self.go_on_btn.connect(
                "clicked", lambda btn: self.gamemodel.lecture_skip_event.set())
            box.add(self.go_on_btn)

            label = _("Pause")
            self.pause_btn = Gtk.Button()
            self.pause_btn.set_label(label)
            self.pause_btn_cid = self.pause_btn.connect(
                "clicked", lambda btn: self.gamemodel.lecture_pause_event.set())
            box.add(self.pause_btn)

        self.pack_start(box, False, False, 0)

        self.writeview_cid = self.writeView.connect("key-press-event", self.onKeyPress)
        self.cid = None
        if self.gamemodel is not None:
            self.cid = self.gamemodel.connect_after("game_terminated", self.on_game_terminated)

    def on_game_terminated(self, model):
        if isinstance(self.gamemodel, ICGameModel):
            self.obs_btn.disconnect(self.obs_btn_cid)
        self.writeView.disconnect(self.writeview_cid)
        if self.cid is not None:
            self.gamemodel.disconnect(self.cid)

    def on_obs_btn_clicked(self, other):
        if not self.gamemodel.connection.ICC:
            allob = 'allob ' + str(self.gamemodel.ficsgame.gameno)
            self.gamemodel.connection.client.run_command(allob)

    def update_observers(self, other, observers):
        """ Rebuilds observers list text """
        text_buf = self.obsView.get_buffer()
        start_iter = text_buf.get_end_iter()
        start_iter.backward_to_tag_toggle(self.button_tag)
        start_iter.forward_char()
        end_iter = text_buf.get_end_iter()
        text_buf.delete(start_iter, end_iter)
        iter = text_buf.get_end_iter()

        obs_list = observers.split()
        for player in obs_list:
            # Colourize only players able to interact with chat View
            if player.endswith("(U)"):
                text_buf.insert(iter, "%s " % player[:-3])
            elif "(" in player:
                pref = player.split('(', 1)[0]
                self._ensureColor(pref)
                text_buf.insert_with_tags_by_name(iter, "%s " % player,
                                                  pref + "_bold")
            else:
                text_buf.insert(iter, "%s " % player)
        self.obsView.show_all()

    def _ensureColor(self, pref):
        """ Ensures that the tags for pref_normal and pref_bold are set in the text buffer """
        text_buf = self.readView.get_buffer()
        if pref not in self.colors:
            color = uistuff.genColor(len(self.colors) + 1, self.startpoint)
            self.colors[pref] = color
            color = [int(c * 255) for c in color]
            color = "#" + "".join([hex(v)[2:].zfill(2) for v in color])
            text_buf.create_tag(pref + "_normal", foreground=color)
            text_buf.create_tag(pref + "_bold", foreground=color,
                                weight=Pango.Weight.BOLD)
            if isinstance(self.gamemodel, ICGameModel):
                otb = self.obsView.get_buffer()
                otb.create_tag(pref + "_normal", foreground=color)
                otb.create_tag(pref + "_bold",
                               foreground=color,
                               weight=Pango.Weight.BOLD)

    def clear(self):
        self.writeView.get_buffer().props.text = ""
        self.readView.get_buffer().props.text = ""
        tagtable = self.readView.get_buffer().get_tag_table()
        for i in range(len(self.colors)):
            tagtable.remove("%d_normal" % i)
            tagtable.remove("%d_bold" % i)
        self.colors.clear()

    def __addMessage(self, iter, time, sender, text):
        pref = sender.lower()
        text_buffer = self.readView.get_buffer()
        iter = text_buffer.get_end_iter()
        text_buffer.create_mark("end", iter, False)
        if text_buffer.props.text:
            text_buffer.insert(iter, "\n")

        # Calculate a color for the sender
        self._ensureColor(pref)
        # Insert time, name and text with different stylesd
        text_buffer.insert_with_tags_by_name(iter, "(%s) " % time, pref + "_normal")
        text_buffer.insert_with_tags_by_name(iter, sender + ": ", pref + "_bold")
        insert_formatted(self.readView, iter, text)

        # Scroll the mark onscreen.
        mark = text_buffer.get_mark("end")
        text_buffer.move_mark(mark, iter)
        self.readView.scroll_mark_onscreen(mark)

        # This is used to buzz the user and add senders to a list of active participants
        self.emit("messageAdded", sender, text, self.colors[pref])

    def insertLogMessage(self, timestamp, sender, text):
        """ Takes a list of (timestamp, sender, text) pairs, and inserts them in
            the beginning of the document.
            All text will be in a gray color
        """
        text_buffer = self.readView.get_buffer()
        iter = text_buffer.get_iter_at_mark(text_buffer.get_mark("logMark"))
        time = strftime("%H:%M:%S", localtime(timestamp))
        self.__addMessage(iter, time, sender, text)

    def addMessage(self, sender, text):
        text_buffer = self.readView.get_buffer()
        iter = text_buffer.get_end_iter()
        self.__addMessage(iter, strftime("%H:%M:%S"), sender, text)

    def disable(self, message):
        """ Sets the write field insensitive, in cases where the channel is
            read only. Use the message to give the user a propriate
            exlpanation """
        self.writeView.set_sensitive(False)
        self.writeView.set_text(message)

    def enable(self):
        self.writeView.set_text("")
        self.writeView.set_sensitive(True)

    def onKeyPress(self, widget, event):
        if event.keyval in list(map(Gdk.keyval_from_name,
                                    ("Return", "KP_Enter"))):
            if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                buffer = self.writeView.get_buffer()
                if buffer.props.text:
                    self.emit("messageTyped", buffer.props.text)
                    buffer.props.text = ""
                return True
