from __future__ import absolute_import

from gi.repository import GLib

from pychess.compat import unicode
from pychess.System import conf
from pychess.Utils.const import ACTION_MENU_ITEMS

################################################################################
# Main menubar MenuItem classes to keep track of menu widget states            #
################################################################################


class GtkMenuItem(object):
    def __init__(self,
                 name,
                 sensitive=False,
                 label=None,
                 tooltip=None):
        assert isinstance(sensitive, bool)
        assert label is None or isinstance(label, str)
        self.name = name
        self._sensitive = sensitive
        self._label = label
        self._tooltip = tooltip

    @property
    def sensitive(self):
        return self._sensitive

    @sensitive.setter
    def sensitive(self, sensitive):
        assert isinstance(sensitive, bool)
        self._sensitive = sensitive
        self._set_widget("sensitive", sensitive)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        assert isinstance(label, str) or isinstance(label, unicode)
        self._label = label
        self._set_widget("label", label)

    @property
    def tooltip(self):
        return self._tooltip

    @tooltip.setter
    def tooltip(self, tooltip):
        assert isinstance(tooltip, str) or isinstance(tooltip, unicode)
        self._tooltip = tooltip
        self._set_widget("tooltip-text", tooltip)

    def _set_widget(self, prop, value):
        from . import gamewidget
        if gamewidget.getWidgets()[self.name].get_property(prop) != value:
            # print("setting %s property %s to %s.." % (self.name, prop, str(value)))

            def do_set_menu_item_prop():
                gamewidget.getWidgets()[self.name].set_property(prop, value)

            GLib.idle_add(do_set_menu_item_prop)
            # print(" success (%s %s = \"%s\")" % (
            #     self.name, prop, gamewidget.getWidgets()[self.name].get_property(prop)))

    def update(self):
        self._set_widget("sensitive", self._sensitive)
        if self._label is not None:
            self._set_widget("label", self._label)
        if self._tooltip is not None:
            self._set_widget("tooltip-text", self._tooltip)


class GtkMenuToggleButton(GtkMenuItem):
    def __init__(self,
                 name,
                 sensitive=False,
                 active=False,
                 label=None):
        assert isinstance(active, bool)
        GtkMenuItem.__init__(self, name, sensitive, label)
        self._active = active

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        assert isinstance(active, bool)
        self._active = active
        self._set_widget("active", active)

    def update(self):
        GtkMenuItem.update(self)
        self._set_widget("active", self._active)


class MenuItemsDict(dict):
    """
    :Description: Keeps track of menubar menuitem widgets that need to be managed on a game
    by game basis. Each menuitem writes through its respective widget state to
    the GUI if we are encapsulated in the gamewidget that's focused/infront
    """

    ANAL_MENU_ITEMS = ("analyze_game1", "analyzer_check", "inv_analyzer_check",
                       "ana_combobox", "inv_ana_combobox")
    VIEW_MENU_ITEMS = ("hint_mode", "spy_mode")

    def __init__(self):
        dict.__init__(self)
        for item in ACTION_MENU_ITEMS:
            dict.__setitem__(self, item, GtkMenuItem(item))
        for item in self.ANAL_MENU_ITEMS:
            dict.__setitem__(self, item, GtkMenuItem(item, sensitive=True))
        for item in self.VIEW_MENU_ITEMS:
            dict.__setitem__(self, item, GtkMenuToggleButton(item, active=conf.get(item, False)))
