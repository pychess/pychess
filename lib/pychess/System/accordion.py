import gtk


class Accordion(gtk.TreeView):
    def __init__(self, model):
        gtk.TreeView.__init__(self, model)

        self.set_headers_visible(False)
        self.set_property("show-expanders", False)
        self.set_property("level-indentation", 10)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn('Column', renderer)

        def top_level(column, cell, store, iter):
            cell.set_property("text", store[iter][0])
            if store.iter_depth(iter) == 0:
                cell.set_property('foreground', "black")
                cell.set_property('background', "gray")
            else:
                cell.set_property('foreground', "black")
                cell.set_property('background', "white")
        column.set_cell_data_func(renderer, top_level)

        self.append_column(column)

        selection = self.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect('changed', self.on_selection_changed)
        self.current = None

    def on_selection_changed(self, selection, data=None):
        model, iter = selection.get_selected()

        if model.iter_depth(iter) == 0 and iter != self.current:
            self.collapse_all()
            self.expand_row(model.get_path(iter), True)
            self.current = iter

        selected_item = model.get_value(iter, 0)
        print selected_item
        

if __name__ == "__main__":
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_title("Accordion example")
    window.set_size_request(200, 200)
    window.connect("delete_event", gtk.main_quit)

    treestore = gtk.TreeStore(str)
    for parent in range(4):
        piter = treestore.append(None, ['parent %i' % parent])
        for child in range(3):
            treestore.append(piter, ['child %i of parent %i' %
                                          (child, parent)])
    accordion = Accordion(treestore)
    window.add(accordion)
    window.show_all()
    gtk.main()
