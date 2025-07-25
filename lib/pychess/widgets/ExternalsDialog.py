import asyncio
import shutil
import os
import stat

from gi.repository import Gtk

# from pychess.ic import TimeSeal
from pychess.Savers import pgn
from pychess.System import conf
from pychess.System import uistuff
from pychess.System import download_file_async
from pychess.System.prefix import getEngineDataPrefix
from pychess.widgets import mainwindow


class ExternalsDialog:
    def __init__(self):
        self.window = Gtk.Window(
            Gtk.WindowType.TOPLEVEL, title=_("Ask for permissions")
        )
        self.window.set_transient_for(mainwindow())
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        gtk_version = (Gtk.get_major_version(), Gtk.get_minor_version())
        if gtk_version >= (3, 12):
            vbox.props.margin_start = 9
            vbox.props.margin_end = 9
        else:
            vbox.props.margin_left = 9
            vbox.props.margin_right = 9
        vbox.props.margin_bottom = 9
        self.window.add(vbox)
        uistuff.keepWindowSize(
            "externalsdialog", self.window, (320, 240), uistuff.POSITION_CENTER
        )

        label = Gtk.Label(
            _(
                "Some PyChess features require further permission in order to download external components"
            )
        )
        vbox.pack_start(label, True, True, 0)

        box = Gtk.Box()
        check_button = Gtk.CheckButton(_("database querying needs scoutfish"))
        check_button.set_active(conf.get("download_scoutfish"))
        check_button.connect(
            "toggled", lambda w: conf.set("download_scoutfish", w.get_active())
        )
        box.add(check_button)
        link = "https://github.com/pychess/scoutfish"
        link_button = Gtk.LinkButton(link, link)
        box.add(link_button)
        vbox.pack_start(box, False, False, 0)

        box = Gtk.Box()
        check_button = Gtk.CheckButton(_("database opening tree needs chess_db"))
        check_button.set_active(conf.get("download_chess_db"))
        check_button.connect(
            "toggled", lambda w: conf.set("download_chess_db", w.get_active())
        )
        box.add(check_button)
        link = "https://github.com/pychess/chess_db"
        link_button = Gtk.LinkButton(link, link)
        box.add(link_button)
        vbox.pack_start(box, False, False, 0)

        # ICC doesn't support telnet connection any more
        # See https://github.com/pychess/pychess/issues/2315

        # box = Gtk.Box()
        # check_button = Gtk.CheckButton(_("ICC lag compensation needs timestamp"))
        # check_button.set_active(conf.get("download_timestamp"))
        # check_button.connect(
        # "toggled", lambda w: conf.set("download_timestamp", w.get_active())
        # )
        # box.add(check_button)
        # link = "http://download.chessclub.com/timestamp/"
        # link_button = Gtk.LinkButton(link, link)
        # box.add(link_button)
        # vbox.pack_start(box, False, False, 0)

        check_button = Gtk.CheckButton(_("Don't show this dialog on startup."))
        check_button.set_active(conf.get("dont_show_externals_at_startup"))
        check_button.connect(
            "toggled",
            lambda w: conf.set("dont_show_externals_at_startup", w.get_active()),
        )
        vbox.pack_start(check_button, True, True, 0)

        buttonbox = Gtk.ButtonBox()
        close_button = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        close_button.connect("clicked", self.on_close_clicked)
        self.window.connect("delete_event", lambda w, a: self.window.destroy())
        buttonbox.add(close_button)
        vbox.pack_start(buttonbox, False, False, 0)

    def show(self):
        self.window.show_all()
        self.window.present()

    def on_close_clicked(self, button):
        async def coro():
            altpath = getEngineDataPrefix()
            if pgn.scoutfish_path is None and conf.get("download_scoutfish"):
                binary = (
                    "https://github.com/pychess/scoutfish/releases/download/20170627/%s"
                    % pgn.scoutfish
                )
                filename = await download_file_async(binary)
                if filename is not None:
                    dest = shutil.move(filename, os.path.join(altpath, pgn.scoutfish))
                    os.chmod(dest, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
                    pgn.scoutfish_path = dest

            if pgn.chess_db_path is None and conf.get("download_chess_db"):
                binary = (
                    "https://github.com/pychess/chess_db/releases/download/20170627/%s"
                    % pgn.parser
                )
                filename = await download_file_async(binary)
                if filename is not None:
                    dest = shutil.move(filename, os.path.join(altpath, pgn.parser))
                    os.chmod(dest, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
                    pgn.chess_db_path = dest

            # ICC doesn't support telnet connection any more
            # See https://github.com/pychess/pychess/issues/2315

            # if TimeSeal.timestamp_path is None and conf.get("download_timestamp"):
            # binary = (
            # "http://download.chessclub.com.s3.amazonaws.com/timestamp/%s"
            # % TimeSeal.timestamp
            # )
            # filename = await download_file_async(binary)
            # if filename is not None:
            # dest = shutil.move(
            # filename, os.path.join(altpath, TimeSeal.timestamp)
            # )
            # os.chmod(dest, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
            # TimeSeal.timestamp_path = dest

        asyncio.create_task(coro())

        self.window.emit("delete-event", None)
