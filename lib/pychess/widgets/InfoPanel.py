import re
from gi.repository import Gtk, GObject, Pango
from pychess.widgets import insert_formatted

TYPE_PERSONAL, TYPE_CHANNEL, TYPE_GUEST, \
    TYPE_ADMIN, TYPE_COMP, TYPE_BLINDFOLD = range(6)


def get_playername(playername):
    re_m = re.match("(\w+)\W*", playername)
    return re_m.groups()[0]


class BulletCellRenderer(Gtk.CellRenderer):
    __gproperties__ = {
        "color": (object, "Color", "Color", GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.color = None
        self.width = 16
        self.height = 16

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, context, widget, bg_area, cell_area, flags):
        if self.color is None:
            return
        else:
            red, green, blue = self.color

        x_loc, y_loc = self.get_size(widget, cell_area)[:2]

        context.set_source_rgb(red, green, blue)
        context.rectangle(x_loc, y_loc, self.width, self.height)
        context.fill()

        context.set_line_width(1)
        context.set_source_rgba(0, 0, 0, 0.5)
        context.rectangle(x_loc + 0.5, y_loc + 0.5, self.width - 1, self.height - 1)
        context.stroke()

        context.set_line_width(1)
        context.set_source_rgba(1, 1, 1, 0.5)
        context.rectangle(x_loc + 1.5, y_loc + 1.5, self.width - 3, self.height - 3)
        context.stroke()

    def on_get_size(self, widget, cell_area=None):
        if cell_area:
            y_loc = int(cell_area.height / 2. - self.height / 2.) + cell_area.y
            x_loc = cell_area.x
        else:
            y_loc = 0
            x_loc = 0
        return (x_loc + 1, y_loc + 1, self.width + 2, self.height + 2)


GObject.type_register(BulletCellRenderer)


class Panel:
    def start(self):
        pass

    def addItem(self, id, text, type, chat_view):
        pass

    def removeItem(self, id):
        pass

    def selectItem(self, id):
        pass


class InfoPanel(Gtk.Notebook, Panel):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.set_show_tabs(False)
        self.set_show_border(False)
        self.id2Widget = {}

        label = Gtk.Label()
        label.set_markup("<big>%s</big>" % _("No conversation's selected"))
        label.props.xalign = .5
        label.props.yalign = 0.381966011
        label.props.justify = Gtk.Justification.CENTER
        label.props.wrap = True
        label.props.width_request = 115
        self.append_page(label, None)

        self.connection = connection

    def addItem(self, grp_id, text, grp_type, chat_view):
        if grp_type in (TYPE_PERSONAL, TYPE_COMP, TYPE_GUEST, TYPE_ADMIN,
                        TYPE_BLINDFOLD):
            infoItem = self.PlayerInfoItem(grp_id, text, chat_view, self.connection)
        elif grp_type == TYPE_CHANNEL:
            infoItem = self.ChannelInfoItem(grp_id, text, chat_view,
                                            self.connection)
        self.addPage(infoItem, grp_id)

    def removeItem(self, grp_id):
        self.removePage(grp_id)

    def selectItem(self, grp_id):
        child = self.id2Widget.get(grp_id)
        if child is not None:
            self.set_current_page(self.page_num(child))

    def addPage(self, widget, grp_id):
        self.id2Widget[grp_id] = widget
        self.append_page(widget, None)
        widget.show_all()

    def removePage(self, grp_id):
        child = self.id2Widget.pop(grp_id)
        self.remove_page(self.page_num(child))

    class PlayerInfoItem(Gtk.Alignment):
        def __init__(self, id, text, chat_view, connection):
            GObject.GObject.__init__(self, xscale=1, yscale=1)
            self.add(Gtk.Label(label=_("Loading player data")))

            playername = get_playername(text)
            self.fm = connection.fm
            self.handle_id = self.fm.connect(
                "fingeringFinished", self.onFingeringFinished, playername)

            self.fm.finger(playername)

        def onFingeringFinished(self, fm, finger, playername):
            if not isinstance(self.get_child(), Gtk.Label) or \
                    finger.getName().lower() != playername.lower():
                return
            self.fm.disconnect(self.handle_id)

            label = Gtk.Label()
            label.set_markup("<b>%s</b>" % playername)
            widget = Gtk.Frame()
            widget.set_label_widget(label)
            widget.set_shadow_type(Gtk.ShadowType.NONE)

            alignment = Gtk.Alignment.new(0, 0, 1, 1)
            alignment.set_padding(3, 0, 12, 0)
            widget.add(alignment)

            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_cursor_visible(False)
            text_view.props.wrap_mode = Gtk.WrapMode.WORD

            tb_iter = text_view.get_buffer().get_end_iter()
            for i, note in enumerate(finger.getNotes()):
                if note:
                    insert_formatted(text_view, tb_iter, "%s\n" % note)
            text_view.show_all()
            scroll_win = Gtk.ScrolledWindow()
            scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroll_win.add(text_view)
            alignment.add(scroll_win)

            self.remove(self.get_child())
            self.add(widget)
            widget.show_all()

    class ChannelInfoItem(Gtk.Alignment):
        def __init__(self, grp_id, text, chat_view, connection):
            GObject.GObject.__init__(self, xscale=1, yscale=1)
            self.cm = connection.cm
            self.add(Gtk.Label(label=_("Receiving list of players")))

            self.names = set()
            chat_view.connect("messageAdded", self.onMessageAdded)
            self.store = Gtk.ListStore(object,  # (r,g,b) Color tuple
                                       str,  # name string
                                       bool  # is separator
                                       )

            connection.players.connect("FICSPlayerExited",
                                       self.onPlayerRemoved)

            self.handle_id = self.cm.connect("receivedNames",
                                             self.onNamesReceived, grp_id)
            self.cm.getPeopleInChannel(grp_id)

        def onPlayerRemoved(self, players, player):
            if player.name in self.names:
                for row in self.store:
                    if row[1] == player.name:
                        self.store.remove(row.iter)
                        break
                self.names.remove(player.name)

        def onNamesReceived(self, cm, channel, people, channel_):
            if not isinstance(self.get_child(),
                              Gtk.Label) or channel != channel_:
                return
            cm.disconnect(self.handle_id)

            scroll_win = Gtk.ScrolledWindow()
            scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            tv_list = Gtk.TreeView()
            tv_list.set_headers_visible(False)
            tv_list.set_tooltip_column(1)
            tv_list.set_model(self.store)
            tv_list.append_column(Gtk.TreeViewColumn("",
                                                     BulletCellRenderer(),
                                                     color=0))
            cell = Gtk.CellRendererText()
            cell.props.ellipsize = Pango.EllipsizeMode.END
            tv_list.append_column(Gtk.TreeViewColumn("", cell, text=1))
            tv_list.fixed_height_mode = True

            self.separatorIter = self.store.append([(), "", True])

            tv_list.set_row_separator_func(lambda m, i, d: m.get_value(i, 2),
                                           None)
            scroll_win.add(tv_list)

            self.store.connect("row-inserted",
                               lambda w, p, i: tv_list.queue_resize())
            self.store.connect("row-deleted", lambda w, i: tv_list.queue_resize())

            # Add those names. If this is not the first namesReceive, we only
            # add the new names
            noneed = set([name for (color, name, isSeparator) in self.store])
            for name in people:
                if name in noneed:
                    continue
                self.store.append([(1, 1, 1), name, False])
                self.names.add(name)

            self.remove(self.get_child())
            self.add(scroll_win)
            self.show_all()

        def onMessageAdded(self, chat_view, sender, text, color):
            s_iter = self.store.get_iter_first()

            # If the names list hasn't been retrieved yet, we have to skip this
            if not s_iter:
                return

            while self.store.get_path(s_iter) != self.store.get_path(
                    self.separatorIter):
                person = self.store.get_value(s_iter, 1)
                # If the person is already in the area before the separator, we
                # don't have to do anything
                if person.lower() == sender.lower():
                    return
                s_iter = self.store.iter_next(s_iter)

            # Go to s_iter after separator
            s_iter = self.store.iter_next(s_iter)

            while s_iter and self.store.iter_is_valid(s_iter):
                person = self.store.get_value(s_iter, 1)
                if person.lower() == sender.lower():
                    self.store.set_value(s_iter, 0, color)
                    self.store.move_before(s_iter, self.separatorIter)
                    return
                s_iter = self.store.iter_next(s_iter)

            # If the person was not in the area under the separator of the
            # store, it must be a new person, who has joined the channel, and we
            # simply add him before the separator
            self.store.insert_before(self.separatorIter,
                                     [color, sender, False])
