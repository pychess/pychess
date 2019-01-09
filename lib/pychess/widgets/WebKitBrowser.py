from gi.repository import Gtk, WebKit


def open_link(label, url):
    """ Gtk.Label() can use this like label.connect("activate-link", open_link) """
    WebKitBrowser(url)
    return True


class WebKitBrowser:
    def __init__(self, url):
        from pychess.System.uistuff import keepWindowSize
        self.window = Gtk.Window()
        keepWindowSize("webkitbrowser", self.window, (800, 600))

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(self.vbox)

        self.box = Gtk.Box()

        self.toolbar = Gtk.Toolbar()
        self.box.pack_start(self.toolbar, False, False, 0)

        self.go_back_button = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_BACK)
        self.toolbar.insert(self.go_back_button, -1)

        self.go_forward_button = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_FORWARD)
        self.toolbar.insert(self.go_forward_button, -1)

        self.go_refresh_button = Gtk.ToolButton(stock_id=Gtk.STOCK_REFRESH)
        self.toolbar.insert(self.go_refresh_button, -1)

        self.url = Gtk.Entry()
        self.box.pack_start(self.url, True, True, 0)

        self.search_entry = Gtk.SearchEntry()
        self.box.pack_start(self.search_entry, False, False, 0)

        self.vbox.pack_start(self.box, False, False, 0)

        self.view = WebKit.WebView()
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add(self.view)

        self.vbox.pack_start(self.scrolled_window, True, True, 0)

        self.window.show_all()

        self.view.connect("load-committed", self.check_buttons)
        self.view.connect("title-changed", self.change_title)

        self.url.connect("activate", self.go)
        self.search_entry.connect("activate", self.search)
        self.go_back_button.connect("clicked", self.go_back)
        self.go_forward_button.connect("clicked", self.go_forward)
        self.go_refresh_button.connect("clicked", self.refresh)

        self.view.open(url)
        self.view.show()

    def go(self, widget):
        link = self.url.get_text()
        if link.startswith("http://"):
            self.view.open(link)
        else:
            self.view.open("http://" + link)
        self.view.show()

    def search(self, widget):
        text = self.search_entry.get_text()
        text = text.replace(" ", "+")
        self.url.set_text("http://www.google.com/search?q=" + text)
        self.search_entry.set_text("")
        self.go(self)

    def check_buttons(self, widget, data):
        uri = widget.get_main_frame().get_uri()
        self.url.set_text(uri)
        self.go_back_button.set_sensitive(self.view.can_go_back())
        self.go_forward_button.set_sensitive(self.view.can_go_forward())

    def change_title(self, widget, data, arg):
        title = widget.get_main_frame().get_title()
        self.window.set_title(title)

    def go_back(self, widget):
        self.view.go_back()

    def go_forward(self, widget):
        self.view.go_forward()

    def refresh(self, widget):
        self.view.reload()
