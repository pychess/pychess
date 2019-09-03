from gi.repository import Gtk


def getUserTextDialog(parent, title, description):
    dialog = Gtk.Dialog(title, parent,
                        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
    textedit = Gtk.Entry()
    textedit.connect("activate", lambda p: dialog.response(Gtk.ResponseType.ACCEPT))
    hbx = Gtk.VBox()
    hbx.pack_start(Gtk.Label(description), False, 5, 5)
    hbx.pack_end(textedit, False, 5, 5)
    dialog.get_content_area().pack_start(hbx, True, True, 0)
    dialog.show_all()
    if (dialog.run() == Gtk.ResponseType.ACCEPT):
        result = textedit.get_text()
    else:
        result = None
    dialog.destroy()
    return result
