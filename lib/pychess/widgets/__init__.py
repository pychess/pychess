from gi.repository import Gtk

from pychess.Utils.IconLoader import get_pixbuf, load_icon
# from pychess.widgets.WebKitBrowser import open_link

main_window = None

gtk_close = load_icon(16, "gtk-close", "window-close")


def mainwindow():
    return main_window


def createImage(pixbuf):
    image = Gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image


def createAlignment(top, right, bottom, left):
    align = Gtk.Alignment.new(.5, .5, 1, 1)
    align.set_property("top-padding", top)
    align.set_property("right-padding", right)
    align.set_property("bottom-padding", bottom)
    align.set_property("left-padding", left)
    return align


def new_notebook(name=None):
    def customGetTabLabelText(child):
        return name

    notebook = Gtk.Notebook()
    if name is not None:
        notebook.set_name(name)
    notebook.get_tab_label_text = customGetTabLabelText
    notebook.set_show_tabs(False)
    notebook.set_show_border(False)
    return notebook


def dock_panel_tab(title, desc, icon, button=None):
    box = Gtk.Box()
    pixbuf = get_pixbuf(icon, 16)
    image = Gtk.Image.new_from_pixbuf(pixbuf)
    label = Gtk.Label(label=title)
    box.set_tooltip_text(desc)
    box.pack_start(image, False, True, 0)
    box.pack_start(label, False, True, 0)
    if button is not None:
        box.pack_start(button, False, True, 0)

    box.set_spacing(2)
    box.show_all()

    return box


def insert_formatted(text_view, iter, text, tag=None):
    def insert(text):
        if tag is not None:
            tb.insert_with_tags_by_name(iter, text, tag)
        else:
            tb.insert(iter, text)

    tb = text_view.get_buffer()
    # I know this is far from perfect but I don't want to use re for this
    if "://" in text or "www" in text:
        parts = text.split()
        position = 0
        for i, part in enumerate(parts):
            if "://" in part or "www" in part:
                if part.startswith('"'):
                    part = part[1:]
                    endpos = part.find('"')
                    if endpos != -1:
                        part = part[:endpos]
                part0 = "http://web.archive.org/%s" % part if part.startswith("http://www.endgame.nl") else part
                parts[i] = '<a href="%s">%s</a>' % (part0, part)
                position = i
                break
        insert("%s " % " ".join(parts[:position]))
        label = Gtk.Label()
        label.set_markup(parts[position])
        # label.connect("activate-link", open_link)
        label.show()
        anchor = tb.create_child_anchor(iter)
        text_view.add_child_at_anchor(label, anchor)
        insert(" %s" % " ".join(parts[position + 1:]))
    else:
        insert(text)
