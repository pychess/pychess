import gobject
import gtk

class InfoBarMessage (gobject.GObject):
    __gsignals__ = {
        "dismissed":  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }
    def __init__ (self, message_type, content, callback, *args):
        """ any *args have to be (button_text/stock_id, response_id)
            tuples for passing to add_button() to init the buttons """
        gobject.GObject.__init__(self)
        self.type = message_type
        container = gtk.HBox()
        container.pack_start(content, expand=False, fill=False)
        self.content = container
        self.callback = callback
        self.callback_cid = None
        self.buttons = []
        for button in args:
            self.buttons.append(button)
        
    def dismiss (self):
        self.emit("dismissed")
        
class InfoBar (gtk.InfoBar):
    """
    This is a gtk.InfoBar which manages messages pushed onto it via
    push_message() like a stack. If/when the current message at the top of the
    stack is responded to or dismissed by the user, the next message in the
    stack waiting for a response is displayed. Messages that aren't applicable
    anymore can be removed from anywhere in the InfoBar message stack by calling
    message.dismiss()
    """
    def __init__ (self, *args):
        gtk.InfoBar.__init__(self, *args)
        self.messages = []
        self.response_cid = None
        self.connect_after("response", self._response_cb)
        
    def _disconnect_response (self):
        if self.response_cid and self.handler_is_connected(self.response_cid):
            self.disconnect(self.response_cid)
        self.response_cid = None
    
    def _disconnect_message (self, message):
        if message.callback_cid and \
                message.handler_is_connected(message.callback_cid):
            message.disconnect(message.callback_cid)
        message.callback_cid = None
    
    def _message_dismissed_cb (self, message):
        if message in self.messages:
            if message == self.messages[-1]:
                self.response(gtk.RESPONSE_CANCEL)
            else:
                self._disconnect_message(message)
                self.messages.remove(message)
    
    def _response_cb (self, infobar, response):
        try:
            message = self.messages.pop()
            self._disconnect_message(message)
            self._disconnect_response()
        except IndexError: pass
        if self.messages:
            self._load_message(self.messages[-1])
        else:
            self.hide()
        return False
        
    def _load_message (self, message):
        for container in (self.get_action_area(), self.get_content_area()):
            for widget in container:
                container.remove(widget)
        self.set_message_type(message.type)
        self.get_content_area().add(message.content)
        if message.buttons:
            for button_text, response_id in message.buttons:
                self.add_button(button_text, response_id)
        else:
            self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CANCEL)
        if message.callback:
            self.response_cid = self.connect("response", message.callback)
        
    def push_message (self, message):
        if not isinstance(message, InfoBarMessage):
            raise TypeError("Not of type InfoBarMessage: %s" % repr(message))
        if self.messages:
            self._disconnect_response()
        self._load_message(message)
        message.callback_cid = message.connect("dismissed",
                                               self._message_dismissed_cb)
        self.messages.append(message)
        self.show_all()
