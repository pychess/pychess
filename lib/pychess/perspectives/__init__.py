from gi.repository import Gtk


class Perspective(object):
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.default = False
        self.widget = Gtk.Alignment()
        self.widget.show()
        self.toolbuttons = []

    @property
    def sensitive(self):
        perspective, button, index = perspective_manager.perspectives[self.name]
        return button.get_sensitive()

    def create_toolbuttons(self):
        pass

    def close(self):
        pass


class PerspectiveManager(object):
    def __init__(self):
        self.perspectives = {}
        self.current_perspective = None

    def set_widgets(self, widgets):
        self.widgets = widgets
        self.toolbar = self.widgets["toolbar1"]

    def on_persp_toggled(self, button):
        active = button.get_active()
        if active:
            name = button.get_name()
            perspective, button, index = self.perspectives[name]
            self.widgets["perspectives_notebook"].set_current_page(index)
            self.current_perspective = perspective

    def add_perspective(self, perspective):
        box = self.widgets["persp_buttons"]
        children = box.get_children()
        widget = None if len(children) == 0 else children[0]
        button = Gtk.RadioButton.new_with_label_from_widget(widget, perspective.label)
        if perspective.default:
            self.current_perspective = perspective
        else:
            button.set_sensitive(False)
        button.set_name(perspective.name)
        button.set_mode(False)
        box.pack_start(button, True, True, 0)
        button.connect("toggled", self.on_persp_toggled)

        index = self.widgets["perspectives_notebook"].append_page(perspective.widget, None)
        self.perspectives[perspective.name] = (perspective, button, index)

    def activate_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        if not perspective.sensitive:
            for toolbutton in perspective.toolbuttons:
                if button not in self.toolbar:
                    self.toolbar.add(toolbutton)
                toolbutton.show()
        button.set_sensitive(True)
        button.set_active(True)

    def disable_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        button.set_sensitive(False)
        for toolbutton in perspective.toolbuttons:
            self.toolbar.remove(toolbutton)

    def get_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        return perspective

    def set_perspective_widget(self, name, widget):
        perspective, button, index = self.perspectives[name]
        container = self.widgets["perspectives_notebook"].get_nth_page(index)
        for child in container.get_children():
            container.remove(child)
        container.add(widget)

    def set_perspective_toobuttons(self, name, buttons):
        perspective, button, index = self.perspectives[name]
        if len(perspective.toolbuttons) == 0:
            separator = Gtk.SeparatorToolItem.new()
            separator.set_draw(True)
            perspective.toolbuttons.append(separator)
            for button in buttons:
                perspective.toolbuttons.append(button)

perspective_manager = PerspectiveManager()
