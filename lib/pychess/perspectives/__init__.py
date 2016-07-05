from gi.repository import Gtk


class Perspective(object):
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.widget = Gtk.Alignment()

    @property
    def sensitive(self):
        perspective, button, index = perspective_manager.perspectives[self.name]
        return button.get_sensitive()


class PerspectiveManager(object):
    def __init__(self):
        self.perspectives = {}

    def set_widgets(self, widgets):
        self.widgets = widgets

    def on_persp_toggled(self, button):
        active = button.get_active()
        if active:
            name = button.get_name()
            perspective, button, index = self.perspectives[name]
            self.widgets["perspectives_notebook"].set_current_page(index)

    def add_perspective(self, perspective, default=False):
        box = self.widgets["persp_buttons"]
        children = box.get_children()
        widget = None if len(children) == 0 else children[0]
        button = Gtk.RadioButton.new_with_label_from_widget(widget, perspective.label)
        if not default:
            button.set_sensitive(False)
        button.set_name(perspective.name)
        button.set_mode(False)
        box.pack_start(button, True, True, 0)
        button.connect("toggled", self.on_persp_toggled)

        index = self.widgets["perspectives_notebook"].append_page(perspective.widget, None)
        self.perspectives[perspective.name] = (perspective, button, index)

    def activate_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        button.set_sensitive(True)
        button.set_active(True)

    def disable_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        button.set_sensitive(False)

    def get_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        return perspective

    def set_perspective_widget(self, name, widget):
        perspective, button, index = self.perspectives[name]
        container = self.widgets["perspectives_notebook"].get_nth_page(index)
        for child in container.get_children():
            container.remove(child)
        container.add(widget)


perspective_manager = PerspectiveManager()
