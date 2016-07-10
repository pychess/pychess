import re
from gi.repository import Gtk, GObject
from pychess.widgets.InfoPanel import Panel

TYPE_PERSONAL, TYPE_CHANNEL, TYPE_GUEST, \
    TYPE_ADMIN, TYPE_COMP, TYPE_BLINDFOLD = range(6)


def get_playername(playername):
    re_m = re.match("(\w+)\W*", playername)
    return re_m.groups()[0]


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
