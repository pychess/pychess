from gi.repository import Gtk


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
                if part.endswith('"'):
                    part = part[:-1]
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
