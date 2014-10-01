from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
import re

from pychess.Utils.IconLoader import load_icon
from pychess.System import uistuff
from pychess.System import glock
from pychess.System.glock import glock_connect
from pychess.widgets.ChatView import ChatView
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import NORTH, EAST, SOUTH, WEST, CENTER

TYPE_PERSONAL, TYPE_CHANNEL = range(2)

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

class TextImageTree (Gtk.TreeView):
    """ Defines a tree with two columns.
        The first one has text. The seccond one a clickable stock_icon """
    
    __gsignals__ = {
        'activated' : (GObject.SignalFlags.RUN_FIRST, None, (str,str,int)),
        'selected' : (GObject.SignalFlags.RUN_FIRST, None, (str,int))
    }
    
    def __init__(self, icon_name):
        GObject.GObject.__init__(self)
        self.id2iter = {}
        
        self.icon_name = icon_name
        pm = Gtk.ListStore(str,str,int)
        self.props.model = pm
        self.idSet = set()
        
        self.set_headers_visible(False)
        self.set_tooltip_column(1)
        self.set_search_column(1)
        
        # First column
        crt = Gtk.CellRendererText()
        crt.props.ellipsize = Pango.EllipsizeMode.END
        self.leftcol = Gtk.TreeViewColumn("", crt, text=1)
        self.leftcol.set_expand(True)
        self.append_column(self.leftcol)
        
        # Second column
        pixbuf = load_icon(16, icon_name)
        crp = Gtk.CellRendererPixbuf()
        crp.props.pixbuf = pixbuf
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
    
    def addRow (self, id, text, type):
        if id in self.id2iter: return
        with glock.glock:
            iter = self.props.model.append([id, text, type])
        self.id2iter[id] = iter
        self.idSet.add(id)
    
    def removeRow (self, id):
        try:
            iter = self.id2iter[id]
        except KeyError:
            return
        with glock.glock:
            self.props.model.remove(iter)
        del self.id2iter[id]
        self.idSet.remove(id)
    
    def selectRow (self, id):
        iter = self.id2iter[id]
        self.get_selection().select_iter(iter)
    
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
                iter = self.props.model.get_iter(self.pressed)
                id = self.props.model.get_value(iter, 0)
                text = self.props.model.get_value(iter, 1)
                type = self.props.model.get_value(iter, 2)
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

class Panel (object):
    def start (self): pass
    def addItem (self, id, text, type, chatView): pass
    def removeItem (self, id): pass
    def selectItem (self, id): pass

#===============================================================================
# Panels
#===============================================================================

class ViewsPanel (Gtk.Notebook, Panel):
    
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
        # add new items, we test if anything was already recieved
        self.messageBuffer = {}
        def globalPersonalMessage (cm, name, title, isadmin, text):
            if not name in self.messageBuffer:
                self.messageBuffer[name] = []
            self.messageBuffer[name].append((title, isadmin, text))
        self.connection.cm.connect("privateMessage", globalPersonalMessage)
    
    def addItem (self, id, name, type, chatView):
        chatView.connect("messageTyped", self.onMessageTyped, id, name, type)
        glock_connect(self.connection.cm, "channelMessage",
                      self.onChannelMessage, id, chatView)
        glock_connect(self.connection.cm, "privateMessage",
                      self.onPersonMessage, get_playername(name), chatView)
        
        if type == TYPE_CHANNEL:
            glock_connect(self.connection.cm, "channelLog",
                          self.onChannelLog, id, chatView)
            self.connection.cm.getChannelLog(id)
            if not self.connection.cm.mayTellChannel(id):
                chatView.disable(_("Only registered users may talk to this channel"))
        
        elif type == TYPE_PERSONAL:
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
    
    def onChannelMessage (self, cm, name, isadmin, isme, channel, text, name_, chatView):
        if channel.lower() == name_.lower() and not isme:
            chatView.addMessage(name, text)
    
    
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
        if type == TYPE_PERSONAL:
            infoItem = self.PlayerInfoItem(id, text, chatView, self.connection)
        elif type == TYPE_CHANNEL:
            infoItem = self.ChannelInfoItem(id, text, chatView, self.connection)
        self.addPage(infoItem, id)
    
    def removeItem (self, id): 
        self.removePage(id)
    
    def selectItem (self, id):
        child = self.id2Widget[id] 
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
            self.handle_id = glock_connect(self.fm, "fingeringFinished",
                                           self.onFingeringFinished, playername)
            
            self.fm.finger(playername)
        
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
            
            store = Gtk.ListStore(str,str)
            for i, note in enumerate(finger.getNotes()):
                if note:
                    store.append([str(i+1),note])
            tv = Gtk.TreeView(store)
            tv.get_selection().set_mode(Gtk.SelectionMode.NONE)
            tv.set_headers_visible(False)
            
            sc = tv.get_style_context()
            bool1, bg_color = sc.lookup_color("p_bg_color")
            bool1, bg_active = sc.lookup_color("p_bg_active")
            tv.override_background_color(Gtk.StateFlags.NORMAL, bg_color)

            cell = Gtk.CellRendererText()
            cell.props.background_rgba = bg_active

            cell.props.cell_background_set = True 
            cell.props.yalign = 0
            tv.append_column(Gtk.TreeViewColumn("", cell, text=0))
            cell = uistuff.appendAutowrapColumn(tv, 50, "Notes", text=1)
            cell.props.background_rgba = bg_color
            cell.props.cell_background_set = True 
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
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
            
            chatView.connect("messageAdded", self.onMessageAdded)
            self.store = Gtk.ListStore(object, # (r,g,b) Color tuple
                                       str,    # name string
                                       bool    # is separator
                                       )
            
            self.handle_id = glock_connect(self.cm, "recievedNames",
                                           self.onNamesRecieved, id)
            self.cm.getPeopleInChannel(id)
        
        def onNamesRecieved (self, cm, channel, people, channel_):
            if not isinstance(self.get_child(), Gtk.Label) or channel != channel_:
                return
            cm.disconnect(self.handle_id)
            
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            
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
            
            # Add those names. If this is not the first namesRecieve, we only
            # add the new names
            noneed = set([name for color, name, isSeparator in self.store])
            for name in people:
                if name in noneed: continue
                self.store.append([(1,1,1), name, False])
            
            self.remove(self.get_child())
            self.add(sw)
            self.show_all()
        
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
        
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox = Gtk.VBox()
        self.add_with_viewport(vbox)
        self.get_child().set_shadow_type(Gtk.ShadowType.NONE)
        
        self.joinedList = TextImageTree("gtk-remove")
        self.joinedList.connect("activated", self.onRemove)
        self.joinedList.connect("selected", self.onSelect)
        vbox.pack_start(self.joinedList, True, True, 0)
        
        expander = Gtk.Expander.new(_("More channels"))
        vbox.pack_start(expander, False, True, 0)
        self.channelsList = TextImageTree("gtk-add")
        self.channelsList.connect("activated", self.onAdd)
        self.channelsList.fixed_height_mode = True
        expander.add(self.channelsList)
        
        expander = Gtk.Expander.new(_("More players"))
        vbox.pack_start(expander, False, True, 0)
        self.playersList = TextImageTree("gtk-add")
        self.playersList.connect("activated", self.onAdd)
        self.playersList.fixed_height_mode = True
        glock_connect(connection.cm, "privateMessage", self.onPersonMessage, after=True)
        glock_connect(connection.cm, "channelsListed", self.onChannelsListed)
        expander.add(self.playersList)
        self.channels = {}
    
    def start (self):
        self.channels = self.connection.cm.getChannels()
        if self.channels:
            self._addChannels(self.channels)
        
        for player in self.connection.players.values():
            if player.online:
                id = self.compileId(player.name, TYPE_PERSONAL)
                self.playersList.addRow(id, player.name + player.display_titles(),
                                        TYPE_PERSONAL)
        
        def addPlayer (players, player):
            self.playersList.addRow(self.compileId(player.name, TYPE_PERSONAL),
                player.name + player.display_titles(), TYPE_PERSONAL)
            return False
        self.connection.players.connect("FICSPlayerEntered", addPlayer)
        def removePlayer (players, player):
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

    def onChannelsListed (self, cm, channels):    
        if not self.channels:
            self.channels = channels
            self._addChannels(channels)
            
    def compileId (self, id, type):
        if type == TYPE_PERSONAL:
            id = "person" + id.lower()
        elif type == TYPE_CHANNEL:
            # FIXME: We can't really add stuff to the id, as panels use it to
            # identify the channel
            assert not id.startswith("person"), "Oops, this is a problem"
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
        self.emit('conversationRemoved', id)
        if type == TYPE_CHANNEL:
            self.connection.cm.removeChannel(id)
    
    def onSelect (self, joinedList, id, type):
        self.emit('conversationSelected', id)
    
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
        glock_connect(connection.cm, "privateMessage",
                      self.onPersonMessage, after=False)

        glock_connect(connection, "disconnected",
                      lambda c: self.window and self.window.hide())
        
        self.viewspanel = ViewsPanel(self.connection)
        self.channelspanel = ChannelsPanel(self.connection)
        self.infopanel = InfoPanel(self.connection)
        self.panels = [self.viewspanel, self.channelspanel, self.infopanel]
    
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
    
    def onPersonMessage (self, cm, name, title, isadmin, text):
        if self.connection.bm.isPlaying():
            if not self.window:
                self.initUi()
        else:
            self.showChat()
            self.window.set_urgency_hint(True)
    
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
