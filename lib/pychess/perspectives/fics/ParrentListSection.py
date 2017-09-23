from gi.repository import Gtk, GdkPixbuf

from pychess.ic.FICSObjects import FICSChallenge

SEPARATOR, ACCEPT, ASSESS, OBSERVE, FOLLOW, CHAT, CHALLENGE, FINGER, ARCHIVED = range(9)


def cmp(x, y):
    return (x > y) - (x < y)


class ParrentListSection():
    """ Parrent for sections mainly consisting of a large treeview """

    def button_press_event(self, treeview, event):
        if event.button == 3:  # right click
            pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is not None:
                path, col = pathinfo[0], pathinfo[1]
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.menu.show_all()
                self.menu.popup(None, None, None, None, event.button,
                                Gtk.get_current_event_time())
            return True
        return False

    def createLocalMenu(self, items):
        ITEM_MAP = {
            ACCEPT: (_("Accept"), self.on_accept),
            ASSESS: (_("Assess"), self.on_assess),
            OBSERVE: (_("Observe"), self.on_observe),
            FOLLOW: (_("Follow"), self.on_follow),
            CHAT: (_("Chat"), self.on_chat),
            CHALLENGE: (_("Challenge"), self.on_challenge),
            FINGER: (_("Finger"), self.on_finger),
            ARCHIVED: (_("Archived"), self.on_archived), }

        self.menu = Gtk.Menu()
        for item in items:
            if item == SEPARATOR:
                menu_item = Gtk.SeparatorMenuItem()
            else:
                label, callback = ITEM_MAP[item]
                menu_item = Gtk.MenuItem(label)
                menu_item.connect("activate", callback)
            self.menu.append(menu_item)
        self.menu.attach_to_widget(self.tv, None)

    def addColumns(self, treeview, *columns, **keyargs):
        if "hide" in keyargs:
            hide = keyargs["hide"]
        else:
            hide = []
        if "pix" in keyargs:
            pix = keyargs["pix"]
        else:
            pix = []
        for i, name in enumerate(columns):
            if i in hide:
                continue
            if i in pix:
                crp = Gtk.CellRendererPixbuf()
                crp.props.xalign = .5
                column = Gtk.TreeViewColumn(name, crp, pixbuf=i)
            else:
                crt = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(name, crt, text=i)
                column.set_resizable(True)
            column.set_sort_column_id(i)
            # prevent columns appear choppy
            column.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)

            column.set_reorderable(True)
            treeview.append_column(column)

    def lowLeftSearchPosFunc(self, tv, search_dialog, user_data):
        alloc = tv.get_allocation()
        window = tv.get_toplevel().get_window()
        x_loc = alloc.x + window.get_position()[0]
        y_loc = alloc.y + window.get_position()[1] + alloc.height
        search_dialog.move(x_loc, y_loc)
        search_dialog.show_all()

    def pixCompareFunction(self, treemodel, iter0, iter1, column):
        pix0 = treemodel.get_value(iter0, column)
        pix1 = treemodel.get_value(iter1, column)
        if isinstance(pix0, GdkPixbuf.Pixbuf) and isinstance(pix1,
                                                             GdkPixbuf.Pixbuf):
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)

    def timeCompareFunction(self, treemodel, iter0, iter1, column):
        (minute0, minute1) = (treemodel.get_value(iter0, 8),
                              treemodel.get_value(iter1, 8))
        return cmp(minute0, minute1)

    def on_accept(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        if isinstance(sought, FICSChallenge):
            self.connection.om.acceptIndex(sought.index)
        else:
            self.connection.om.playIndex(sought.index)

        try:
            message = self.messages[hash(sought)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(sought)]

    def on_assess(self, widget):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        player1 = self.connection.username
        player2 = sought.player.name
        game_type = sought.game_type.short_fics_name
        self.connection.glm.assess(player1, player2, game_type)
        self.assess_sent = True

    def on_observe(self, widget, *args):
        player = self.getSelectedPlayer()
        if player is not None:
            if player.game is not None:
                self.connection.bm.observe(player.game)
            else:
                self.connection.bm.observe(None, player=player)

    def on_follow(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.bm.follow(player)

    def on_chat(self, button):
        player = self.getSelectedPlayer()
        if player is None:
            return
        self.lounge.chat.openChatWithPlayer(player.name)
        # TODO: isadmin og type

    def on_challenge(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.lounge.seek_challenge.onChallengeButtonClicked(widget, player)

    def on_finger(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.fm.finger(player.name)
            self.lounge.finger_sent = True

    def on_archived(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.adm.queryAdjournments(player.name)
            self.connection.adm.queryHistory(player.name)
            self.connection.adm.queryJournal(player.name)
