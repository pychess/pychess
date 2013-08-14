import gobject
import gtk

def get_message_content (heading_text, message_text, image_stock_id):
    hbox = gtk.HBox()
    image = gtk.Image()
    image.set_from_stock(image_stock_id, gtk.ICON_SIZE_DIALOG)
    hbox.pack_start(image, expand=False, fill=False)
    vbox = gtk.VBox()
    label = gtk.Label()
    label.props.xalign = 0
    label.props.justify = gtk.JUSTIFY_LEFT
    label.set_markup("<b><big>%s</big></b>" % heading_text)
    vbox.pack_start(label, expand=False, fill=False)
    label = gtk.Label()
    label.props.xalign = 0
    label.props.justify = gtk.JUSTIFY_LEFT
    label.props.wrap = True
    label.set_text(message_text)
    vbox.pack_start(label, expand=False, fill=False)
    hbox.pack_start(vbox, expand=False, fill=False, padding=7)
    return hbox

class InfoBarMessageButton (gobject.GObject):
    def __init__(self, text, response_id, sensitive=True, tooltip_text=""):
        gobject.GObject.__init__(self)
        self.text = text
        self.response_id = response_id
        self.sensitive = sensitive
        self.tooltip_text = tooltip_text

        self._sensitive_cid = None
        self._tooltip_cid = None
        self._button = None
        
    def get_sensitive (self):
        return self._sensitive
    def set_sensitive (self, sensitive):
        self._sensitive = sensitive
    sensitive = gobject.property(get_sensitive, set_sensitive)

    def get_tooltip_text (self):
        return self._tooltip_text
    def set_tooltip_text (self, tooltip_text):
        self._tooltip_text = tooltip_text
    tooltip_text = gobject.property(get_tooltip_text, set_tooltip_text)

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
    
    def _disconnect_message (self, message):
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
            self._unload_message(message)
        self._disconnect_message(message)
        self.messages.remove(message)
        self._response_cb(self, None)
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
            button._button.set_property("tooltip-text", button.tooltip_text)
        
        return False
    
    def _response_cb (self, infobar, response):
        try:
            shown_message = self.messages[-1]
        except IndexError:
            self.hide()
        else:
            self._load_message(shown_message)
        
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
                "notify::tooltip-text", self._button_tooltip_cb, message)
            self._button_sensitive_cb(button, None, message)
            self._button_tooltip_cb(button, None, message)
        if message.callback:
            self.response_cid = self.connect("response", message.callback, message)
        
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

    def clear_messages (self):
        for message in self.messages:
            message.dismiss()
        