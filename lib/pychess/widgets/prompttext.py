from gi.repository import Gtk


def getUserTextDialog(parent, title, description):
    dialog = Gtk.Dialog(
        title,
        parent,
        Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        (
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.ACCEPT,
        ),
    )
    dialog.set_resizable(False)
    dialog.set_size_request(400, -1)

    vbx = Gtk.VBox()
    label = Gtk.Label(description)
    label.set_xalign(0)
    vbx.pack_start(label, True, True, 5)
    textedit = Gtk.Entry()
    textedit.connect("activate", lambda p: dialog.response(Gtk.ResponseType.ACCEPT))
    vbx.pack_end(textedit, True, True, 5)

    hbx = Gtk.HBox()
    hbx.pack_start(vbx, True, True, 10)

    dialog.get_content_area().pack_start(hbx, True, True, 5)
    dialog.show_all()
    if dialog.run() == Gtk.ResponseType.ACCEPT:
        result = textedit.get_text()
    else:
        result = None
    dialog.destroy()
    return result
