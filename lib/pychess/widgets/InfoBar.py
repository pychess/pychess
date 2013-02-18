import gobject
import gtk

class InfoBarMessageButton (gobject.GObject):
    def __init__(self, text, response_id, sensitive=True, tooltip=""):
        gobject.GObject.__init__(self)
        self.text = text
        self.response_id = response_id
        self.sensitive = sensitive
        self.tooltip = tooltip

        self._sensitive_cid = None
        self._tooltip_cid = None
        self._button = None
        
    def get_sensitive (self):
        return self._sensitive
    def set_sensitive (self, sensitive):
        self._sensitive = sensitive
    sensitive = gobject.property(get_sensitive, set_sensitive)

    def get_tooltip (self):
        return self._tooltip
    def set_tooltip (self, tooltip):
        self._tooltip = tooltip
    tooltip = gobject.property(get_tooltip, set_tooltip)

class InfoBarMessage (gobject.GObject):
    __gsignals__ = {
        "dismissed":  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }
    def __init__ (self, message_type, content, callback):
        gobject.GObject.__init__(self)
        self.type = message_type
        container = gtk.HBox()
        container.pack_start(content, expand=False, fill=False)
        self.content = container
        self.callback = callback
        self.buttons = []

        self._dismissed_cid = None
        
    def add_button (self, button):
        """
        All buttons must be added before doing InfoBar.push_message()
        """
        if not isinstance(button, InfoBarMessageButton):
            raise TypeError("Not an InfoBarMessageButton: %s" % repr(button))
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
    
    def _remove_message (self, message):
        if message.handler_is_connected(message._dismissed_cid):
            message.disconnect(message._dismissed_cid)
        message._dismissed_cid = None
        
        for button in message.buttons:
            if button.handler_is_connected(button._sensitive_cid):
                button.disconnect(button._sensitive_cid)
            button._sensitive_cid = None
            
            if button.handler_is_connected(button._tooltip_cid):
                button.disconnect(button._tooltip_cid)
            button._tooltip_cid = None
    
    def _message_dismissed_cb (self, message):
        try:
            shown_message = self.messages[-1]
        except IndexError:
            shown_message = None
        
        if message == shown_message:
            self.response(gtk.RESPONSE_CANCEL)
        else:
            self._remove_message(message)
            self.messages.remove(message)
        
        return False
    
    def _button_sensitive_cb (self, button, property, message):
        try:
            shown_message = self.messages[-1]
        except IndexError:
            return
        
        if message == shown_message:
            self.set_response_sensitive(button.response_id, button.sensitive)
        
        return False
    
    def _button_tooltip_cb (self, button, property, message):
        try:
            shown_message = self.messages[-1]
        except IndexError:
            return
        
        if message == shown_message and button._button is not None:
            button._button.set_property("tooltip-text", button.tooltip)
        
        return False
    
    def _response_cb (self, infobar, response):
        try:
            shown_message = self.messages.pop()
        except IndexError:
            pass
        else:
            self._unload_message(shown_message)
            self._remove_message(shown_message)
        
        try:
            cur_message = self.messages[-1]
        except IndexError:
            self.hide()
        else:
            self._load_message(cur_message)
        
        return False
        
    def _unload_message (self, message):
        if self.response_cid is not None and \
                self.handler_is_connected(self.response_cid):
            self.disconnect(self.response_cid)
        self.response_cid = None
        
        for button in message.buttons:
            button._button = None
        
    def _load_message (self, message):
        for container in (self.get_action_area(), self.get_content_area()):
            for widget in container:
                container.remove(widget)
        self.set_message_type(message.type)
        self.get_content_area().add(message.content)
        for button in message.buttons:
            button._button = self.add_button(button.text, button.response_id)
            button._sensitive_cid = button.connect(
                "notify::sensitive", self._button_sensitive_cb, message)
            button._tooltip_cid = button.connect(
                "notify::tooltip", self._button_tooltip_cb, message)
            self._button_sensitive_cb(button, None, message)
            self._button_tooltip_cb(button, None, message)
        if message.callback:
            self.response_cid = self.connect("response", message.callback)
        
    def push_message (self, message):
        if not isinstance(message, InfoBarMessage):
            raise TypeError("Not of type InfoBarMessage: %s" % repr(message))
        
        try:
            shown_message = self.messages[-1]
        except IndexError:
            pass
        else:
            self._unload_message(shown_message)
        
        self.messages.append(message)
        self._load_message(message)
        message._dismissed_cid = message.connect("dismissed",
                                                 self._message_dismissed_cb)
        self.show_all()
