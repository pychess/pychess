from gi.repository import GObject
from gi.repository import Gtk


def get_message_content (heading_text, message_text, image_stock_id):
    # TODO: If you try to fix this first read issue #958 and 1018
    #hbox = Gtk.HBox()
    #image = Gtk.Image()
    #image.set_from_stock(image_stock_id, Gtk.IconSize.DIALOG)    
    #hbox.pack_start(image, False, False, 0)
    #vbox = Gtk.VBox()
    #label = Gtk.Label()
    #label.props.xalign = 0
    #label.props.justify = Gtk.Justification.LEFT
    #label.set_markup("<b><big>%s</big></b>" % heading_text)    
    #label.set_text(heading_text)    
    #vbox.pack_start(label, False, False, 0)
    label = Gtk.Label()
    label.props.xalign = 0
    label.props.justify = Gtk.Justification.LEFT
    label.props.wrap = True
    #label.set_width_chars(70)
    label.set_text("%s %s" % (heading_text, message_text))
    #vbox.pack_start(label, False, False, 0)
    #hbox.pack_start(vbox, False, False, 0)
    #return vbox
    return label

class InfoBarMessageButton (GObject.GObject):
    def __init__(self, text, response_id, sensitive=True, tooltip_text=""):
        GObject.GObject.__init__(self)
        self.text = text
        self.response_id = response_id
        self.sensitive = sensitive
        self.tooltip_text = tooltip_text
        self._button = None
        
    def get_sensitive (self):
        return self._sensitive
    def set_sensitive (self, sensitive):
        self._sensitive = sensitive
    sensitive = GObject.property(get_sensitive, set_sensitive)

    def get_tooltip_text (self):
        return self._tooltip_text
    def set_tooltip_text (self, tooltip_text):
        self._tooltip_text = tooltip_text
    tooltip_text = GObject.property(get_tooltip_text, set_tooltip_text)

class InfoBarMessage (Gtk.InfoBar):
    __gsignals__ = {
        "dismissed":  (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__ (self, message_type, content, callback):
        GObject.GObject.__init__(self)
        self.callback = callback
        self.buttons = []

        self.get_content_area().add(content)
    
    def add_button (self, button):
        """
        All buttons must be added before doing InfoBarNotebook.push_message()
        """
        if not isinstance(button, InfoBarMessageButton):
            raise TypeError("Not an InfoBarMessageButton: %s" % repr(button))
        self.buttons.append(button)
        button._button = Gtk.InfoBar.add_button(self, button.text, button.response_id)
        
        def set_sensitive(button, property):
            if self.get_children():
                self.set_response_sensitive(button.response_id, button.sensitive)
        button.connect("notify::sensitive", set_sensitive)
        
        def set_tooltip_text(button, property):
            button._button.set_property("tooltip-text", button.tooltip_text)
        button.connect("notify::tooltip-text", set_tooltip_text)
        
    def dismiss (self):
        self.hide()
        self.emit("dismissed")
    
    def update_content (self, content):
        for widget in self.get_content_area():
            self.get_content_area().remove(widget)
        self.get_content_area().add(content)
        self.show_all()
        
class InfoBarNotebook(Gtk.Notebook):
    """
    This is a :class:`Gtk.Notebook` which manages InfoBarMessage objects pushed onto it via
    push_message() like a stack. If/when the current message at the top of the
    stack is responded to or dismissed by the user, the next message in the
    stack waiting for a response is displayed. Messages that aren't applicable
    anymore can be removed from anywhere in the InfoBar message stack by calling
    message.dismiss()
    """
    def __init__ (self):
        Gtk.Notebook.__init__(self)
        self.set_show_tabs(False)
        
    def push_message (self, message):

        def on_dismissed(mesage):
            pn = self.page_num(message)
            if pn != -1:
                self.remove_page(pn)
            
        def on_response(message, response_id):
            if callable(message.callback):
                message.callback(self, response_id, message)
            pn = self.page_num(message)
            if pn != -1:
                self.remove_page(pn)
            
        cp = self.get_current_page()
        if cp > 0:
            self.remove_page(cp)
        self.append_page(message, None)
        message.connect("response", on_response)
        message.connect("dismissed", on_dismissed)
        self.show_all()

    def clear_messages (self):
        for child in self.get_children():
            self.remove(child)
        
