import re

from gi.repository import Gtk
from pychess.widgets.ChatView import ChatView
from pychess.widgets.ViewsPanel import ViewsPanel
from pychess.widgets.InfoPanel import InfoPanel
from pychess.widgets.ChannelsPanel import ChannelsPanel
from pychess.System import uistuff

TYPE_PERSONAL, TYPE_CHANNEL, TYPE_GUEST, \
    TYPE_ADMIN, TYPE_COMP, TYPE_BLINDFOLD = range(6)


def get_playername(playername):
    re_m = re.match("(\w+)\W*", playername)
    return re_m.groups()[0]


class ChatWindow(object):
    def __init__(self, widgets, connection):
        self.connection = connection

        self.viewspanel = ViewsPanel(self.connection)
        self.channelspanel = ChannelsPanel(self.connection)
        self.adj = self.channelspanel.get_vadjustment()
        self.infopanel = InfoPanel(self.connection)
        self.chatbox = Gtk.Paned()
        self.chatbox.add1(self.channelspanel)

        notebook = Gtk.Notebook()
        notebook.append_page(self.viewspanel, Gtk.Label(_("Chat")))
        notebook.append_page(self.infopanel, Gtk.Label(_("Info")))
        self.chatbox.add2(notebook)

        self.panels = [self.viewspanel, self.channelspanel, self.infopanel]
        self.viewspanel.connect('channel_content_Changed',
                                self.channelspanel.channel_Highlight, id)

        self.channelspanel.connect('conversationAdded',
                                   self.onConversationAdded)
        self.channelspanel.connect('conversationRemoved',
                                   self.onConversationRemoved)
        self.channelspanel.connect('conversationSelected',
                                   self.onConversationSelected)
        self.channelspanel.connect('focus_in_event', self.focus_in, self.adj)

        for panel in self.panels:
            panel.show_all()
            panel.start()

        uistuff.keep(self.chatbox, "chat_paned_position", first_value=100)

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

    def openChatWithPlayer(self, name):
        cm = self.connection.cm
        self.channelspanel.onPersonMessage(cm, name, "", False, "")

    def focus_in(widget, event, adj):
        alloc = widget.get_allocation()
        if alloc.y < adj.value or alloc.y > adj.value + adj.page_size:
            adj.set_value(min(alloc.y, adj.upper - adj.page_size))

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

    chatwin = ChatWindow({}, Con())
    globals()["_"] = lambda x: x
    chatwin.window.connect("delete-event", Gtk.main_quit)
    Gtk.main()
