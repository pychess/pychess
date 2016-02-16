from __future__ import absolute_import

from gi.repository import Gtk

from pychess.System import uistuff
from pychess.System.idle_add import idle_add


class DiscovererDialog:
    @classmethod
    def init(cls, discoverer):
        assert not hasattr(cls, "widgets"), "Show can only be called once"
        cls.widgets = uistuff.GladeWidgets("discovererDialog.glade")

        # =======================================================================
        # Clear glade defaults
        # =======================================================================
        for child in cls.widgets["enginesTable"].get_children():
            cls.widgets["enginesTable"].remove(child)

        # =======================================================================
        # Connect us to the discoverer
        # =======================================================================
        discoverer.connect("engine_discovered", cls._onEngineDiscovered)
        discoverer.connect("all_engines_discovered",
                           cls._onAllEnginesDiscovered)
        cls.finished = False
        cls.throbber = None
        cls.nameToBar = {}

    @classmethod
    def show(cls, discoverer, mainwindow, binnames):
        if cls.finished:
            return

        # ======================================================================
        # Insert the names to be discovered
        # ======================================================================
        for i, name in enumerate(binnames):
            label = Gtk.Label(label=name + ":")
            label.props.xalign = 1
            cls.widgets["enginesTable"].attach(label, 0, 1, i, i + 1)
            bar = Gtk.ProgressBar()
            cls.widgets["enginesTable"].attach(bar, 1, 2, i, i + 1)
            cls.nameToBar[name] = bar

        # =======================================================================
        # Add throbber
        # =======================================================================

        cls.throbber = Gtk.Spinner()
        cls.throbber.set_size_request(50, 50)
        cls.widgets["throbberDock"].add(cls.throbber)

        # =======================================================================
        # Show the window
        # =======================================================================
        cls.widgets["discovererDialog"].set_position(
            Gtk.WindowPosition.CENTER_ON_PARENT)
        cls.widgets["discovererDialog"].set_modal(True)
        cls.widgets["discovererDialog"].set_transient_for(mainwindow)
        cls.widgets["discovererDialog"].show_all()

        cls.throbber.start()

    @classmethod
    @idle_add
    def _onEngineDiscovered(cls, discoverer, binname, xmlenginevalue):
        if binname in cls.nameToBar:
            bar = cls.nameToBar[binname]
            bar.props.fraction = 1

    @classmethod
    @idle_add
    def _onAllEnginesDiscovered(cls, discoverer):
        cls.finished = True
        if cls.throbber:
            cls.throbber.stop()
        cls.widgets["discovererDialog"].hide()
