from gi.repository import Gtk, Pango

from pychess.System.prefix import addDataPrefix
from pychess.widgets import insert_formatted


__title__ = _("News")

__icon__ = addDataPrefix("glade/panel_annotation.svg")

__desc__ = _("List of server news")


class Sidepanel():

    def load(self, widgets, connection, lounge):
        self.widgets = widgets

        __widget__ = lounge.news_list

        connection.nm.connect("readNews", self.onNewsItem)

        return __widget__

    def onNewsItem(self, nm, news):
        weekday, month, day, title, details = news

        dtitle = "%s, %s %s: %s" % (weekday, month, day, title)
        label = Gtk.Label(label=dtitle)
        label.props.width_request = 300
        label.props.xalign = 0
        label.set_ellipsize(Pango.EllipsizeMode.END)
        expander = Gtk.Expander()
        expander.set_label_widget(label)
        expander.set_tooltip_text(title)
        textview = Gtk.TextView()
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.props.pixels_above_lines = 4
        textview.props.pixels_below_lines = 4
        textview.props.right_margin = 2
        textview.props.left_margin = 6

        tb_iter = textview.get_buffer().get_end_iter()
        insert_formatted(textview, tb_iter, details)

        alignment = Gtk.Alignment()
        alignment.set_padding(3, 6, 12, 0)
        alignment.props.xscale = 1
        alignment.add(textview)

        expander.add(alignment)
        expander.show_all()
        self.widgets["newsVBox"].pack_start(expander, False, False, 0)
