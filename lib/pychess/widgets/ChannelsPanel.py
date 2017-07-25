from gi.repository import Gtk, GObject, Gdk, Pango

from pychess.Utils.IconLoader import load_icon
from pychess.widgets.InfoPanel import Panel

TYPE_PERSONAL, TYPE_CHANNEL, TYPE_GUEST, \
    TYPE_ADMIN, TYPE_COMP, TYPE_BLINDFOLD = range(6)

add_icon = load_icon(16, "gtk-add", "list-add")
remove_icon = load_icon(16, "gtk-remove", "list-remove")


def cmp(x, y):
    return (x > y) - (x < y)


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
        crp = Gtk.CellRendererPixbuf()
        crp.props.pixbuf = icon
        self.rightcol = Gtk.TreeViewColumn("", crp)
        self.append_column(self.rightcol)

        # Second column
        crt = Gtk.CellRendererText()
        crt.props.ellipsize = Pango.EllipsizeMode.END
        self.leftcol = Gtk.TreeViewColumn("", crt, text=1)
        self.leftcol.set_expand(True)
        self.append_column(self.leftcol)

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

    def onPersonMessage(self, cm, name, title, isadmin, text):
        if not self.compileId(name, TYPE_PERSONAL) in self.joinedList:
            grp_id = self.compileId(name, TYPE_PERSONAL)
            self.onAdd(self.playersList, grp_id, name, TYPE_PERSONAL)
