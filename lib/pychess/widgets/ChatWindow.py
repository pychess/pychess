import time

import gtk
import gobject
import pango

from pychess.System import uistuff
from pychess.System.glock import glock_connect
from pychess.widgets.ChatView import ChatView
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import NORTH, EAST, SOUTH, WEST, CENTER

TYPE_PERSONAL, TYPE_CHANNEL = range(2)

class BulletCellRenderer (gtk.GenericCellRenderer):
    __gproperties__ = {
        "color": (object, "Color", "Color", gobject.PARAM_READWRITE),
    }
    
    def __init__(self):
        self.__gobject_init__()
        self.color = None
        self.width = 16
        self.height = 16
    
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
    
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
    
    def on_render(self, window, widget, bg_area, cell_area, expose_area, flags):
        if not self.color: return
        
        x, y = self.get_size(widget, cell_area)[:2]
        context = window.cairo_create()
        
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

gobject.type_register(BulletCellRenderer)

class TextImageTree (gtk.TreeView):
    """ Defines a tree with two columns.
        The first one has text. The seccond one a clickable stock_icon """
    
    __gsignals__ = {
        'activated' : (gobject.SIGNAL_RUN_FIRST, None, (str,str,int)),
        'selected' : (gobject.SIGNAL_RUN_FIRST, None, (str,int))
    }
    
    def __init__(self, icon_name):
        gtk.TreeView.__init__(self)
        self.id2iter = {}
        
        self.icon_name = icon_name
        self.props.model = gtk.ListStore(str,str,int)
        self.idSet = set()
        
        self.set_headers_visible(False)
        self.set_tooltip_column(1)
        self.set_search_column(1)
        
        # First column
        crt = gtk.CellRendererText()
        crt.props.ellipsize = pango.ELLIPSIZE_END
        self.leftcol = gtk.TreeViewColumn("", crt, text=1)
        self.leftcol.set_expand(True)
        self.append_column(self.leftcol)
        
        # Second column
        icons = gtk.icon_theme_get_default()
        pixbuf = icons.load_icon(icon_name, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        crp = gtk.CellRendererPixbuf()
        crp.props.pixbuf = pixbuf
        self.rightcol = gtk.TreeViewColumn("", crp)
        self.append_column(self.rightcol)
        
        # Mouse
        self.pressed = None
        self.stdcursor = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
        self.linkcursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        # Selection
        self.get_selection().connect("changed", self.selection_changed)
    
    def addRow (self, id, text, type):
        iter = self.props.model.append([id, text, type])
        self.id2iter[id] = iter
        self.idSet.add(id)
    
    def removeRow (self, id):
        iter = self.id2iter[id]
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
            self.window.set_cursor(self.linkcursor)
        else:
            self.window.set_cursor(self.stdcursor)
    
    def leave_notify (self, widget, event):
        self.window.set_cursor(self.stdcursor)
    
    def selection_changed (self, selection):
        model, iter = selection.get_selected()
        if iter:
            id = model.get_value(iter, 0)
            type = model.get_value(iter, 2)
            self.emit("selected", id, type)

class Panel:
    def start (self): pass
    def addItem (self, id, text, type, chatView): pass
    def removeItem (self, id): pass
    def selectItem (self, id): pass

#===============================================================================
# Panels
#===============================================================================

class ViewsPanel (gtk.Notebook, Panel):
    
    def __init__ (self, connection):
        gtk.Notebook.__init__(self)
        self.set_show_tabs(False)
        self.set_show_border(False)
        self.id2Widget = {}
        self.connection = connection
        
        label = gtk.Label()
        label.set_markup("<big>%s</big>" %
                         _("You have opened no conversations yet"))
        label.props.xalign = .5
        label.props.yalign = 0.381966011
        label.props.justify = gtk.JUSTIFY_CENTER
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
                      self.onPersonMessage, name, chatView)
        
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
            chatView.appendLogMessage(time, handle, text)
    
    def onMessageTyped (self, chatView, text, id, name, type):
        if type == TYPE_CHANNEL:
            self.connection.cm.tellChannel(id, text)
        elif type == TYPE_PERSONAL:
            self.connection.cm.tellPlayer(name, text)
        chatView.addMessage(self.connection.getUsername(), text)
    
    def onPersonMessage (self, cm, name, title, isadmin, text, name_, chatView):
        if name.lower() == name_.lower():
            chatView.addMessage(name, text)
    
    def onChannelMessage (self, cm, name, isadmin, isme, channel, text, name_, chatView):
        if channel.lower() == name_.lower() and not isme:
            chatView.addMessage(name, text)
    
    
    def addPage (self, widget, id):
        self.id2Widget[id] = widget
        self.append_page(widget)
        widget.show_all()
    
    def removePage (self, id):
        child = self.id2Widget.pop(id)
        self.remove_page(self.page_num(child))


class InfoPanel (gtk.Notebook, Panel):
    def __init__ (self, connection):
        gtk.Notebook.__init__(self)
        self.set_show_tabs(False)
        self.set_show_border(False)
        self.id2Widget = {}
        
        label = gtk.Label()
        label.set_markup("<big>%s</big>" % _("No conversation's selected"))
        label.props.xalign = .5
        label.props.yalign = 0.381966011
        label.props.justify = gtk.JUSTIFY_CENTER
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
        self.append_page(widget)
        widget.show_all()
    
    def removePage (self, id):
        child = self.id2Widget.pop(id)
        self.remove_page(self.page_num(child))
    
    class PlayerInfoItem (gtk.Alignment):
        def __init__ (self, id, text, chatView, connection):
            gtk.Alignment.__init__(self, xscale=1, yscale=1)
            self.add(gtk.Label(_("Loading player data")))
            
            self.fm = connection.fm
            self.handle_id = glock_connect(self.fm, "fingeringFinished",
                                           self.onFingeringFinished, text)
            
            self.fm.finger(text)
        
        def onFingeringFinished (self, fm, finger, text):
            if not isinstance(self.get_child(), gtk.Label) or \
                    finger.getName().lower() != text.lower():
                return
            self.fm.disconnect(self.handle_id)
            
            label = gtk.Label()
            label.set_markup("<b>%s</b>" % text)
            widget = gtk.Frame()
            widget.set_label_widget(label)
            widget.set_shadow_type(gtk.SHADOW_NONE)
            
            alignment = gtk.Alignment(0, 0, 1, 1)
            alignment.set_padding(3, 0, 12, 0)
            widget.add(alignment)
            
            store = gtk.ListStore(str,str)
            for i, note in enumerate(finger.getNotes()):
                if note:
                    store.append([str(i+1),note])
            tv = gtk.TreeView(store)
            tv.get_selection().set_mode(gtk.SELECTION_NONE)
            tv.set_headers_visible(False)
            tv.modify_base(gtk.STATE_NORMAL, self.get_style().bg[gtk.STATE_NORMAL].copy())
            cell = gtk.CellRendererText()
            cell.props.cell_background_gdk = self.get_style().bg[gtk.STATE_ACTIVE].copy()
            cell.props.cell_background_set = True 
            cell.props.yalign = 0
            tv.append_column(gtk.TreeViewColumn("", cell, text=0))
            cell = uistuff.appendAutowrapColumn(tv, 50, "Notes", text=1)
            cell.props.cell_background_gdk = self.get_style().bg[gtk.STATE_NORMAL].copy()
            cell.props.cell_background_set = True 
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.add(tv)
            alignment.add(sw)
            
            self.remove(self.get_child())
            self.add(widget)
            widget.show_all()
    
    class ChannelInfoItem (gtk.Alignment):
        def __init__ (self, id, text, chatView, connection):
            gtk.Alignment.__init__(self, xscale=1, yscale=1)
            self.cm = connection.cm
            self.add(gtk.Label(_("Recieving list of players")))
            
            chatView.connect("messageAdded", self.onMessageAdded)
            self.store = gtk.ListStore(object, # (r,g,b) Color tuple
                                       str,    # name string
                                       bool    # is separator
                                       )
            
            self.handle_id = glock_connect(self.cm, "recievedNames",
                                           self.onNamesRecieved, id)
            self.cm.getPeopleInChannel(id)
        
        def onNamesRecieved (self, cm, channel, people, channel_):
            if not isinstance(self.get_child(), gtk.Label) or channel != channel_:
                return
            cm.disconnect(self.handle_id)
            
            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            
            list = gtk.TreeView()
            list.set_headers_visible(False)
            list.set_tooltip_column(1)
            list.set_model(self.store)
            list.append_column(gtk.TreeViewColumn("", BulletCellRenderer(), color=0))
            cell = gtk.CellRendererText()
            cell.props.ellipsize = pango.ELLIPSIZE_END
            list.append_column(gtk.TreeViewColumn("", cell, text=1))
            list.fixed_height_mode = True
            
            self.separatorIter = self.store.append([(),"",True])
            list.set_row_separator_func(lambda m,i: m.get_value(i, 2))
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

class ChannelsPanel (gtk.ScrolledWindow, Panel):
    
    __gsignals__ = {
        'conversationAdded' : (gobject.SIGNAL_RUN_FIRST, None, (str,str,int)),
        'conversationRemoved' : (gobject.SIGNAL_RUN_FIRST, None, (str,)),
        'conversationSelected' : (gobject.SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self, connection):
        gtk.ScrolledWindow.__init__(self)
        self.connection = connection
        
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox = gtk.VBox()
        self.add_with_viewport(vbox)
        self.child.set_shadow_type(gtk.SHADOW_NONE)
        
        self.joinedList = TextImageTree("gtk-remove")
        self.joinedList.connect("activated", self.onRemove)
        self.joinedList.connect("selected", self.onSelect)
        vbox.pack_start(self.joinedList)
        
        expander = gtk.Expander(_("More channels"))
        vbox.pack_start(expander, expand=False)
        self.channelsList = TextImageTree("gtk-add")
        self.channelsList.connect("activated", self.onAdd)
        self.channelsList.fixed_height_mode = True
        expander.add(self.channelsList)
        
        expander = gtk.Expander(_("More players"))
        vbox.pack_start(expander, expand=False)
        self.playersList = TextImageTree("gtk-add")
        self.playersList.connect("activated", self.onAdd)
        self.playersList.fixed_height_mode = True
        glock_connect(connection.cm, "privateMessage", self.onPersonMessage, after=True)
        expander.add(self.playersList)
    
    def start (self):
        for id, name in self.connection.cm.getChannels():
            id = self.compileId(id, TYPE_CHANNEL)
            self.channelsList.addRow(id, name, TYPE_CHANNEL)
        
        for id, name in self.connection.cm.getChannels():
            if id in self.connection.cm.getJoinedChannels():
                id = self.compileId(id, TYPE_CHANNEL)
                self.onAdd(self.channelsList, id, name, TYPE_CHANNEL)
        
        for name in self.connection.glm.getPlayerlist():
            id = self.compileId(name, TYPE_PERSONAL)
            self.playersList.addRow(id, name, TYPE_PERSONAL)
    
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

class ChatWindow:
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
    
    def initUi (self):
        self.window = gtk.Window()
        self.window.set_border_width(12)
        self.window.set_icon_name("pychess")
        self.window.set_title("PyChess - Internet Chess Chat")
        self.window.connect("delete-event", lambda w,e: w.hide() or True)
        
        uistuff.keepWindowSize("chatwindow", self.window, defaultSize=(650,400))
        
        dock = PyDockTop("icchat")
        dock.show()
        self.window.add(dock)
        
        leaf = dock.dock(self.viewspanel, CENTER, gtk.Label("chat"), "chat")
        leaf.setDockable(False)
        
        self.channelspanel.connect('conversationAdded', self.onConversationAdded)
        self.channelspanel.connect('conversationRemoved', self.onConversationRemoved)
        self.channelspanel.connect('conversationSelected', self.onConversationSelected)
        leaf.dock(self.channelspanel, WEST, gtk.Label(_("Conversations")), "conversations")
        
        leaf.dock(self.infopanel, EAST, gtk.Label(_("Conversation info")), "info")
        
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
        self.showChat()
        self.window.set_urgency_hint(True)
    
    def openChatWithPlayer (self, name):
        self.showChat()
        self.window.window.raise_()
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
    cw.window.connect("delete-event", gtk.main_quit)
    gtk.main()
