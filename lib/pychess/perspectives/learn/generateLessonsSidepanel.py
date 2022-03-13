import asyncio

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.System import conf
from pychess.Utils.const import COLUMN_ROW_RESET, GTK_ICON_VIEW_REFRESH
from pychess.widgets import mainwindow


def generateLessonsSidepanel(solving_progress, learn_category_id, entries, start_from):
    """
    generateLessonsSidepanel returns a class to be used as a panel by Gtk. More
    specifically, that class is meant to be named Sidepanel.

    generateLessonsSidepanel allows to avoid duplicate code between
    PuzzlesPanel and LessonsPanel.py.
    """
    class Sidepanel():
        def load(self, persp):
            self.persp = persp
            self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            self.tv = Gtk.TreeView()

            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(_("Title"), renderer, text=1)
            self.tv.append_column(column)

            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(_("Source"), renderer, text=2)
            self.tv.append_column(column)

            renderer = Gtk.CellRendererProgress()
            column = Gtk.TreeViewColumn(_("Progress"), renderer, text=3, value=4)
            column.set_expand(True)
            self.tv.append_column(column)

            renderer = Gtk.CellRendererPixbuf()
            column = Gtk.TreeViewColumn(_("Reset"), renderer, icon_name=5)
            column.set_name(COLUMN_ROW_RESET)
            self.tv.append_column(column)

            self.tv.connect("row-activated", self.row_activated)

            def on_progress_updated(solving_progress, key, progress):
                for i, row in enumerate(self.store):
                    if row[0] == key:
                        progress_ratio_string, percent, reset_icon = self._compute_progress_info(progress)
                        treeiter = self.store.get_iter(Gtk.TreePath(i))
                        self.store[treeiter][3] = progress_ratio_string
                        self.store[treeiter][4] = percent
                        self.store[treeiter][5] = reset_icon
            solving_progress.connect("progress_updated", on_progress_updated)

            self.store = Gtk.ListStore(str, str, str, str, int, str)

            async def coro():
                for file_name, title, author in entries:
                    progress = solving_progress.get(file_name)
                    progress_ratio_string, percent, reset_icon = self._compute_progress_info(progress)
                    self.store.append([file_name, title, author, progress_ratio_string, percent, reset_icon])
                    await asyncio.sleep(0)
            create_task(coro())

            self.tv.set_model(self.store)
            self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
            self.tv.set_cursor(conf.get("learncombo%s" % learn_category_id))

            scrollwin = Gtk.ScrolledWindow()
            scrollwin.add(self.tv)
            scrollwin.show_all()

            self.box.pack_start(scrollwin, True, True, 0)
            self.box.show_all()

            return self.box

        def row_activated(self, widget, path, col):
            if path is None:
                return
            else:
                filename, title, *_ = entries[path[0]]
                if col.get_name() == COLUMN_ROW_RESET:
                    self._reset_progress_file(filename, title)
                else:
                    conf.set("categorycombo", learn_category_id)
                    from pychess.widgets.TaskerManager import learn_tasker
                    learn_tasker.learn_combo.set_active(path[0])
                    start_from(filename)

        @staticmethod
        def _compute_progress_info(progress):
            solved = progress.count(1)
            skipped = progress.count(2)
            percent = 0 if solved == 0 else round((solved * 100.) / len(progress))
            reset_icon = None if solved == 0 and skipped == 0 else GTK_ICON_VIEW_REFRESH
            return "%s / %s" % (solved, len(progress)), percent, reset_icon

        def _reset_progress_file(self, filename, title):
            progress = solving_progress[filename]
            _str, _percent, reset_icon = self._compute_progress_info(progress)
            if reset_icon is not None:
                dialog = Gtk.MessageDialog(
                    mainwindow(), 0,
                    Gtk.MessageType.QUESTION,
                    Gtk.ButtonsType.OK_CANCEL,
                    _('This will reset the progress to 0 for the puzzle "{title}"').format(title=title),
                )
                response = dialog.run()
                if response == Gtk.ResponseType.OK:
                    solving_progress[filename] = [0] * len(progress)
                    self.persp.update_progress(None, None, None)
                dialog.destroy()
    return Sidepanel
