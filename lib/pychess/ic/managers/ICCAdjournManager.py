from __future__ import absolute_import

from gi.repository import GObject

from pychess.ic.icc import DG_GAMELIST_BEGIN, DG_GAMELIST_ITEM
from pychess.ic.managers.AdjournManager import AdjournManager


class ICCAdjournManager(AdjournManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_GAMELIST_BEGIN, self.on_icc_gamelist_begin)
        self.connection.expect_dg_line(DG_GAMELIST_ITEM, self.on_icc_gamelist_item)

        self.connection.client.run_command("set-2 %s 1" % DG_GAMELIST_BEGIN)
        self.connection.client.run_command("set-2 %s 1" % DG_GAMELIST_ITEM)

        self.queryAdjournments()
        self.queryHistory()
        self.queryLibrary()

    def on_icc_gamelist_begin(self, data):
        # command {parameters} nhits first last {summary}
        # command is one of search, history, liblist, or stored
        # TODO
        pass

    def on_icc_gamelist_item(self, data):
        # index id event date time white-name white-rating black-name black-rating rated rating-type
        # wild init-time-W inc-W init-time-B inc-B eco status color mode {note} here
        # TODO
        pass

    def queryLibrary(self, owner=None):
        if owner is None:
            self.connection.client.run_command("liblist")
        else:
            self.connection.client.run_command("liblist %s" % owner)
