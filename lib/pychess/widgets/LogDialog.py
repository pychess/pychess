# -*- coding: UTF-8 -*-

import time
import logging

from gi.repository import Gtk, Gdk, Pango, GLib

from pychess.System import uistuff
from pychess.System.LogEmitter import logemitter


class InformationWindow:
    @classmethod
    def _init(cls):
        cls.tagToIter = {}
        cls.tagToPage = {}
        cls.pathToPage = {}
        cls.tagToTime = {}

        cls.window = Gtk.Window()
        cls.window.set_title(_("PyChess Information Window"))
        cls.window.set_border_width(12)
        cls.window.set_icon_name("pychess")
        uistuff.keepWindowSize("logdialog", cls.window, (640, 480))
        mainHBox = Gtk.HBox()
        mainHBox.set_spacing(6)
        cls.window.add(mainHBox)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        mainHBox.pack_start(sw, False, True, 0)
        cls.treeview = Gtk.TreeView(Gtk.TreeStore(str))
        cls.treeview.append_column(Gtk.TreeViewColumn("",
                                                      Gtk.CellRendererText(),
                                                      text=0))
        cls.treeview.set_headers_visible(False)
        cls.treeview.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        sw.add(cls.treeview)
        cls.pages = Gtk.Notebook()
        cls.pages.set_show_tabs(False)
        cls.pages.set_show_border(False)
        mainHBox.pack_start(cls.pages, True, True, 0)

        mainHBox.show_all()

        def selectionChanged(selection):
            treestore, iter = selection.get_selected()
            if iter:
                child = cls.pathToPage[treestore.get_path(iter).to_string()][
                    "child"]
                cls.pages.set_current_page(cls.pages.page_num(child))

        cls.treeview.get_selection().connect("changed", selectionChanged)

    @classmethod
    def show(cls):
        cls.window.show()

    @classmethod
    def hide(cls):
        cls.window.hide()

    @classmethod
    def newMessage(cls, tag, timestamp, message, importance):
        def _newMessage(cls, tag, timestamp, message, importance):
            textview = cls._getPageFromTag(tag)["textview"]

            if tag not in cls.tagToTime or timestamp - cls.tagToTime[tag] >= 1:
                t = time.strftime("%H:%M:%S", time.localtime(timestamp))
                textview.get_buffer().insert_with_tags_by_name(
                    textview.get_buffer().get_end_iter(),
                    "\n%s\n%s\n" % (t, "-" * 60), str(logging.INFO))
                cls.tagToTime[tag] = timestamp

            if not message.endswith("\n"):
                message = "%s\n" % message
            textview.get_buffer().insert_with_tags_by_name(
                textview.get_buffer().get_end_iter(), message, str(importance))

        GLib.idle_add(_newMessage, cls, tag, timestamp, message, importance)

    @classmethod
    def _createPage(cls, parent_iter, tag):
        name = tag[-1]
        if isinstance(name, int):
            name = str(name)
        iter = cls.treeview.get_model().append(parent_iter, (name, ))
        cls.tagToIter[tag] = iter

        widgets = uistuff.GladeWidgets("findbar.glade")
        frame = widgets["frame"]
        frame.unparent()
        frame.show_all()

        uistuff.keepDown(widgets["scrolledwindow"])
        textview = widgets["textview"]
        tb = textview.get_buffer()
        tb.create_tag(str(logging.DEBUG), family='Monospace')
        tb.create_tag(
            str(logging.INFO),
            family='Monospace',
            weight=Pango.Weight.BOLD)
        tb.create_tag(
            str(logging.WARNING),
            family='Monospace',
            foreground="red")
        tb.create_tag(
            str(logging.ERROR),
            family='Monospace',
            weight=Pango.Weight.BOLD,
            foreground="red")

        findbar = widgets["findbar"]
        findbar.hide()
        # Make searchEntry and "out of label" share height with the buttons
        widgets["prevButton"].connect(
            "size-allocate",
            lambda w, alloc: widgets["searchEntry"].set_size_request(-1, alloc.height) or widgets["outofLabel"].set_size_request(-1, alloc.height - 2))

        # Make "out of label" more visually distinct
        uistuff.makeYellow(widgets["outofLabel"])
        widgets["outofLabel"].hide()

        widgets["closeButton"].connect("clicked",
                                       lambda w: widgets["findbar"].hide())

        # Connect showing/hiding of the findbar
        cls.window.connect("key-press-event", cls.onTextviewKeypress, widgets)
        widgets["findbar"].connect("key-press-event", cls.onFindbarKeypress)

        widgets["searchEntry"].connect("changed", cls.onSearchChanged, widgets)

        widgets["prevButton"].connect("clicked",
                                      lambda w: cls.searchJump(-1, widgets))
        widgets["nextButton"].connect("clicked",
                                      lambda w: cls.searchJump(1, widgets))

        cls.pages.append_page(frame, None)
        page = {"child": frame, "textview": textview}
        cls.tagToPage[tag] = page
        cls.pathToPage[cls.treeview.get_model().get_path(iter).to_string(
        )] = page

        cls.treeview.expand_all()

    @classmethod
    def _getPageFromTag(cls, tag):
        if isinstance(tag, list):
            tag = tuple(tag)
        elif not isinstance(tag, tuple):
            tag = (tag, )

        if tag in cls.tagToPage:
            return cls.tagToPage[tag]

        for i in range(len(tag) - 1):
            subtag = tag[:-i - 1]
            if subtag in cls.tagToIter:
                newtag = subtag + (tag[len(subtag)], )
                iter = cls.tagToIter[subtag]
                cls._createPage(iter, newtag)
                return cls._getPageFromTag(tag)

        cls._createPage(None, tag[:1])
        return cls._getPageFromTag(tag)

    @classmethod
    def onSearchChanged(cls, search_entry, widgets):
        pattern = search_entry.get_text().lower()
        widgets["outofLabel"].props.visible = bool(pattern)
        if not pattern:
            return

        text = widgets["textview"].get_buffer().props.text.lower()

        widgets["outofLabel"].hits = []
        widgets["outofLabel"].searchCurrent = -1
        i = -len(pattern)
        while True:
            i = text.find(pattern, i + len(pattern))
            if i != -1:
                widgets["outofLabel"].hits.append(i)
            else:
                break

        cls.searchJump(1, widgets)

    @classmethod
    def searchJump(cls, count, widgets):
        if not hasattr(widgets["outofLabel"], "hits"):
            return
        amount = len(widgets["outofLabel"].hits)
        if not amount:
            widgets["outofLabel"].set_text("0 %s 0" % _("of"))
        else:
            widgets["outofLabel"].searchCurrent += count
            current = widgets["outofLabel"].searchCurrent % amount
            widgets["outofLabel"].set_text("%d %s %d" %
                                           (current + 1, _("of"), amount))
            goto = widgets["outofLabel"].hits[current]
            iter0 = widgets["textview"].get_buffer().get_iter_at_offset(goto)
            length = len(widgets["searchEntry"].get_text())
            iter1 = widgets["textview"].get_buffer().get_iter_at_offset(goto +
                                                                        length)
            widgets["textview"].get_buffer().select_range(iter0, iter1)
            widgets["textview"].scroll_to_iter(iter0, 0.2, False, 0.5, 0.5)

    @classmethod
    def onTextviewKeypress(cls, textview, event, widgets):
        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval in (ord("f"), ord("F")):
                widgets["findbar"].props.visible = not widgets[
                    "findbar"].props.visible
                if widgets["findbar"].props.visible:
                    signal = widgets["searchEntry"].connect_after(
                        "draw",
                        lambda w, e: w.grab_focus() or widgets["searchEntry"].disconnect(signal))

    @classmethod
    def onFindbarKeypress(cls, findbar, event):
        if Gdk.keyval_name(event.keyval) == "Escape":
            findbar.props.visible = False

    ################################################################################
    # Add early messages and connect for new                                       #
    ################################################################################


InformationWindow._init()


def addMessage(emitter, message):
    task, timestamp, message, type = message
    InformationWindow.newMessage(task, timestamp, message, type)


for message in logemitter.messages:
    addMessage(logemitter, message)
logemitter.messages = None

logemitter.connect("logged", addMessage)

################################################################################
# External functions                                                           #
################################################################################

destroy_funcs = []


def add_destroy_notify(func):
    destroy_funcs.append(func)


def _destroy_notify(widget, *args):
    [func() for func in destroy_funcs]
    return True


InformationWindow.window.connect("delete-event", _destroy_notify)


def show():
    InformationWindow.show()


def hide():
    InformationWindow.hide()


if __name__ == "__main__":
    show()
    InformationWindow.window.connect("delete-event", Gtk.main_quit)
    Gtk.main()
