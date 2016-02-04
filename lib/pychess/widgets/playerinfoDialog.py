from __future__ import absolute_import
from gi.repository import Gtk, GObject


firstRun = True


def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["player_info"].show_all()


def initialize(widgets):
    def addColumns(treeview, *columns):
        model = Gtk.ListStore(*((str, ) * len(columns)))
        treeview.set_model(model)
        treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        for i, name in enumerate(columns):
            crt = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(name, crt, text=i)
            treeview.append_column(column)

    addColumns(widgets["results_view"], "", "Games", "Won", "Drawn", "Lost",
               "Score")
    model = widgets["results_view"].get_model()
    model.append(("White", "67", "28", "24", "15", "59%"))
    model.append(("Black", "66", "26", "23", "17", "56%"))
    model.append(("Total", "133", "54", "47", "32", "58%"))

    addColumns(widgets["rating_view"], "Current", "Initial", "Lowest",
               "Highest", "Average")
    model = widgets["rating_view"].get_model()
    model.append(("1771", "1734", "1659", "1791", "1700"))

    widgets["history_view"].set_model(Gtk.ListStore(object))
    widgets["history_view"].get_selection().set_mode(Gtk.SelectionMode.NONE)
    widgets["history_view"].append_column(
        Gtk.TreeViewColumn("Player Rating History",
                           HistoryCellRenderer(),
                           data=0))
    widgets["history_view"].get_model().append((1, ))

    def hide_window(button, *args):
        widgets["player_info"].hide()
        return True

    widgets["player_info"].connect("delete-event", hide_window)
    widgets["player_info_close_button"].connect("clicked", hide_window)


class HistoryCellRenderer(Gtk.CellRenderer):
    __gproperties__ = {
        "data":
        (GObject.TYPE_PYOBJECT, "Data", "Data", GObject.PARAM_READWRITE),
    }

    def __init__(self):
        self.__gobject_init__()
        self.data = None

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_render(self, window, widget, background_area, rect, expose_area,
                  flags):
        if not self.data:
            return
        cairo = window.cairo_create()
        x_loc, y_loc, width, height = rect.x, rect.y, rect.width, rect.height
        cairo.rectangle(x_loc + 1, y_loc + 1, x_loc + width - 2, y_loc + height - 2)
        cairo.set_source_rgb(0.45, 0.45, 0.45)
        cairo.stroke()

    def on_get_size(self, widget, cell_area=None):
        return (0, 0, -1, 130)
