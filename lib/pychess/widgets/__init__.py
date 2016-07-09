from gi.repository import Gtk

from pychess.Utils.IconLoader import get_pixbuf


def dock_panel_tab(title, desc, icon):
    box = Gtk.Box()
    pixbuf = get_pixbuf(icon, 16)
    image = Gtk.Image.new_from_pixbuf(pixbuf)
    label = Gtk.Label(label=title)
    label.set_size_request(0, 0)
    label.set_alignment(0, 1)
    box.pack_start(image, False, False, 0)
    box.pack_start(label, True, True, 0)
    box.set_spacing(2)
    box.show_all()

    def cb(widget, x, y, keyboard_mode, tooltip, title, desc, filename):
        table = Gtk.Table(2, 2)
        table.set_row_spacings(2)
        table.set_col_spacings(6)
        table.set_border_width(4)
        pixbuf = get_pixbuf(filename, 56)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.set_alignment(0, 0)
        table.attach(image, 0, 1, 0, 2)
        titleLabel = Gtk.Label()
        titleLabel.set_markup("<b>%s</b>" % title)
        titleLabel.set_alignment(0, 0)
        table.attach(titleLabel, 1, 2, 0, 1)
        descLabel = Gtk.Label(label=desc)
        descLabel.props.wrap = True
        table.attach(descLabel, 1, 2, 1, 2)
        tooltip.set_custom(table)
        table.show_all()
        return True

    box.props.has_tooltip = True
    box.connect("query-tooltip", cb, title, desc, icon)
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
                parts[i] = '<a href="%s">%s</a>' % (part, part)
                position = i
                break
        insert("%s " % " ".join(parts[:position]))
        label = Gtk.Label()
        label.set_markup(parts[position])
        label.show()
        anchor = tb.create_child_anchor(iter)
        text_view.add_child_at_anchor(label, anchor)
        insert(" %s" % " ".join(parts[position + 1:]))
    else:
        insert(text)
