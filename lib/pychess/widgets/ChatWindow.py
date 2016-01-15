import re

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango

from pychess.compat import cmp
from pychess.Utils.IconLoader import load_icon
from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.widgets.ChatView import ChatView
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import NORTH, EAST, SOUTH, WEST, CENTER

TYPE_PERSONAL, TYPE_CHANNEL , TYPE_GUEST , TYPE_ADMIN , TYPE_COMP , TYPE_BLINDFOLD = range(6)

def get_playername (playername):
    m = re.match("(\w+)\W*", playername)
    return m.groups()[0]

class BulletCellRenderer (Gtk.CellRenderer):
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
        if not self.color: return

        x, y = self.get_size(widget, cell_area)[:2]

        r,g,b = self.color
        context.set_source_rgb (r,g,b)
        context.rectangle (x, y, self.width, self.height)
        context.fill()

        context.set_line_width (1)
        context.set_source_rgba (0, 0, 0, 0.5)
        context.rectangle (x+0.5, y+0.5, self.width-1, self.height-1)
        context.stroke ()

        context.set_line_width (1)
        context.set_source_rgba (1, 1, 1, 0.5)
        context.rectangle (x+1.5, y+1.5, self.width-3, self.height-3)
        context.stroke ()

    def on_get_size(self, widget, cell_area=None):
        if cell_area:
            y = int(cell_area.height/2.-self.height/2.) + cell_area.y
            x = cell_area.x
        else:
            y = 0
            x = 0
        return (x+1, y+1, self.width+2, self.height+2)

GObject.type_register(BulletCellRenderer)


add_icon = load_icon(16, "gtk-add", "list-add")
remove_icon = load_icon(16, "gtk-remove", "list-remove")

class TextImageTree (Gtk.TreeView):
    """ Defines a tree with two columns.
        The first one has text. The second one a clickable stock_icon """

    __gsignals__ = {
        'activated' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,int)),
        'selected' : (GObject.SignalFlags.RUN_FIRST, None, (str,int))
    }

    def __init__(self, icon):
        GObject.GObject.__init__(self)
        self.id2iter = {}

        pm = Gtk.ListStore(str,str,int,str)
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
    def addRow (self, id, text, type):
        if id in self.id2iter: return
        model = self.sort_model.get_model()
        iter = model.append([id, text , type, GObject.markup_escape_text(text)])
        self.id2iter[id] = iter
        self.idSet.add(id)

    @idle_add
    def removeRow (self, id):
        try:
            iter = self.id2iter[id]
        except KeyError:
            return
        model = self.sort_model.get_model()
        model.remove(iter)
        del self.id2iter[id]
        self.idSet.remove(id)

    @idle_add
    def selectRow (self, id):
        iter = self.id2iter[id]
        iter = self.sort_model.convert_child_iter_to_iter(iter)[1]
        sel = self.get_selection()
        sel.select_iter(iter)

    def __contains__ (self, id):
        return id in self.idSet

    def button_press (self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            self.pressed = path_col_pos[0]

    def button_release (self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            if self.pressed == path_col_pos[0]:
                model = self.sort_model
                iter = model.get_iter(self.pressed)
                id = model.get_value(iter, 0)
                text = model.get_value(iter, 1)
                type = model.get_value(iter, 2)
                self.emit("activated", id, text, type)
        self.pressed = None

    def motion_notify (self, widget, event):
        path_col_pos = self.get_path_at_pos(int(event.x), int(event.y))
        if path_col_pos and path_col_pos[1] == self.rightcol:
            self.get_window().set_cursor(self.linkcursor)
        else:
            self.get_window().set_cursor(self.stdcursor)

    def leave_notify (self, widget, event):
        self.get_window().set_cursor(self.stdcursor)

    def selection_changed (self, selection):
        model, iter = selection.get_selected()
        if iter:
            id = model.get_value(iter, 0)
            type = model.get_value(iter, 2)
            self.emit("selected", id, type)

    def compareFunction (self, treemodel, iter0, iter1, column):
        val0 = treemodel.get_value(iter0, column).split(":")[0]
        val1 = treemodel.get_value(iter1, column).split(":")[0]
        if val0.isdigit() and val1.isdigit():
            return cmp(int(val0), int(val1))
        return cmp(val0, val1)


class Panel (object):
    def start (self): pass
    def addItem (self, id, text, type, chatView): pass
    def removeItem (self, id): pass
    def selectItem (self, id): pass

#===============================================================================
# Panels
#===============================================================================

class ViewsPanel (Gtk.Notebook, Panel):

    __gsignals__ = {
        'channel_content_Changed' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }


    def __init__ (self, connection):
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
        def globalPersonalMessage (cm, name, title, isadmin, text):
            if not name in self.messageBuffer:
                self.messageBuffer[name] = []
            self.messageBuffer[name].append((title, isadmin, text))
        self.connection.cm.connect("privateMessage", globalPersonalMessage)

    def addItem (self, id, name, type, chatView):
        chatView.connect("messageTyped", self.onMessageTyped, id, name, type)
        self.connection.cm.connect("channelMessage",
                      self.onChannelMessage, id, chatView)
        self.connection.cm.connect("privateMessage",
                      self.onPersonMessage, get_playername(name), chatView)

        if type == TYPE_CHANNEL:
            self.connection.cm.connect("channelLog",
                          self.onChannelLog, id, chatView)
            self.connection.cm.getChannelLog(id)
            if not self.connection.cm.mayTellChannel(id):
                chatView.disable(_("Only registered users may talk to this channel"))

        elif type in (TYPE_PERSONAL,TYPE_COMP,TYPE_GUEST,TYPE_ADMIN,TYPE_BLINDFOLD):
            if name in self.messageBuffer:
                for title, isadmin, messagetext in self.messageBuffer[name]:
                    chatView.addMessage(name, messagetext)
                del self.messageBuffer[name]

        self.addPage(chatView, id)

    def removeItem (self, id):
        self.removePage(id)

    def selectItem (self, id):
        child = self.id2Widget[id]
        self.set_current_page(self.page_num(child))


    def onChannelLog (self, cm, channel, time, handle, text, name_, chatView):
        if channel.lower() == name_.lower():
            chatView.insertLogMessage(time, handle, text)

    def onMessageTyped (self, chatView, text, id, name, type):
        if type == TYPE_CHANNEL:
            self.connection.cm.tellChannel(id, text)
        elif type == TYPE_PERSONAL:
            self.connection.cm.tellPlayer(get_playername(name), text)
        chatView.addMessage(self.connection.getUsername(), text)

    def onPersonMessage (self, cm, name, title, isadmin, text, name_, chatView):
        if name.lower() == name_.lower():
            chatView.addMessage(name, text)
            self.emit('channel_content_Changed',name_)

    def onChannelMessage (self, cm, name, isadmin, isme, channel, text, name_, chatView):
        if channel.lower() == name_.lower() and not isme:
            chatView.addMessage(name, text)
            self.emit('channel_content_Changed',channel)


    def addPage (self, widget, id):
        self.id2Widget[id] = widget
        self.append_page(widget, None)
        widget.show_all()

    def removePage (self, id):
        child = self.id2Widget.pop(id)
        self.remove_page(self.page_num(child))


class InfoPanel (Gtk.Notebook, Panel):
    def __init__ (self, connection):
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

    def addItem (self, id, text, type, chatView):
        if type in (TYPE_PERSONAL,TYPE_COMP,TYPE_GUEST,TYPE_ADMIN,TYPE_BLINDFOLD):
            infoItem = self.PlayerInfoItem(id, text, chatView, self.connection)
        elif type == TYPE_CHANNEL:
            infoItem = self.ChannelInfoItem(id, text, chatView, self.connection)
        self.addPage(infoItem, id)

    def removeItem (self, id):
        self.removePage(id)

    def selectItem (self, id):
        child = self.id2Widget.get(id)
        if child is not None:
            self.set_current_page(self.page_num(child))


    def addPage (self, widget, id):
        self.id2Widget[id] = widget
        self.append_page(widget, None)
        widget.show_all()

    def removePage (self, id):
        child = self.id2Widget.pop(id)
        self.remove_page(self.page_num(child))

    class PlayerInfoItem (Gtk.Alignment):
        def __init__ (self, id, text, chatView, connection):
            GObject.GObject.__init__(self, xscale=1, yscale=1)
            self.add(Gtk.Label(label=_("Loading player data")))

            playername = get_playername(text)
            self.fm = connection.fm
            self.handle_id = self.fm.connect("fingeringFinished",
                                           self.onFingeringFinished, playername)

            self.fm.finger(playername)


        @idle_add
        def onFingeringFinished (self, fm, finger, playername):
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

            tv = Gtk.TextView()
            tv.set_editable(False)
            tv.set_cursor_visible(False)
            tv.props.wrap_mode = Gtk.WrapMode.WORD

            tb = tv.get_buffer()
            iter = tb.get_end_iter()
            for i, note in enumerate(finger.getNotes()):
                if note:
                    tb.insert(iter, "%s: %s\n" % (i+1, note))
            tv.show_all()
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            sw.add(tv)
            alignment.add(sw)

            self.remove(self.get_child())
            self.add(widget)
            widget.show_all()

    class ChannelInfoItem (Gtk.Alignment):
        def __init__ (self, id, text, chatView, connection):
            GObject.GObject.__init__(self, xscale=1, yscale=1)
            self.cm = connection.cm
            self.add(Gtk.Label(label=_("Receiving list of players")))

            self.names = set()
            chatView.connect("messageAdded", self.onMessageAdded)
            self.store = Gtk.ListStore(object, # (r,g,b) Color tuple
                                       str,    # name string
                                       bool    # is separator
                                       )

            connection.players.connect("FICSPlayerExited", self.onPlayerRemoved)

            self.handle_id = self.cm.connect("receivedNames",
                                           self.onNamesReceived, id)
            self.cm.getPeopleInChannel(id)

        @idle_add
        def onPlayerRemoved (self, players, player):
            if player.name in self.names:
                for row in self.store:
                    if row[1] == player.name:
                        self.store.remove(row.iter)
                        break
                self.names.remove(player.name)

        @idle_add
        def onNamesReceived (self, cm, channel, people, channel_):
            if not isinstance(self.get_child(), Gtk.Label) or channel != channel_:
                return
            cm.disconnect(self.handle_id)

            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            list = Gtk.TreeView()
            list.set_headers_visible(False)
            list.set_tooltip_column(1)
            list.set_model(self.store)
            list.append_column(Gtk.TreeViewColumn("", BulletCellRenderer(), color=0))
            cell = Gtk.CellRendererText()
            cell.props.ellipsize = Pango.EllipsizeMode.END
            list.append_column(Gtk.TreeViewColumn("", cell, text=1))
            list.fixed_height_mode = True

            self.separatorIter = self.store.append([(),"",True])

            list.set_row_separator_func(lambda m,i,d: m.get_value(i, 2), None)
            sw.add(list)

            self.store.connect("row-inserted", lambda w,p,i: list.queue_resize())
            self.store.connect("row-deleted", lambda w,i: list.queue_resize())

            # Add those names. If this is not the first namesReceive, we only
            # add the new names
            noneed = set([name for (color, name, isSeparator) in self.store])
            for name in people:
                if name in noneed: continue
                self.store.append([(1,1,1), name, False])
                self.names.add(name)

            self.remove(self.get_child())
            self.add(sw)
            self.show_all()

        @idle_add
        def onMessageAdded (self, chatView, sender, text, color):
            iter = self.store.get_iter_first()

            # If the names list hasn't been retrieved yet, we have to skip this
            if not iter:
                return

            while self.store.get_path(iter) != self.store.get_path(self.separatorIter):
                person = self.store.get_value(iter, 1)
                # If the person is already in the area before the separator, we
                # don't have to do anything
                if person.lower() == sender.lower():
                    return
                iter = self.store.iter_next(iter)

            # Go to iter after separator
            iter = self.store.iter_next(iter)

            while iter and self.store.iter_is_valid(iter):
                person = self.store.get_value(iter, 1)
                if person.lower() == sender.lower():
                    self.store.set_value(iter, 0, color)
                    self.store.move_before(iter, self.separatorIter)
                    return
                iter = self.store.iter_next(iter)

            # If the person was not in the area under the separator of the
            # store, it must be a new person, who has joined the channel, and we
            # simply add him before the separator
            self.store.insert_before(self.separatorIter, [color, sender, False])

class ChannelsPanel (Gtk.ScrolledWindow, Panel):

    __gsignals__ = {
        'conversationAdded' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,int)),
        'conversationRemoved' : (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'conversationSelected' : (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__ (self, connection):
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

        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander = Gtk.Expander.new(_("Friends"))
        vbox.pack_start(expander, False, True, 0)
        self.friendsList = TextImageTree(add_icon)
        self.friendsList.connect("activated", self.onAdd)
        self.friendsList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.friendsList)
        self.channels = {}

        expander = Gtk.Expander.new(_("Admin"))
        vbox.pack_start(expander, False, True, 0)
        self.adminList = TextImageTree(add_icon)
        self.adminList.connect("activated", self.onAdd)
        self.adminList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.adminList)


        expander = Gtk.Expander.new(_("More channels"))
        vbox.pack_start(expander, False, True, 0)
        self.channelsList = TextImageTree(add_icon)
        self.channelsList.connect("activated", self.onAdd)
        self.channelsList.fixed_height_mode = True
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.channelsList)

        expander = Gtk.Expander.new(_("More players"))
        vbox.pack_start(expander, False, True, 0)
        self.playersList = TextImageTree(add_icon)
        self.playersList.connect("activated", self.onAdd)
        self.playersList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.playersList)

        expander = Gtk.Expander.new(_("Computers"))
        vbox.pack_start(expander, False, True, 0)
        self.compList = TextImageTree(add_icon)
        self.compList.connect("activated", self.onAdd)
        self.compList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.compList)

        expander = Gtk.Expander.new(_("BlindFold"))
        vbox.pack_start(expander, False, True, 0)
        self.blindList = TextImageTree(add_icon)
        self.blindList.connect("activated", self.onAdd)
        self.blindList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.blindList)

        expander = Gtk.Expander.new(_("Guests"))
        vbox.pack_start(expander, False, True, 0)
        self.guestList = TextImageTree(add_icon)
        self.guestList.connect("activated", self.onAdd)
        self.guestList.fixed_height_mode = True
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.cm.connect("channelsListed", self.onChannelsListed)
        vbox.pack_start(Gtk.Separator.new(0),False,False,2)
        expander.add(self.guestList)

        self.channels = {}
        self.highlighted = {}

    def change_fg_colour(self,lc, cell ,model, iter,data):
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
            if model[iter][0] == chan:
                if data[chan] :
                    cell.set_property('foreground_rgba',Gdk.RGBA(0.8,0.3,0.3,1))
                else:
                    cell.set_property('foreground_rgba',Gdk.RGBA(0,0,0,1))


    def channel_Highlight(self, a, channel, b):
        """
        :Description: Highlights a channel ( that is **not** in focus ) that has received an update and
        changes it's foreground colour to represent change in contents

        :param a: not used
        :param channel: **(str)** The channel the message is intended for
        :param b:  not used
        :return: None
        """
        chan_ref = re.compile('^[\dCS]h*[eo]*[su]*[st]*') # reg-exp to determine channel or person

        jList = self.joinedList
        lc = jList.leftcol      # treeViewColumn

        model , cur_iter = jList.get_selection().get_selected() #Selected iter
        if ((not chan_ref.search(channel)) or len(channel) > 5 ): # len() required for names begining with 'Shout' or 'Chess'
            channel = "person" + channel.lower()
        temp_iter = jList.id2iter[channel]
        temp_iter = jList.sort_model.convert_child_iter_to_iter(temp_iter)[1] #channel iter
        jList.get_selection().select_iter(temp_iter)
        cell = lc.get_cells()[0]
        jList.get_selection().select_iter(cur_iter)
        self.highlighted[channel] = True
        if cur_iter != temp_iter :
            iter = temp_iter
            lc.set_cell_data_func(cell,self.change_fg_colour,func_data=self.highlighted)

    def start (self):
        self.channels = self.connection.cm.getChannels()
        if self.channels:
            self._addChannels(self.channels)
        for player in list(self.connection.players.values()):
            id = self.compileId(player.name, TYPE_PERSONAL)
            if (str(player.name) in self.connection.notify_users):
                self.friendsList.addRow(id, player.name + player.display_titles(),TYPE_PERSONAL)
            elif  ((player.online) and ('(B)' in player.display_titles())):
                self.blindList.addRow(id, player.name + player.display_titles(),TYPE_BLINDFOLD)
            elif  ((player.online) and ('(C)' in player.display_titles())):
                self.compList.addRow(id, player.name + player.display_titles(),TYPE_COMP)
            elif  ((player.online) and ('Guest' in str(player.name))):
                self.guestList.addRow(id, player.name + player.display_titles(),TYPE_GUEST)
            elif  player.online :
                self.playersList.addRow(id, player.name + player.display_titles(),TYPE_PERSONAL)




        def addPlayer (players, new_players):
            for player in new_players:
                #print("Player : %s : %s" % (str(player.name),player.display_titles()))
                if (str(player.name) in self.connection.notify_users):
                    self.friendsList.addRow(self.compileId(player.name, TYPE_PERSONAL),
                        player.name + player.display_titles(), TYPE_PERSONAL)
                elif '(C)' in  str(player.display_titles()):
                    self.compList.addRow(self.compileId(player.name, TYPE_COMP),
                        player.name + player.display_titles(), TYPE_COMP)
                elif '(B)' in  str(player.display_titles()):
                    self.blindList.addRow(self.compileId(player.name, TYPE_BLINDFOLD),
                        player.name + player.display_titles(), TYPE_BLINDFOLD)
                elif 'Guest' in  str(player.name):
                    self.guestList.addRow(self.compileId(player.name, TYPE_GUEST),
                        player.name + player.display_titles(), TYPE_GUEST)
                else:
                    self.playersList.addRow(self.compileId(player.name, TYPE_PERSONAL),
                        player.name + player.display_titles(), TYPE_PERSONAL)
            return False
        self.connection.players.connect("FICSPlayerEntered", addPlayer)

        def removePlayer (players, player):
            if (str(player.name) in list(self.connection.notify_users)):
                self.friendsList.removeRow(self.compileId(player.name, TYPE_PERSONAL))
            else:
                self.playersList.removeRow(self.compileId(player.name, TYPE_PERSONAL))
            return False
        self.connection.players.connect("FICSPlayerExited", removePlayer)

    def _addChannels (self, channels):
        for id, name in channels:
            id = self.compileId(id, TYPE_CHANNEL)
            self.channelsList.addRow(id, str(id) + ": " + name, TYPE_CHANNEL)

        for id, name in channels:
            if id in self.connection.cm.getJoinedChannels():
                id = self.compileId(id, TYPE_CHANNEL)
                if id.isdigit():
                    self.onAdd(self.channelsList, id, str(id)+": "+name, TYPE_CHANNEL)
                else:
                    self.onAdd(self.channelsList, id, name, TYPE_CHANNEL)

    @idle_add
    def onChannelsListed (self, cm, channels):
        if not self.channels:
            self.channels = channels
            self._addChannels(channels)

    def compileId (self, id, type):
        if type == TYPE_CHANNEL:
            # FIXME: We can't really add stuff to the id, as panels use it to
            # identify the channel
            assert not id.startswith("person"), "Oops, this is a problem"
        else:
            id = "person" + id.lower()
        return id

    def onAdd (self, list, id, text, type):
        if id in list:
            list.removeRow(id)
        self.joinedList.addRow(id, text, type)
        self.emit('conversationAdded', id, text, type)
        if type == TYPE_CHANNEL:
            self.connection.cm.joinChannel(id)
        self.joinedList.selectRow(id)

    def onRemove (self, joinedList, id, text, type):
        joinedList.removeRow(id)
        if type == TYPE_CHANNEL:
            self.channelsList.addRow(id, text, type)
        elif type == TYPE_PERSONAL:
            self.playersList.addRow(id, text, type)
        elif type == TYPE_COMP:
            self.compList.addRow(id, text, type)
        elif type == TYPE_ADMIN:
            self.adminList.addRow(id, text, type)
        elif type == TYPE_GUEST:
            self.guestList.addRow(id, text, type)
        elif type == TYPE_BLINDFOLD:
            self.blindList.addRow(id, text, type)

        self.emit('conversationRemoved', id)
        if type == TYPE_CHANNEL:
            self.connection.cm.removeChannel(id)

    def onSelect (self, joinedList, id, type):
        self.emit('conversationSelected', id)
        model , iter = joinedList.get_selection().get_selected() #Selected iter
        cell = joinedList.leftcol.get_cells()[0]
        self.highlighted[id] = False
        joinedList.leftcol.set_cell_data_func(cell,self.change_fg_colour,func_data=self.highlighted)

    @idle_add
    def onPersonMessage (self, cm, name, title, isadmin, text):
        if not self.compileId(name, TYPE_PERSONAL) in self.joinedList:
            id = self.compileId(name, TYPE_PERSONAL)
            self.onAdd(self.playersList, id, name, TYPE_PERSONAL)

#===============================================================================
# /Panels
#===============================================================================

class ChatWindow (object):
    def __init__ (self, widgets, connection):
        self.connection = connection
        self.window = None

        widgets["show_chat_button"].connect("clicked", self.showChat)
        connection.cm.connect("privateMessage", self.onPersonMessage)
        connection.connect("disconnected", self.onDisconnected)

        self.viewspanel = ViewsPanel(self.connection)
        self.channelspanel = ChannelsPanel(self.connection)
        self.infopanel = InfoPanel(self.connection)
        self.panels = [self.viewspanel, self.channelspanel, self.infopanel]
        self.viewspanel.connect('channel_content_Changed', self.channelspanel.channel_Highlight,id)

    @idle_add
    def onDisconnected(self, conn):
        if self.window:
            self.window.hide()

    def showChat (self, *widget):
        if not self.window:
            self.initUi()
        self.window.show_all()
        self.window.present()

    def initUi (self):
        self.window = Gtk.Window()
        self.window.set_border_width(12)
        self.window.set_icon_name("pychess")
        self.window.set_title("PyChess - Internet Chess Chat")
        self.window.connect("delete-event", lambda w,e: w.hide() or True)

        uistuff.keepWindowSize("chatwindow", self.window, defaultSize=(650,400))

        dock = PyDockTop("icchat")
        dock.show()
        self.window.add(dock)

        leaf = dock.dock(self.viewspanel, CENTER, Gtk.Label(label="chat"), "chat")
        leaf.setDockable(False)

        self.channelspanel.connect('conversationAdded', self.onConversationAdded)
        self.channelspanel.connect('conversationRemoved', self.onConversationRemoved)
        self.channelspanel.connect('conversationSelected', self.onConversationSelected)
        leaf.dock(self.channelspanel, WEST, Gtk.Label(label=_("Conversations")), "conversations")

        leaf.dock(self.infopanel, EAST, Gtk.Label(label=_("Conversation info")), "info")

        for panel in self.panels:
            panel.show_all()
            panel.start()

    def onConversationAdded (self, panel, id, text, type):
        chatView = ChatView()
        for panel in self.panels:
            panel.addItem(id, text, type, chatView)

    def onConversationRemoved (self, panel, id):
        for panel in self.panels:
            panel.removeItem(id)

    def onConversationSelected (self, panel, id):
        for panel in self.panels:
            panel.selectItem(id)

    @idle_add
    def onPersonMessage (self, cm, name, title, isadmin, text):
        console_active = False
        for window in Gtk.Window.list_toplevels():
            if window.is_active() and "pychess" in window.get_icon_name():
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

    def openChatWithPlayer (self, name):
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
                chrs = map(chr,range(ord("a"),ord("z")+1))
                yield "".join(random.sample(chrs, random.randrange(20)))
        def getChannels(self):
            return [(str(i),n) for i,n in enumerate(self.getPlayerlist())]
        def joinChannel (self, channel):
            pass
        def connect (self, *args): pass
        def getPeopleInChannel (self, name): pass
        def finger (self, name): pass
        def getJoinedChannels (self): return []
    class Con:
        def __init__ (self):
            self.glm = LM()
            self.cm = LM()
            self.fm = LM()
    cw = ChatWindow({}, Con())
    globals()["_"] = lambda x:x
    cw.showChat()
    cw.window.connect("delete-event", Gtk.main_quit)
    Gtk.main()
