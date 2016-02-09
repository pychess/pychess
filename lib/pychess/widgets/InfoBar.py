from gi.repository import GObject, Gtk


def get_message_content(heading_text, message_text, image_stock_id):
    label = Gtk.Label()
    label.props.xalign = 0
    label.props.justify = Gtk.Justification.LEFT
    label.props.wrap = True
    label.set_text("%s %s" % (heading_text, message_text))
    return label


class InfoBarMessageButton(GObject.GObject):
    def __init__(self, text, response_id, sensitive=True, tooltip_text=""):
        GObject.GObject.__init__(self)
        self.text = text
        self.response_id = response_id
        self.sensitive = sensitive
        self.tooltip_text = tooltip_text
        self._button = None

    def get_sensitive(self):
        return self._sensitive

    def set_sensitive(self, sensitive):
        self._sensitive = sensitive

    sensitive = GObject.property(get_sensitive, set_sensitive)

    def get_tooltip_text(self):
        return self._tooltip_text

    def set_tooltip_text(self, tooltip_text):
        self._tooltip_text = tooltip_text

    tooltip_text = GObject.property(get_tooltip_text, set_tooltip_text)


class InfoBarMessage(Gtk.InfoBar):
    __gsignals__ = {"dismissed": (GObject.SignalFlags.RUN_FIRST, None, ()), }

    def __init__(self, message_type, content, callback):
        GObject.GObject.__init__(self)
        self.callback = callback
        self.content = content
        self.buttons = []

        self.get_content_area().add(content)

    def add_button(self, button):
        """
        All buttons must be added before doing InfoBarNotebook.push_message()
        """
        if not isinstance(button, InfoBarMessageButton):
            raise TypeError("Not an InfoBarMessageButton: %s" % repr(button))
        self.buttons.append(button)
        button._button = Gtk.InfoBar.add_button(self, button.text,
                                                button.response_id)

        def set_sensitive(button, property):
            if self.get_children():
                self.set_response_sensitive(button.response_id,
                                            button.sensitive)

        button.connect("notify::sensitive", set_sensitive)

        def set_tooltip_text(button, property):
            button._button.set_property("tooltip-text", button.tooltip_text)

        button.connect("notify::tooltip-text", set_tooltip_text)

    def dismiss(self):
        self.hide()
        self.emit("dismissed")

    def update_content(self, content):
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

    def __init__(self, name=None):
        Gtk.Notebook.__init__(self)
        if name is not None:
            self.set_name(name)
        self.get_tab_label_text = self.customGetTabLabelText
        self.set_show_tabs(False)

    def customGetTabLabelText(self, child):
        return child.content.get_text()

    def push_message(self, message):
        def on_dismissed(mesage):
            page_num = self.page_num(message)
            if page_num != -1:
                self.remove_page(page_num)

        def onResponse(message, response_id):
            if callable(message.callback):
                message.callback(self, response_id, message)
            page_num = self.page_num(message)
            if page_num != -1:
                self.remove_page(page_num)

        current_page = self.get_current_page()
        if current_page > 0:
            self.remove_page(current_page)
        self.append_page(message, None)
        message.connect("response", onResponse)
        message.connect("dismissed", on_dismissed)
        self.show_all()

    def clear_messages(self):
        for child in self.get_children():
            self.remove(child)
