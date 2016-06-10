import re

from gi.repository import Gtk, Gdk, GObject, Pango

from pychess.compat import cmp
from pychess.Utils.IconLoader import load_icon
from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.widgets import insert_formatted
from pychess.widgets.ChatView import ChatView
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import EAST, WEST, CENTER

TYPE_PERSONAL, TYPE_CHANNEL, TYPE_GUEST, \
    TYPE_ADMIN, TYPE_COMP, TYPE_BLINDFOLD = range(6)


def get_playername(playername):
    re_m = re.match("(\w+)\W*", playername)
    return re_m.groups()[0]


class BulletCellRenderer(Gtk.CellRenderer):
    __gproperties__ = {
        "color": (object, "Color", "Color", GObject.PARAM_READWRITE),
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

add_icon = load_icon(16, "gtk-add", "list-add")
remove_icon = load_icon(16, "gtk-remove", "list-remove")


class TextImageTree(Gtk.TreeView):
    """ :Description: Defines a tree with two columns.
        The first one has text. The second one a clickable stock_icon
    """

    __gsignals__ = {
        'activated': (GObject.SignalFlags.RUN_FIRST, None, (str, str, int)),
        'selected': (GObject.SignalFlags.RUN_FIRST, None, (str, int))
    }

    def __init__(self, icon):
        GObject.GObject.__init__(self)
        self.id2iter = {}

        pm = Gtk.ListStore(str, str, int, str)
        self.sort_model = Gtk.TreeModelSort(model=pm)
        self.set_model(self.sort_model)
        self.idSet = set()

        self.set_headers_visible(False)
        self.set_tooltip_column(3)
        self.set_search_column(1)
        self.sort_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        self.sort_model.set_sort_func(1, self.compareFunction, 1)

        # First column
        crt = Gtk.CellRendererText()
        crt.props.ellipsize = Pango.EllipsizeMode.END
        self.leftcol = Gtk.TreeViewColumn("", crt, text=1)
        self.leftcol.set_expand(True)
        self.append_column(self.leftcol)

        # Second column
        crp = Gtk.CellRendererPixbuf()
        crp.props.pixbuf = icon
        self.rightcol = Gtk.TreeViewColumn("", crp)
        self.append_column(self.rightcol)

        # Mouse
        self.pressed = None
        self.stdcursor = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
        self.linkcursor = Gdk.Cursor.new(Gdk.CursorType.HAND2)
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)

        # Selection
        self.get_selection().connect("changed", self.selection_changed)

    @idle_add
    def addRow(self, grp_id, text, grp_type):
        """ :Description: Takes a player or a channel identified by grp_id and adds
            them to the correct group defined by grp_type
            :return: None
        """
        if grp_id in self.id2iter:
            return
        model = self.sort_model.get_model()
        m_iter = model.append([grp_id, text, grp_type, GObject.markup_escape_text(text)])
        self.id2iter[grp_id] = m_iter
        self.idSet.add(grp_id)

    @idle_add
    def removeRow(self, grp_id):
        """ :Description: Takes a player or channel identified by grp_id and removes them from
            the data model.
            :return: None
        """
        try:
            m_iter = self.id2iter[grp_id]
        except KeyError:
            return
        model = self.sort_model.get_model()
        model.remove(m_iter)
        del self.id2iter[grp_id]
        self.idSet.remove(grp_id)

    @idle_add
    def selectRow(self, grp_id):
        """ :Description: Takes a grp_id and finds the row associated with this id then
            sets this row to be the focus ie selected

            :returns: None
        """
        m_iter = self.id2iter[grp_id]
        m_iter = self.sort_model.convert_child_iter_to_iter(m_iter)[1]
        sel = self.get_selection()
        sel.select_iter(m_iter)

    def __contains__(self, grp_id):
        """ :Description: Checks to see if a grp_id in a member of the id set
            :returns: boolean
        """
        return grp_id in self.idSet

    def button_press(self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            self.pressed = path_col_pos[0]

    def button_release(self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            if self.pressed == path_col_pos[0]:
                model = self.sort_model
                m_iter = model.get_iter(self.pressed)
                grp_id = model.get_value(m_iter, 0)
                text = model.get_value(m_iter, 1)
                grp_type = model.get_value(m_iter, 2)
                self.emit("activated", grp_id, text, grp_type)
        self.pressed = None

    def motion_notify(self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            self.get_window().set_cursor(self.linkcursor)
        else:
            self.get_window().set_cursor(self.stdcursor)

    def leave_notify(self, widget, event):
        self.get_window().set_cursor(self.stdcursor)

    def selection_changed(self, selection):
        model, m_iter = selection.get_selected()
        if m_iter:
            grp_id = model.get_value(m_iter, 0)
            grp_type = model.get_value(m_iter, 2)
            self.emit("selected", grp_id, grp_type)

    def compareFunction(self, treemodel, iter0, iter1, column):
        val0 = treemodel.get_value(iter0, column).split(":")[0]
        val1 = treemodel.get_value(iter1, column).split(":")[0]
        if val0.isdigit() and val1.isdigit():
            return cmp(int(val0), int(val1))
        return cmp(val0, val1)


class Panel(object):
    def start(self):
        pass

    def addItem(self, id, text, type, chat_view):
        pass

    def removeItem(self, id):
        pass

    def selectItem(self, id):
        pass

# ===============================================================================
# Panels
# ===============================================================================


class ViewsPanel(Gtk.Notebook, Panel):
    """ :Description: This panel is used to display the main chat text for each of the channel or
        private communication
    """

    __gsignals__ = {
        'channel_content_Changed': (GObject.SignalFlags.RUN_FIRST, None,
                                    (str, int))
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.set_show_tabs(False)
        self.set_show_border(False)
        self.id2Widget = {}
        self.connection = connection

        label = Gtk.Label()
        label.set_markup("<big>%s</big>" %
                         _("You have opened no conversations yet"))
        label.props.xalign = .5
        label.props.yalign = 0.381966011
        label.props.justify = Gtk.Justification.CENTER
        label.props.wrap = True
        label.props.width_request = 300
        self.append_page(label, None)

        # When a person addresses us directly, ChannelsPanel will emit an
        # additem event and we add a new view. This however means that the first
        # message the user sends isn't registred by our privateMessage handler.
        # Therefore we save all messages sent by this hook, and when later we
        # add new items, we test if anything was already received
        self.messageBuffer = {}

        def globalPersonalMessage(cm, name, title, isadmin, text):
            if name not in self.messageBuffer:
                self.messageBuffer[name] = []
            self.messageBuffer[name].append((title, isadmin, text))

        self.connection.cm.connect("privateMessage", globalPersonalMessage)

    def addItem(self, grp_id, name, grp_type, chat_view):
        chat_view.connect("messageTyped", self.onMessageTyped, grp_id, name, grp_type)
        self.connection.cm.connect("channelMessage", self.onChannelMessage, grp_id,
                                   chat_view)
        self.connection.cm.connect("privateMessage", self.onPersonMessage,
                                   get_playername(name), chat_view)

        if grp_type == TYPE_CHANNEL:
            self.connection.cm.connect("channelLog", self.onChannelLog, grp_id,
                                       chat_view)
            self.connection.cm.getChannelLog(grp_id)
            if not self.connection.cm.mayTellChannel(grp_id):
                chat_view.disable(_(
                    "Only registered users may talk to this channel"))

        elif grp_type in (TYPE_PERSONAL, TYPE_COMP, TYPE_GUEST,
                          TYPE_ADMIN, TYPE_BLINDFOLD):
            if name in self.messageBuffer:
                for title, isadmin, messagetext in self.messageBuffer[name]:
                    chat_view.addMessage(name, messagetext)
                del self.messageBuffer[name]

        self.addPage(chat_view, grp_id)

    def removeItem(self, grp_id):
        self.removePage(grp_id)

    def selectItem(self, grp_id):
        child = self.id2Widget[grp_id]
        self.set_current_page(self.page_num(child))

    def onChannelLog(self, cm, channel, time, handle, text, name_, chat_view):
        if channel.lower() == name_.lower():
            chat_view.insertLogMessage(time, handle, text)

    def onMessageTyped(self, chat_view, text, grp_id, name, grp_type):
        if grp_type == TYPE_CHANNEL:
            self.connection.cm.tellChannel(grp_id, text)
        elif grp_type == TYPE_PERSONAL:
            self.connection.cm.tellPlayer(get_playername(name), text)
        chat_view.addMessage(self.connection.getUsername(), text)

    def onPersonMessage(self, cm, name, title, isadmin, text, name_, chat_view):
        if name.lower() == name_.lower():
            chat_view.addMessage(name, text)
            self.emit('channel_content_Changed', name_, TYPE_PERSONAL)

    def onChannelMessage(self, cm, name, isadmin, isme, channel, text, name_,
                         chat_view):
        if channel.lower() == name_.lower() and not isme:
            chat_view.addMessage(name, text)
            self.emit('channel_content_Changed', channel, TYPE_CHANNEL)

    def addPage(self, widget, grp_id):
        self.id2Widget[grp_id] = widget
        self.append_page(widget, None)
        widget.show_all()

    def removePage(self, grp_id):
        child = self.id2Widget.pop(grp_id)
        self.remove_page(self.page_num(child))


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

        @idle_add
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

        @idle_add
        def onPlayerRemoved(self, players, player):
            if player.name in self.names:
                for row in self.store:
                    if row[1] == player.name:
                        self.store.remove(row.iter)
                        break
                self.names.remove(player.name)

        @idle_add
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

        @idle_add
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


class ChannelsPanel(Gtk.ScrolledWindow, Panel):

    __gsignals__ = {
        'conversationAdded': (GObject.SignalFlags.RUN_FIRST, None,
                              (str, str, int)),
        'conversationRemoved': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'conversationSelected': (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox = Gtk.VBox()
        self.add_with_viewport(vbox)
        self.get_child().set_shadow_type(Gtk.ShadowType.NONE)

        self.joinedList = TextImageTree(remove_icon)
        self.joinedList.connect("activated", self.onRemove)
        self.joinedList.connect("selected", self.onSelect)
        vbox.pack_start(self.joinedList, True, True, 0)

        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander = Gtk.Expander.new(_("Friends"))
        vbox.pack_start(expander, False, True, 0)
        self.friendsList = TextImageTree(add_icon)
        self.friendsList.connect("activated", self.onAdd)
        self.friendsList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.friendsList)
        self.channels = {}

        expander = Gtk.Expander.new(_("Admin"))
        vbox.pack_start(expander, False, True, 0)
        self.adminList = TextImageTree(add_icon)
        self.adminList.connect("activated", self.onAdd)
        self.adminList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.adminList)

        expander = Gtk.Expander.new(_("More channels"))
        vbox.pack_start(expander, False, True, 0)
        self.channelsList = TextImageTree(add_icon)
        self.channelsList.connect("activated", self.onAdd)
        self.channelsList.fixed_height_mode = True
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.channelsList)

        expander = Gtk.Expander.new(_("More players"))
        vbox.pack_start(expander, False, True, 0)
        self.playersList = TextImageTree(add_icon)
        self.playersList.connect("activated", self.onAdd)
        self.playersList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.playersList)

        expander = Gtk.Expander.new(_("Computers"))
        vbox.pack_start(expander, False, True, 0)
        self.compList = TextImageTree(add_icon)
        self.compList.connect("activated", self.onAdd)
        self.compList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.compList)

        expander = Gtk.Expander.new(_("BlindFold"))
        vbox.pack_start(expander, False, True, 0)
        self.blindList = TextImageTree(add_icon)
        self.blindList.connect("activated", self.onAdd)
        self.blindList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.blindList)

        expander = Gtk.Expander.new(_("Guests"))
        vbox.pack_start(expander, False, True, 0)
        self.guestList = TextImageTree(add_icon)
        self.guestList.connect("activated", self.onAdd)
        self.guestList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0), False, False, 2)
        expander.add(self.guestList)

        self.channels = {}
        self.highlighted = {}

    def change_fg_colour(self, lc, cell, model, m_iter, data):
        """
        :Description: Changes the foreground colour of a cell

        :param lc: :class:`Gtk.TreeViewColumn` The column we are interested in
        :param cell: :class:`Gtk.CellRenderer` The cell we want to change
        :param model: :class:`Gtk.TreeModel`
        :param iter: :class:`Gtk.TreeIter`
        :param data: :py:class:`dict` (key=int,value=bool) value is true if channel already highlighted
        :return: None
        """

        for chan in data:
            if model[m_iter][0] == chan:
                if data[chan]:
                    cell.set_property('foreground_rgba',
                                      Gdk.RGBA(0.9, 0.2, 0.2, 1))
                else:
                    cell.set_property('foreground_rgba', Gdk.RGBA(0, 0, 0, 1))

    def channel_Highlight(self, a, channel, grp_type, b):
        """
        :Description: Highlights a channel ( that is **not** in focus ) that has received an update and
        changes it's foreground colour to represent change in contents

        :param a: not used
        :param channel: **(str)** The channel the message is intended for
        :param grp_type: either TYPE_CHANNEL or TYPE_PERSONAL
        :param b:  not used
        :return: None
        """
        j_list = self.joinedList
        leftcol = j_list.leftcol  # treeViewColumn

        cur_iter = j_list.get_selection().get_selected()[1]  # Selected iter
        if grp_type == TYPE_PERSONAL:
            channel = "person" + channel.lower()
        tmp_iter = j_list.id2iter[channel]
        tmp_iter = j_list.sort_model.convert_child_iter_to_iter(tmp_iter)[1]  # channel iter
        j_list.get_selection().select_iter(tmp_iter)
        cell = leftcol.get_cells()[0]
        j_list.get_selection().select_iter(cur_iter)
        self.highlighted[channel] = True
        if cur_iter != tmp_iter:
            # iter = tmp_iter
            leftcol.set_cell_data_func(cell,
                                       self.change_fg_colour,
                                       func_data=self.highlighted)

    def start(self):
        self.channels = self.connection.cm.getChannels()
        if self.channels:
            self._addChannels(self.channels)
        for player in list(self.connection.players.values()):
            grp_id = self.compileId(player.name, TYPE_PERSONAL)
            if str(player.name) in self.connection.notify_users:
                self.friendsList.addRow(
                    grp_id, player.name + player.display_titles(), TYPE_PERSONAL)
            elif player.online and ('(B)' in player.display_titles()):
                self.blindList.addRow(
                    grp_id, player.name + player.display_titles(), TYPE_BLINDFOLD)
            elif player.online and ('(C)' in player.display_titles()):
                self.compList.addRow(grp_id, player.name + player.display_titles(),
                                     TYPE_COMP)
            elif player.online and ('Guest' in str(player.name)):
                self.guestList.addRow(
                    grp_id, player.name + player.display_titles(), TYPE_GUEST)
            elif player.online:
                self.playersList.addRow(
                    grp_id, player.name + player.display_titles(), TYPE_PERSONAL)

        def addPlayer(players, new_players):
            for player in new_players:
                # print("Player : %s : %s" % (str(player.name),player.display_titles()))
                if str(player.name) in self.connection.notify_users:
                    self.friendsList.addRow(
                        self.compileId(player.name, TYPE_PERSONAL),
                        player.name + player.display_titles(), TYPE_PERSONAL)
                elif '(C)' in str(player.display_titles()):
                    self.compList.addRow(
                        self.compileId(player.name, TYPE_COMP),
                        player.name + player.display_titles(), TYPE_COMP)
                elif '(B)' in str(player.display_titles()):
                    self.blindList.addRow(
                        self.compileId(player.name, TYPE_BLINDFOLD),
                        player.name + player.display_titles(), TYPE_BLINDFOLD)
                elif 'Guest' in str(player.name):
                    self.guestList.addRow(
                        self.compileId(player.name, TYPE_GUEST),
                        player.name + player.display_titles(), TYPE_GUEST)
                else:
                    self.playersList.addRow(
                        self.compileId(player.name, TYPE_PERSONAL),
                        player.name + player.display_titles(), TYPE_PERSONAL)
            return False

        self.connection.players.connect("FICSPlayerEntered", addPlayer)

        def removePlayer(players, player):
            if (str(player.name) in list(self.connection.notify_users)):
                self.friendsList.removeRow(self.compileId(player.name,
                                                          TYPE_PERSONAL))
            else:
                self.playersList.removeRow(self.compileId(player.name,
                                                          TYPE_PERSONAL))
            return False

        self.connection.players.connect("FICSPlayerExited", removePlayer)

    def _addChannels(self, channels):
        for grp_id, name in channels:
            grp_id = self.compileId(grp_id, TYPE_CHANNEL)
            self.channelsList.addRow(grp_id, str(grp_id) + ": " + name, TYPE_CHANNEL)

        for grp_id, name in channels:
            if grp_id in self.connection.cm.getJoinedChannels():
                grp_id = self.compileId(grp_id, TYPE_CHANNEL)
                if grp_id.isdigit():
                    self.onAdd(self.channelsList, grp_id, str(grp_id) + ": " + name,
                               TYPE_CHANNEL)
                else:
                    self.onAdd(self.channelsList, grp_id, name, TYPE_CHANNEL)

    @idle_add
    def onChannelsListed(self, cm, channels):
        if not self.channels:
            self.channels = channels
            self._addChannels(channels)

    def compileId(self, grp_id, type):
        if type == TYPE_CHANNEL:
            # FIXME: We can't really add stuff to the grp_id, as panels use it to
            # identify the channel
            assert not grp_id.startswith("person"), "Oops, this is a problem"
        else:
            grp_id = "person" + grp_id.lower()
        return grp_id

    def onAdd(self, grp_list, grp_id, text, grp_type):
        if grp_id in grp_list:
            grp_list.removeRow(grp_id)
        self.joinedList.addRow(grp_id, text, grp_type)
        self.emit('conversationAdded', grp_id, text, grp_type)
        if grp_type == TYPE_CHANNEL:
            self.connection.cm.joinChannel(grp_id)
        self.joinedList.selectRow(grp_id)

    def onRemove(self, joined_list, grp_id, text, grp_type):
        joined_list.removeRow(grp_id)
        if grp_type == TYPE_CHANNEL:
            self.channelsList.addRow(grp_id, text, grp_type)
        elif grp_type == TYPE_PERSONAL:
            self.playersList.addRow(grp_id, text, grp_type)
        elif grp_type == TYPE_COMP:
            self.compList.addRow(grp_id, text, grp_type)
        elif grp_type == TYPE_ADMIN:
            self.adminList.addRow(grp_id, text, grp_type)
        elif grp_type == TYPE_GUEST:
            self.guestList.addRow(grp_id, text, grp_type)
        elif grp_type == TYPE_BLINDFOLD:
            self.blindList.addRow(grp_id, text, grp_type)

        self.emit('conversationRemoved', grp_id)
        if grp_type == TYPE_CHANNEL:
            self.connection.cm.removeChannel(grp_id)

    def onSelect(self, joined_list, grp_id, grp_type):
        self.emit('conversationSelected', grp_id)
        joined_list.get_selection().get_selected()[1]  # Selected iter
        cell = joined_list.leftcol.get_cells()[0]
        self.highlighted[grp_id] = False
        joined_list.leftcol.set_cell_data_func(cell,
                                               self.change_fg_colour,
                                               func_data=self.highlighted)

    @idle_add
    def onPersonMessage(self, cm, name, title, isadmin, text):
        if not self.compileId(name, TYPE_PERSONAL) in self.joinedList:
            grp_id = self.compileId(name, TYPE_PERSONAL)
            self.onAdd(self.playersList, grp_id, name, TYPE_PERSONAL)

# ===============================================================================
# /Panels
# ===============================================================================


class ChatWindow(object):
    def __init__(self, widgets, connection):
        self.connection = connection
        self.window = None

        widgets["show_chat_button"].connect("clicked", self.showChat)
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.connect("disconnected", self.onDisconnected)

        self.viewspanel = ViewsPanel(self.connection)
        self.channelspanel = ChannelsPanel(self.connection)
        self.infopanel = InfoPanel(self.connection)
        self.panels = [self.viewspanel, self.channelspanel, self.infopanel]
        self.viewspanel.connect('channel_content_Changed',
                                self.channelspanel.channel_Highlight, id)

    @idle_add
    def onDisconnected(self, conn):
        if self.window:
            self.window.hide()

    def showChat(self, *widget):
        if not self.window:
            self.initUi()
        self.window.show_all()
        self.window.present()

    def initUi(self):
        self.window = Gtk.Window()
        self.window.set_border_width(12)
        self.window.set_icon_name("pychess")
        self.window.set_title("PyChess - Internet Chess Chat")
        self.window.connect_after("delete-event",
                                  lambda w, e: w.hide() or True)

        uistuff.keepWindowSize("chat", self.window, defaultSize=(650, 400))

        self.dock = PyDockTop("icchat")
        self.dock.show()
        self.window.add(self.dock)

        leaf = self.dock.dock(self.viewspanel,
                         CENTER,
                         Gtk.Label(label="chat"),
                         "chat")
        leaf.setDockable(False)

        self.channelspanel.connect('conversationAdded',
                                   self.onConversationAdded)
        self.channelspanel.connect('conversationRemoved',
                                   self.onConversationRemoved)
        self.channelspanel.connect('conversationSelected',
                                   self.onConversationSelected)
        leaf.dock(self.channelspanel,
                  WEST,
                  Gtk.Label(label=_("Conversations")),
                  "conversations")

        leaf.dock(self.infopanel,
                  EAST,
                  Gtk.Label(label=_("Conversation info")),
                  "info")

        for panel in self.panels:
            panel.show_all()
            panel.start()

    def onConversationAdded(self, panel, grp_id, text, grp_type):
        chatView = ChatView()
        plus_channel = '+channel ' + str(grp_id)
        self.connection.cm.connection.client.run_command(plus_channel)
        for panel in self.panels:
            panel.addItem(grp_id, text, grp_type, chatView)

    def onConversationRemoved(self, panel, grp_id):
        minus_channel = '-channel ' + str(grp_id)
        self.connection.cm.connection.client.run_command(minus_channel)
        for panel in self.panels:
            panel.removeItem(grp_id)

    def onConversationSelected(self, panel, grp_id):
        for panel in self.panels:
            panel.selectItem(grp_id)

    @idle_add
    def onPersonMessage(self, cm, name, title, isadmin, text):
        console_active = False
        for window in Gtk.Window.list_toplevels():
            if window.is_active():
                window_icon_name = window.get_icon_name()
                if window_icon_name is not None and "pychess" in window_icon_name:
                    console_active = True
                    break

        if self.connection.bm.isPlaying() or console_active:
            if not self.window:
                self.initUi()
        else:
            self.showChat()
            self.window.set_urgency_hint(True)
            self.initial_focus_id = self.window.connect(
                "focus-in-event", self.on_initial_focus_in)

    def on_initial_focus_in(self, widget, event):
        self.window.set_urgency_hint(False)
        self.window.disconnect(self.initial_focus_id)
        return False

    def openChatWithPlayer(self, name):
        self.showChat()
        self.window.get_window().raise_()
        cm = self.connection.cm
        self.onPersonMessage(cm, name, "", False, "")
        self.channelspanel.onPersonMessage(cm, name, "", False, "")


if __name__ == "__main__":
    import random

    class LM:
        def getPlayerlist(self):
            for i in range(10):
                chrs = map(chr, range(ord("a"), ord("z") + 1))
                yield "".join(random.sample(chrs, random.randrange(20)))

        def getChannels(self):
            return [(str(i), n) for i, n in enumerate(self.getPlayerlist())]

        def joinChannel(self, channel):
            pass

        def connect(self, *args):
            pass

        def getPeopleInChannel(self, name):
            pass

        def finger(self, name):
            pass

        def getJoinedChannels(self):
            return []

    class Con:
        def __init__(self):
            self.glm = LM()
            self.cm = LM()
            self.fm = LM()

    cw = ChatWindow({}, Con())
    globals()["_"] = lambda x: x
    cw.showChat()
    cw.window.connect("delete-event", Gtk.main_quit)
    Gtk.main()
