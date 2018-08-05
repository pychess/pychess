# -*- coding: UTF-8 -*-

import re
from math import floor

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Gdk

from pychess.Utils import prettyPrintScore
from pychess.Utils.const import WHITE, BLACK, FEN_EMPTY, reprResult, reprSign, FAN_PIECES
from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.Utils.Cord import Cord
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import toSAN, toFAN, FCORD, TCORD
from pychess.Savers.pgn import move_count, nag2symbol, parseTimeControlTag
from pychess.widgets.ChessClock import formatTime
from pychess.widgets.LearnInfoBar import LearnInfoBar
from pychess.widgets import insert_formatted, preferencesDialog, mainwindow
from pychess.widgets.Background import isDarkTheme


# --- Constants

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_annotation.svg")
__desc__ = _("Annotated game")

EMPTY_BOARD = LBoard()
EMPTY_BOARD.applyFen(FEN_EMPTY)


css = """
GtkButton#rounded {
    border-radius: 20px;
}
"""


def add_provider(widget):
    screen = widget.get_screen()
    style = widget.get_style_context()
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode('utf-8'))
    style.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)


# -- Documentation
"""
We are maintaining a list of nodes to help manipulate the textbuffer.
Node can represent a move, comment or variation (start/end) marker.
Nodes are dicts with keys like:
board  = in move node it's the lboard of move
         in comment node it's the lboard where the comment belongs to
         in end variation marker node it's the first lboard of the variation
         in start variation marker is's None
start  = the beginning offest of the node in the textbuffer
end    = the ending offest of the node in the textbuffer
parent = the parent lboard if the node is a move in a variation, otherwise None
vari   = in end variation node it's the start variation marker node
         in start variation node it's None
level  = depth in variation tree (0 for mainline nodes, 1 for first level variation moves, etc.)
index  = in comment nodes the index of comment if more exist for a move
"""


# -- Widget

class Sidepanel:
    def load(self, gmwidg):
        """
        The method initializes the widget, attached events, internal variables, layout...
        """

        # Internal variables
        self.nodelist = []
        self.boardview = gmwidg.board.view
        self.gamemodel = gmwidg.gamemodel
        self.variation_to_remove = None
        if self.gamemodel is None:
            return None

        # Internal objects/helpers
        self.cursor_standard = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
        self.cursor_hand = Gdk.Cursor.new(Gdk.CursorType.HAND2)

        # Header text area
        self.header_textview = Gtk.TextView()
        self.header_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.header_textview.set_editable(False)
        self.header_textview.set_cursor_visible(False)
        self.header_textbuffer = self.header_textview.get_buffer()

        # Header text tags
        self.header_textbuffer.create_tag("head1")
        self.header_textbuffer.create_tag("head2", weight=Pango.Weight.BOLD)

        # Move text area
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()

        # Load of the preferences
        def cb_config_changed(*args):
            self.fetch_chess_conf()
            self.tag_move.set_property("font_desc", self.font)
            for i in range(len(self.tag_vari_depth)):
                self.tag_vari_depth[i].set_property("font_desc", self.font)
            self.update()
        self.fetch_chess_conf()

        self.cids_conf = []
        self.cids_conf.append(conf.notify_add("movetextFont", cb_config_changed))
        self.cids_conf.append(conf.notify_add("figuresInNotation", cb_config_changed))
        self.cids_conf.append(conf.notify_add("showEmt", cb_config_changed))
        self.cids_conf.append(conf.notify_add("showBlunder", cb_config_changed))
        self.cids_conf.append(conf.notify_add("showEval", cb_config_changed))

        # Move text tags
        self.tag_remove_variation = self.textbuffer.create_tag("remove-variation")
        self.tag_new_line = self.textbuffer.create_tag("new_line")

        self.tag_move = self.textbuffer.create_tag("move", font_desc=self.font)
        palette = self.get_palette()
        self.tag_vari_depth = []
        for i in range(64):
            tag = self.textbuffer.create_tag("variation-depth-%d" % i, font_desc=self.font, foreground=palette[i % len(palette)], style="italic", left_margin=15 * (i + 1))
            self.tag_vari_depth.append(tag)

        self.textbuffer.create_tag("scored0")
        self.textbuffer.create_tag("scored1", foreground_rgba=Gdk.RGBA(0.2, 0, 0, 1))
        self.textbuffer.create_tag("scored2", foreground_rgba=Gdk.RGBA(0.4, 0, 0, 1))
        self.textbuffer.create_tag("scored3", foreground_rgba=Gdk.RGBA(0.6, 0, 0, 1))
        self.textbuffer.create_tag("scored4", foreground_rgba=Gdk.RGBA(0.8, 0, 0, 1))
        self.textbuffer.create_tag("scored5", foreground_rgba=Gdk.RGBA(1.0, 0, 0, 1))
        self.textbuffer.create_tag("emt", foreground="grey")
        self.textbuffer.create_tag("comment", foreground="#6e71ec")
        self.textbuffer.create_tag("lesson-comment", foreground="green", font_desc=self.font)
        self.textbuffer.create_tag("margin", left_margin=4)

        self.selected_tag = self.textbuffer.create_tag("selected", background_full_height=True, background=self.get_slected_background())

        # Events
        self.cids_textview = [
            self.textview.connect("motion-notify-event", self.motion_notify_event),
            self.textview.connect("button-press-event", self.button_press_event),
            self.textview.connect("style-updated", self.on_style_updated)
        ]
        self.cid_shown_changed = self.boardview.connect("shownChanged", self.on_shownChanged)
        self.cid_remove_variation = self.tag_remove_variation.connect("event", self.tag_event_handler)
        self.cids_gamemodel = [
            self.gamemodel.connect_after("game_loaded", self.on_game_loaded),
            self.gamemodel.connect_after("game_changed", self.on_game_changed),
            self.gamemodel.connect_after("game_started", self.update),
            self.gamemodel.connect_after("game_ended", self.update),
            self.gamemodel.connect_after("moves_undone", self.on_moves_undone),
            self.gamemodel.connect_after("variation_undone", self.update),
            self.gamemodel.connect_after("opening_changed", self.update),
            self.gamemodel.connect_after("players_changed", self.on_players_changed),
            self.gamemodel.connect_after("game_terminated", self.on_game_terminated),
            self.gamemodel.connect("variation_added", self.variation_added),
            self.gamemodel.connect("variation_extended", self.variation_extended),
            self.gamemodel.connect("analysis_changed", self.analysis_changed),
            self.gamemodel.connect("analysis_finished", self.update),
        ]

        if self.gamemodel.lesson_game:
            self.cids_gamemodel.append(self.gamemodel.connect_after("learn_success", self.on_learn_success))

        # Layout
        __widget__ = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        __widget__.set_spacing(3)
        __widget__.pack_start(self.header_textview, False, False, 0)
        __widget__.pack_start(Gtk.Separator(), False, False, 0)

        self.choices_box = Gtk.Box()
        self.choices_box.connect("realize", add_provider)
        __widget__.pack_start(self.choices_box, False, False, 0)
        self.choices_enabled = True

        sw = Gtk.ScrolledWindow()
        sw.add(self.textview)
        __widget__.pack_start(sw, True, True, 0)

        if self.gamemodel.practice_game or self.gamemodel.lesson_game:
            self.infobar = LearnInfoBar(self.gamemodel, gmwidg.board, self)
            self.boardview.infobar = self.infobar
            __widget__.pack_start(self.infobar, False, False, 0)

        return __widget__

    def fetch_chess_conf(self):
        """
        The method retrieves few parameters from the configuration.
        """
        self.fan = conf.get("figuresInNotation")
        movetext_font = conf.get("movetextFont")
        self.font = Pango.font_description_from_string(movetext_font)
        self.showEmt = conf.get("showEmt")
        self.showBlunder = conf.get("showBlunder") and not self.gamemodel.isPlayingICSGame()
        self.showEval = conf.get("showEval") and not self.gamemodel.isPlayingICSGame()

    def on_game_terminated(self, model):
        """
        The method disconnects all the created events when the widget is destroyed
        at the end of the game.
        """
        for cid in self.cids_textview:
            self.textview.disconnect(cid)
        self.boardview.disconnect(self.cid_shown_changed)
        self.tag_remove_variation.disconnect(self.cid_remove_variation)
        for cid in self.cids_gamemodel:
            self.gamemodel.disconnect(cid)
        for cid in self.cids_conf:
            conf.notify_remove(cid)

    def get_palette(self):
        if isDarkTheme(self.textview):
            palette = ["#e5e5e5", "#35e119", "#ee3e34", "#24c6ee", "#a882bc", "#f09243", "#e475e5", "#c0c000"]  # white, green, red, aqua, purple, orange, fuchsia, ochre
        else:
            palette = ["#4b4b4b", "#51a745", "#ee3e34", "#3965a8", "#a882bc", "#f09243", "#772120", "#c0c000"]  # black, green, red, blue, purple, orange, brown, ochre
        return palette

    def get_slected_background(self):
        return "grey" if isDarkTheme(self.textview) else "lightgrey"

    def on_style_updated(self, widget):
        palette = self.get_palette()
        for i in range(64):
            self.tag_vari_depth[i].set_property("foreground", palette[i % len(palette)])

        self.selected_tag.set_property("background", self.get_slected_background())

    def tag_event_handler(self, tag, widget, event, iter):
        """
        The method handles the event specific to a tag, which is further processed
        by the button event of the main widget.
        """
        if (event.type == Gdk.EventType.BUTTON_PRESS) and (tag.get_property("name") == "remove-variation"):
            offset = iter.get_offset()
            node = None
            for n in self.nodelist:
                if offset >= n["start"] and offset < n["end"]:
                    node = n
                    break
            if node is None:
                return
            self.variation_to_remove = node
        return False

    def motion_notify_event(self, widget, event):
        """
        The method defines the applicable cursor (standard/hand)
        """
        if self.textview.get_window_type(event.window) not in (
           Gtk.TextWindowType.TEXT, Gtk.TextWindowType.PRIVATE):
            event.window.set_cursor(self.cursor_standard)
            return True

        if (event.is_hint):
            # (x, y, state) = event.window.get_pointer()
            (ign, x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            # state = event.get_state()

        (x, y) = self.textview.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y))

        ret = self.textview.get_iter_at_position(x, y)
        if len(ret) == 3:
            pos_is_over_text, it_at_pos, trailing = ret
        else:
            it_at_pos, trailing = ret

        if it_at_pos.get_child_anchor() is not None:
            event.window.set_cursor(self.cursor_hand)
            return True

        it = self.textview.get_iter_at_location(x, y)

        # https://gramps-project.org/bugs/view.php?id=9335
        if isinstance(it, Gtk.TextIter):
            offset = it.get_offset()
        else:
            offset = it[1].get_offset()

        for node in self.nodelist:
            if offset >= node["start"] and offset < node["end"] and "vari" not in node:
                event.window.set_cursor(self.cursor_hand)
                return True
        event.window.set_cursor(self.cursor_standard)
        return True

    def button_press_event(self, widget, event):
        """
        The method handles the click made on the widget, like showing the board
        editing a comment, or showing a local popup-menu.
        """

        # Detection of the node with the coordinates of the mouse
        (wx, wy) = event.get_coords()
        (x, y) = self.textview.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(wx), int(wy))
        it = self.textview.get_iter_at_location(x, y)

        # https://gramps-project.org/bugs/view.php?id=9335
        if isinstance(it, Gtk.TextIter):
            offset = it.get_offset()
        else:
            offset = it[1].get_offset()

        node = None
        for n in self.nodelist:
            if offset >= n["start"] and offset < n["end"]:
                node = n
                board = node["board"]
                break
        if node is None:
            return True
        # print("-------------------------------------------------------")
        # print("index is:", self.nodelist.index(node))
        # print(node)
        # print("-------------------------------------------------------")

        # Left click
        if event.button == 1:
            if "vari" in node:
                if self.variation_to_remove is not None:
                    node = self.variation_to_remove
                    self.remove_variation(node)
                    self.gamemodel.remove_variation(node["board"], node["parent"])
                    self.variation_to_remove = None
                return True
            elif "comment" in node:
                self.menu_edit_comment(board=board, index=node["index"])
            else:
                self.boardview.setShownBoard(board.pieceBoard)

        # Right click
        elif event.button == 3:
            self.menu = Gtk.Menu()

            if node is not None:
                position = -1
                for index, child in enumerate(board.children):
                    if isinstance(child, str):
                        position = index
                        break

                menuitem = Gtk.MenuItem(_("Refresh"))
                menuitem.connect('activate', self.menu_refresh)
                self.menu.append(menuitem)

                if len(self.gamemodel.boards) > 1 and board == self.gamemodel.boards[1].board and \
                        not self.gamemodel.boards[0].board.children:
                    menuitem = Gtk.MenuItem(_("Add start comment"))
                    menuitem.connect('activate', self.menu_edit_comment, self.gamemodel.boards[0].board, 0)
                    self.menu.append(menuitem)

                if position == -1:
                    menuitem = Gtk.MenuItem(_("Add comment"))
                    menuitem.connect('activate', self.menu_edit_comment, board, 0)
                else:
                    menuitem = Gtk.MenuItem(_("Edit comment"))
                    menuitem.connect('activate', self.menu_edit_comment, board, position)
                self.menu.append(menuitem)

                symbol_menu1 = Gtk.Menu()
                for nag, menutext in (("$1", _("Good move")),
                                      ("$2", _("Bad move")),
                                      ("$3", _("Excellent move")),
                                      ("$4", _("Very bad move")),
                                      ("$5", _("Interesting move")),
                                      ("$6", _("Suspicious move")),
                                      ("$7", _("Forced move"))):
                    menuitem = Gtk.MenuItem("%s %s" % (nag2symbol(nag), menutext))
                    menuitem.connect('activate', self.menu_move_attribute,
                                     board, nag)
                    symbol_menu1.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add move symbol"))
                menuitem.set_submenu(symbol_menu1)
                self.menu.append(menuitem)

                symbol_menu2 = Gtk.Menu()
                for nag, menutext in (("$10", _("Drawish")),
                                      ("$13", _("Unclear position")),
                                      ("$14", _("Slight advantage")),
                                      ("$16", _("Moderate advantage")),
                                      ("$18", _("Decisive advantage")),
                                      ("$20", _("Crushing advantage")),
                                      ("$22", _("Zugzwang")),
                                      ("$32", _("Development advantage")),
                                      ("$36", _("Initiative")),
                                      ("$40", _("With attack")),
                                      ("$44", _("Compensation")),
                                      ("$132", _("Counterplay")),
                                      ("$138", _("Time pressure"))):
                    menuitem = Gtk.MenuItem("%s %s" % (nag2symbol(nag), menutext))
                    menuitem.connect('activate', self.menu_position_attribute,
                                     board, nag)
                    symbol_menu2.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add evaluation symbol"))
                menuitem.set_submenu(symbol_menu2)
                self.menu.append(menuitem)

                self.menu.append(Gtk.SeparatorMenuItem())

                removals_menu = Gtk.Menu()

                menuitem = Gtk.MenuItem(_("Comment"))
                menuitem.connect('activate', self.menu_delete_comment, board, position)
                removals_menu.append(menuitem)

                menuitem = Gtk.MenuItem(_("Symbols"))
                menuitem.connect('activate', self.menu_remove_symbols, board)
                removals_menu.append(menuitem)

                menuitem = Gtk.MenuItem(_("All the evaluations"))
                menuitem.connect('activate', self.menu_reset_evaluations)
                removals_menu.append(menuitem)

                menuitem = Gtk.MenuItem(_("Remove"))
                menuitem.set_submenu(removals_menu)
                self.menu.append(menuitem)

                self.menu.show_all()
                self.menu.popup(None, None, None, None, event.button, event.time)
        return True

    def menu_refresh(self, widget):
        self.update()

    def menu_edit_comment(self, widget=None, board=None, index=0):
        """
        The method will create/update or delete a comment.
        The popup window will receive an additional button if there is an existing comment.
        """
        creation = True
        if not board.children:
            board.children.append("")
        elif not isinstance(board.children[index], str):
            board.children.insert(index, "")
        else:
            creation = False

        buttons_list = () if creation else (Gtk.STOCK_CLEAR, Gtk.ResponseType.REJECT)
        buttons_list = buttons_list + (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                       Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)

        dialog = Gtk.Dialog(_("Add comment") if creation else _("Edit comment"),
                            mainwindow(),
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            buttons_list)

        textedit = Gtk.TextView()
        textedit.set_editable(True)
        textedit.set_cursor_visible(True)
        textedit.set_wrap_mode(Gtk.WrapMode.WORD)

        textbuffer = textedit.get_buffer()
        textbuffer.set_text(board.children[index])

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(textedit)

        dialog.get_content_area().pack_start(sw, True, True, 0)
        dialog.resize(300, 200)
        dialog.show_all()

        response = dialog.run()
        dialog.destroy()

        (iter_first, iter_last) = textbuffer.get_bounds()
        comment = textbuffer.get_text(iter_first, iter_last, False)
        update = response in [Gtk.ResponseType.REJECT, Gtk.ResponseType.ACCEPT]
        drop = (response == Gtk.ResponseType.REJECT) or (creation and not update) or (update and len(comment) == 0)
        if drop:
            if not creation:
                self.gamemodel.needsSave = True
            del board.children[index]
        else:
            if update:
                if board.children[index] != comment:
                    self.gamemodel.needsSave = True
                board.children[index] = comment
        if drop or update:
            self.update()

    def menu_delete_comment(self, widget=None, board=None, index=0):
        """
        The method removes a comment.
        """
        if index == -1 or not board.children:
            return
        elif not isinstance(board.children[index], str):
            return
        self.gamemodel.needsSave = True
        del board.children[index]
        self.update()

    def menu_move_attribute(self, widget, board, nag):
        """
        The method will assign a sign to a move, like "a4!" or "Kh8?!".
        It is not possible to have multiple NAG tags for the move.
        """
        if len(board.nags) == 0:
            board.nags.append(nag)
            self.gamemodel.needsSave = True
        else:
            if board.nags[0] != nag:
                board.nags[0] = nag
                self.gamemodel.needsSave = True

        if self.gamemodel.needsSave:
            self.update_node(board)

    def menu_position_attribute(self, widget, board, nag):
        """
        The method will assign a sign to describe the current position.
        It is not possible to have multiple NAG tags for the position.
        """
        color = board.color
        if color == WHITE and nag in ("$14", "$16", "$18", "$20", "$22", "$32",
                                      "$36", "$40", "$44", "$132", "$138"):
            nag = "$%s" % (int(nag[1:]) + 1)

        if len(board.nags) == 0:
            board.nags.append("")
            board.nags.append(nag)
            self.gamemodel.needsSave = True
        if len(board.nags) == 1:
            board.nags.append(nag)
            self.gamemodel.needsSave = True
        else:
            if board.nags[1] != nag:
                board.nags[1] = nag
                self.gamemodel.needsSave = True

        if self.gamemodel.needsSave:
            self.update_node(board)

    def menu_remove_symbols(self, widget, board):
        """
        The method removes all the NAG tags assigned to the current node.
        """
        if board.nags:
            board.nags = []
            self.update_node(board)
            self.gamemodel.needsSave = True

    def menu_reset_evaluations(self, widget):
        """
        The method removes all the evaluations in order to recalculate them
        or simplify the output.
        """
        self.gamemodel.scores = {}
        self.update()

    def print_node(self, node):
        """ Just a debug helper """

        if "vari" in node:
            if node["board"] is None:
                text = "["
            else:
                text = "]"
        elif "comment" in node:
            text = node["comment"]
        else:
            text = self.__movestr(node["board"])
        return text

    def remove_variation(self, node):
        parent = node["parent"]

        # Set new shown board to parent board by default
        if parent.pieceBoard is None:
            # variation without played move at game end
            self.boardview.setShownBoard(self.gamemodel.boards[-1])
        else:
            self.boardview.setShownBoard(parent.pieceBoard)

        last_node = self.nodelist[-1] == node

        startnode = node["vari"]
        start = startnode["start"]
        end = node["end"]

        need_delete = []
        for n in self.nodelist[self.nodelist.index(startnode):]:
            if n["start"] < end:
                need_delete.append(n)

        if not last_node:
            diff = end - start
            for n in self.nodelist[self.nodelist.index(node) + 1:]:
                n["start"] -= diff
                n["end"] -= diff

        for n in need_delete:
            self.nodelist.remove(n)

        start_iter = self.textbuffer.get_iter_at_offset(start)
        end_iter = self.textbuffer.get_iter_at_offset(end)
        self.textbuffer.delete(start_iter, end_iter)

    def variation_start(self, iter, index, level):
        start = iter.get_offset()
        if not iter.ends_tag(tag=self.tag_new_line):
            self.textbuffer.insert_with_tags_by_name(iter, "\n", "new_line")
        vlevel = min(level + 1, len(self.tag_vari_depth) - 1)
        self.textbuffer.insert_with_tags_by_name(iter, "(", "variation-depth-%d" % vlevel)

        node = {}
        node["board"] = EMPTY_BOARD
        node["vari"] = None
        node["start"] = start
        node["end"] = iter.get_offset()

        if index == -1:
            self.nodelist.append(node)
        else:
            self.nodelist.insert(index, node)

        return (iter.get_offset() - start, node)

    def variation_end(self, iter, index, level, firstboard, parent, opening_node):
        start = iter.get_offset()
        vlevel = min(level + 1, len(self.tag_vari_depth) - 1)
        self.textbuffer.insert_with_tags_by_name(iter, ")", "variation-depth-%d" % vlevel)

        self.textbuffer.insert_with_tags_by_name(iter, u" ✖ ", "remove-variation")
        # chr = iter.get_char()

        # somehow iter.begins_tag() doesn't work, so we use get_char() instead
        if iter.get_char() != "\n":
            self.textbuffer.insert_with_tags_by_name(iter, "\n", "new_line")

        node = {}
        node["board"] = firstboard
        node["parent"] = parent
        node["vari"] = opening_node
        node["start"] = start
        node["end"] = iter.get_offset()

        if index == -1:
            self.nodelist.append(node)
        else:
            self.nodelist.insert(index, node)

        return iter.get_offset() - start

    def update_node(self, board):
        """ Called after adding/removing evaluation symbols """
        node = None
        for n in self.nodelist:
            if n["board"] == board:
                start = self.textbuffer.get_iter_at_offset(n["start"])
                end = self.textbuffer.get_iter_at_offset(n["end"])
                node = n
                break
        if node is None:
            return

        index = self.nodelist.index(node)
        level = node["level"]
        parent = node["parent"]
        diff = node["end"] - node["start"]
        self.nodelist.remove(node)
        self.textbuffer.delete(start, end)
        inserted_node = self.insert_node(board, start, index, level, parent)
        diff = inserted_node["end"] - inserted_node["start"] - diff

        if len(self.nodelist) > index + 1:
            for node in self.nodelist[index + 1:]:
                node["start"] += diff
                node["end"] += diff
        self.update_selected_node()

    def insert_node(self, board, iter, index, level, parent):
        start = iter.get_offset()
        movestr = self.__movestr(board)
        self.textbuffer.insert(iter, "%s " % movestr)

        startIter = self.textbuffer.get_iter_at_offset(start)
        endIter = self.textbuffer.get_iter_at_offset(iter.get_offset())

        if level == 0:
            self.textbuffer.apply_tag_by_name("move", startIter, endIter)
            self.textbuffer.apply_tag_by_name("margin", startIter, endIter)
            self.colorize_node(board.plyCount, startIter, endIter)
        else:
            self.textbuffer.apply_tag_by_name("variation-depth-%d" % level, startIter, endIter)

        node = {}
        node["board"] = board
        node["start"] = start
        node["end"] = iter.get_offset()
        node["parent"] = parent
        node["level"] = level

        if index == -1:
            self.nodelist.append(node)
        else:
            self.nodelist.insert(index, node)
        return node

    def variation_extended(self, gamemodel, prev_board, board):
        node = None
        for n in self.nodelist:
            if n["board"] == prev_board:
                end = self.textbuffer.get_iter_at_offset(n["end"])
                node = n
                break

        node_index = self.nodelist.index(node) + 1

        inserted_node = self.insert_node(board, end, node_index, node["level"],
                                         node["parent"])
        diff = inserted_node["end"] - inserted_node["start"]

        if len(self.nodelist) > node_index + 1:
            for node in self.nodelist[node_index + 1:]:
                node["start"] += diff
                node["end"] += diff

        self.boardview.setShownBoard(board.pieceBoard)
        self.gamemodel.needsSave = True

    def hide_movelist(self):
        return (self.gamemodel.lesson_game and not self.gamemodel.solved) or (
            self.gamemodel.puzzle_game and len(self.gamemodel.moves) == 0)

    def variation_added(self, gamemodel, boards, parent):
        # Don't show moves in interactive lesson games
        if self.hide_movelist():
            return

        # first find the iter where we will inset this new variation
        node = None
        for n in self.nodelist:
            if n["board"] == parent:
                end = self.textbuffer.get_iter_at_offset(n["end"])
                node = n
                break

        if node is None:
            next_node_index = len(self.nodelist)
            end = self.textbuffer.get_end_iter()
            level = 0
        else:
            next_node_index = self.nodelist.index(node) + 1
            level = node["level"]

        # diff will store the offset we need to shift the remaining stuff
        diff = 0

        # variation opening parenthesis
        sdiff, opening_node = self.variation_start(end, next_node_index, level)
        diff += sdiff

        for i, board in enumerate(boards):
            # do we have initial variation comment?
            if (board.prev is None):
                continue
            else:
                # insert variation move
                inserted_node = self.insert_node(
                    board, end, next_node_index + i, level + 1, parent)
                diff += inserted_node["end"] - inserted_node["start"]
                end = self.textbuffer.get_iter_at_offset(inserted_node["end"])

        diff += self.variation_end(end, next_node_index + len(boards), level,
                                   boards[1], parent, opening_node)

        # adjust remaining stuff offsets
        if next_node_index > 0:
            for node in self.nodelist[next_node_index + len(boards) + 1:]:
                node["start"] += diff
                node["end"] += diff

        # if new variation is coming from clicking in book panel
        # we want to jump into the first board in new vari
        self.boardview.setShownBoard(boards[1].pieceBoard)
        self.gamemodel.needsSave = True

    def colorize_node(self, ply, start, end):
        """
        The method updates the color or the node in order to show the errors and blunders.
        """
        tags = ["emt", "scored0", "scored5", "scored4", "scored3", "scored2", "scored1"]
        tags_diff = [None, None, 400, 200, 90, 50, 20]
        for tag_name in tags:
            self.textbuffer.remove_tag_by_name(tag_name, start, end)

        tag_name = "scored0"
        if self.showBlunder and ply - 1 in self.gamemodel.scores and ply in self.gamemodel.scores:
            color = (ply - 1) % 2
            oldmoves, oldscore, olddepth = self.gamemodel.scores[ply - 1]
            oldscore = oldscore * -1 if color == BLACK else oldscore
            moves, score, depth = self.gamemodel.scores[ply]
            score = score * -1 if color == WHITE else score
            diff = score - oldscore
            for i, td in enumerate(tags_diff):
                if td is None:
                    continue
                if (diff >= td and color == BLACK) or (diff <= -td and color == WHITE):
                    tag_name = tags[i]
                    break
        self.textbuffer.apply_tag_by_name(tag_name, start, end)

    def analysis_changed(self, gamemodel, ply):
        """
        The method updates the analysis received from an external event.
        """
        if self.boardview.animating:
            return
        if not self.boardview.shownIsMainLine():
            return

        try:
            board = gamemodel.getBoardAtPly(ply).board
        except IndexError:
            return

        node = None
        if self.showEval or self.showBlunder:
            for n in self.nodelist:
                if n["board"] == board:
                    start = self.textbuffer.get_iter_at_offset(n["start"])
                    end = self.textbuffer.get_iter_at_offset(n["end"])
                    node = n
                    break
        if node is None:
            return

        if self.showBlunder:
            self.colorize_node(ply, start, end)

        emt_eval = ""
        if self.showEmt and self.gamemodel.timemodel.hasTimes:
            elapsed = gamemodel.timemodel.getElapsedMoveTime(board.plyCount -
                                                             gamemodel.lowply)
            emt_eval = "%s " % formatTime(elapsed)

        if self.showEval:
            if board.plyCount in gamemodel.scores:
                moves, score, depth = gamemodel.scores[board.plyCount]
                score = score * -1 if board.color == BLACK else score
                emt_eval += "%s " % prettyPrintScore(score, depth, format_mate=True)

        if emt_eval:
            if node == self.nodelist[-1]:
                next_node = None
                self.textbuffer.delete(end, self.textbuffer.get_end_iter())
            else:
                next_node = self.nodelist[self.nodelist.index(node) + 1]
                next_start = self.textbuffer.get_iter_at_offset(next_node[
                    "start"])
                self.textbuffer.delete(end, next_start)
            self.textbuffer.insert_with_tags_by_name(end, emt_eval, "emt")

            if next_node is not None:
                diff = end.get_offset() - next_node["start"]
                for node in self.nodelist[self.nodelist.index(next_node):]:
                    node["start"] += diff
                    node["end"] += diff

    def update_selected_node(self):
        """ Update the selected node highlight """
        self.textbuffer.remove_tag_by_name("selected",
                                           self.textbuffer.get_start_iter(),
                                           self.textbuffer.get_end_iter())
        shown_board = self.gamemodel.getBoardAtPly(
            self.boardview.shown, self.boardview.shown_variation_idx)
        start = None
        for node in self.nodelist:
            if node["board"] == shown_board.board:
                start = self.textbuffer.get_iter_at_offset(node["start"])
                end = self.textbuffer.get_iter_at_offset(node["end"])
                # don't hightlight initial game comment!
                if shown_board.board != self.gamemodel.boards[0].board:
                    self.textbuffer.apply_tag_by_name("selected", start, end)
                break

        if start:
            # self.textview.scroll_to_iter(start, within_margin=0.03)
            self.textview.scroll_to_iter(start, 0.01, True, 0.00, 0.00)

    def insert_nodes(self, board, level=0, parent=None, result=None):
        """ Recursively builds the node tree """

        # Don't show moves in interactive lesson games
        if self.hide_movelist():
            return

        end_iter = self.textbuffer.get_end_iter  # Convenience shortcut to the function

        while True:
            # start = end_iter().get_offset()

            if board is None:
                break

            # Initial game or variation comment
            if board.prev is None:
                for index, child in enumerate(board.children):
                    if isinstance(child, str):
                        self.insert_comment(child,
                                            board,
                                            parent,
                                            index=index,
                                            level=level,
                                            ini_board=board)
                board = board.next
                continue

            if board.fen_was_applied:
                self.insert_node(board, end_iter(), -1, level, parent)

            if self.showEmt and level == 0 and board.fen_was_applied and self.gamemodel.timemodel.hasTimes:
                elapsed = self.gamemodel.timemodel.getElapsedMoveTime(
                    board.plyCount - self.gamemodel.lowply)
                self.textbuffer.insert_with_tags_by_name(
                    end_iter(), "%s " % formatTime(elapsed), "emt")

            if self.showEval and level == 0 and board.fen_was_applied and board.plyCount in self.gamemodel.scores:
                moves, score, depth = self.gamemodel.scores[board.plyCount]
                score = score * -1 if board.color == BLACK else score
                # endIter = self.textbuffer.get_iter_at_offset(end_iter().get_offset())
                self.textbuffer.insert_with_tags_by_name(
                    end_iter(), "%s " % prettyPrintScore(score, depth, format_mate=True), "emt")

            for index, child in enumerate(board.children):
                if isinstance(child, str):
                    # comment
                    self.insert_comment(child,
                                        board,
                                        parent,
                                        index=index,
                                        level=level)
                else:
                    # variation
                    diff, opening_node = self.variation_start(end_iter(), -1, level)
                    self.insert_nodes(child[0], level + 1, parent=board)
                    self.variation_end(end_iter(), -1, level, child[1], board, opening_node)

            if board.next:
                board = board.next
            else:
                break

        if result and result != "*" and not self.gamemodel.lesson_game and not self.gamemodel.practice_game:
            self.textbuffer.insert_with_tags_by_name(end_iter(), " " + result, "move")

    def apply_symbols(self, text):
        """
        The method will apply a Unicode symbol for any move contained in a sentence.
        Because it applies to a PGN-compatible text, only English letters are replaced (RNBQK).
        """
        def process_word(word):
            # Undecoration of the word
            regex = re_decoration.search(word)
            if regex:
                lead, core, trail = regex.groups()

                # Detection of the pieces in the move
                regex = re_move.search(core)
                if regex:
                    parts = list(regex.groups())

                    # Application of the Unicode symbols
                    for i, sign in enumerate(reprSign):  # TODO what about reprSignMakruk and reprSignSittuyin ?
                        if parts[0] == sign:
                            parts[0] = FAN_PIECES[WHITE][i]
                        if parts[2] == sign:
                            parts[2] = FAN_PIECES[WHITE][i]

                    return lead + "".join(parts) + trail
                else:
                    return word
            else:
                return word

        # Application of the filter on each element of the text
        if self.fan:
            re_decoration = re.compile('^([^a-hprnkqx1-8]*|[0-9]+\.+)?([a-hprnkqx1-8=@]+)([^a-hprnkqx1-8]*)$', re.IGNORECASE)
            re_move = re.compile('^([PRNBQK]?)(@?[a-h]?[1-8]?x?[a-h][1-8]=?)([RNBQK]?)(.*)$')
            return " ".join([process_word(word) for word in text.split(" ")])
        else:
            return text

    def insert_comment(self,
                       comment,
                       board,
                       parent,
                       index=0,
                       level=0,
                       ini_board=None):
        comment = re.sub("\[%.*?\]", "", comment)
        if not comment:
            return

        end_iter = self.textbuffer.get_end_iter()
        pos = len(self.nodelist)
        for n in self.nodelist:
            if n["board"] == board:
                pos = self.nodelist.index(n)
                break
        start = end_iter.get_offset()

        self.textbuffer.insert_with_tags_by_name(end_iter, self.apply_symbols(comment) + " ", "comment")

        node = {}
        node["board"] = ini_board if ini_board is not None else board
        node["comment"] = comment
        node["index"] = index
        node["parent"] = parent
        node["level"] = level
        node["start"] = start
        node["end"] = end_iter.get_offset()
        self.nodelist.insert(pos if ini_board is not None else pos + 1, node)

        return node

    def update_header(self):
        self.header_textbuffer.set_text("")

        end_iter = self.header_textbuffer.get_end_iter

        if self.gamemodel.info is not None:
            insert_formatted(self.header_textview, end_iter(), self.gamemodel.info)
            self.header_textbuffer.insert(end_iter(), "\n")

        if self.gamemodel.players:
            text = repr(self.gamemodel.players[0])
        else:
            return

        self.header_textbuffer.insert_with_tags_by_name(end_iter(), text, "head2")
        white_elo = self.gamemodel.tags['WhiteElo']
        if white_elo:
            self.header_textbuffer.insert_with_tags_by_name(end_iter(), " %s" % white_elo, "head1")

        self.header_textbuffer.insert_with_tags_by_name(end_iter(), " - ", "head1")

        # text = self.gamemodel.tags['Black']
        text = repr(self.gamemodel.players[1])
        self.header_textbuffer.insert_with_tags_by_name(end_iter(), text, "head2")
        black_elo = self.gamemodel.tags['BlackElo']
        if black_elo:
            self.header_textbuffer.insert_with_tags_by_name(end_iter(), " %s" % black_elo, "head1")

        result = reprResult[self.gamemodel.status]
        self.header_textbuffer.insert_with_tags_by_name(end_iter(), ' ' + result + '\n', "head2")

        text = ""
        time_control = self.gamemodel.tags.get('TimeControl')
        if time_control:
            match = parseTimeControlTag(time_control)
            if match is None:
                text += _("No time control") if time_control == "-" else time_control
            else:
                secs, inc, moves = match

                ttime = ""
                tmin = int(floor(secs / 60))
                tsec = secs - 60 * tmin
                if tmin > 0:
                    ttime += str(tmin) + " " + (_("mins") if tmin > 1 else _("min"))
                if tsec > 0:
                    if ttime != "":
                        ttime += " "
                    ttime += str(tsec) + " " + (_("secs") if tsec > 1 else _("sec"))

                if moves is not None and moves > 0:
                    text += _("%(time)s for %(count)d moves") % ({"time": ttime, "count": moves})
                else:
                    text += ttime
                    if inc != 0:
                        text += (" + " if inc >= 0 else " – ") + str(abs(inc)) + " " + (_("secs") if abs(inc) > 1 else _("sec")) + "/" + _("move")

        event = self.gamemodel.tags['Event']
        if event and event != "?":
            if len(text) > 0:
                text += ', '
            text += event

        site = self.gamemodel.tags['Site']
        if site and site != "?":
            if len(text) > 0:
                text += ', '
            text += site

        round = self.gamemodel.tags['Round']
        if round and round != "?":
            if len(text) > 0:
                text += ', '
            text += _('round %s') % round

        date = self.gamemodel.tags['Date']
        date = date.replace(".??", "").replace("????.", "")
        if date != "":
            if len(text) > 0:
                text += ', '
            text += date
        self.header_textbuffer.insert_with_tags_by_name(end_iter(), text, "head1")

        eco = self.gamemodel.tags.get('ECO')
        if eco:
            self.header_textbuffer.insert_with_tags_by_name(end_iter(), "\n" + eco, "head2")
            opening = self.gamemodel.tags.get('Opening')
            if opening:
                self.header_textbuffer.insert_with_tags_by_name(end_iter(), " - ", "head1")
                self.header_textbuffer.insert_with_tags_by_name(end_iter(), opening, "head2")
            variation = self.gamemodel.tags.get('Variation')
            if variation:
                self.header_textbuffer.insert_with_tags_by_name(end_iter(), ", ", "head1")
                self.header_textbuffer.insert_with_tags_by_name(end_iter(), variation, "head2")

    def update(self, *args):
        """
        This method execute the full refresh of the widget.
        """
        self.fetch_chess_conf()
        self.textbuffer.set_text('')
        self.nodelist = []
        self.update_header()
        self.update_choices()

        result = reprResult[self.gamemodel.status]

        self.insert_nodes(self.gamemodel.boards[0].board, result=result)
        self.update_selected_node()

    def on_choice_clicked(self, button, board):
        self.boardview.setShownBoard(board)
        if self.gamemodel.lesson_game:
            self.infobar.opp_choice_selected(board)

    def on_enter_notify_event(self, button, event, move):
        arrow = Cord(FCORD(move), color="G"), Cord(TCORD(move))
        self.boardview.arrows.add(arrow)
        self.boardview.redrawCanvas()

    def on_leave_notify_event(self, button, event, move):
        arrow = Cord(FCORD(move), color="G"), Cord(TCORD(move))
        if arrow in self.boardview.arrows:
            self.boardview.arrows.remove(arrow)
            self.boardview.redrawCanvas()

    def remove_choices(self):
        """ Removes all choice buttons """
        for widget in self.choices_box:
            self.choices_box.remove(widget)

    def update_choices(self):
        # First update lesson move comments
        if self.hide_movelist():
            self.show_lesson_comments()

        view = self.boardview
        try:
            next_board = view.model.getBoardAtPly(view.shown + 1, variation=view.shown_variation_idx)
        except IndexError:
            next_board = None

        # On game end and variation end there will be no choices for sure
        if next_board is None:
            self.remove_choices()
            return

        base_board = view.model.getBoardAtPly(view.shown, variation=view.shown_variation_idx)

        # Don't show our choices in lesson games
        if self.gamemodel.lesson_game and base_board.color == self.gamemodel.orientation:
            self.remove_choices()
            return

        # Gether variations first moves if there are any
        choices = []
        for child in next_board.board.children:
            if isinstance(child, list):
                lboard = child[1]
                if self.fan:
                    text = toFAN(base_board.board, lboard.lastMove)
                else:
                    text = toSAN(base_board.board, lboard.lastMove, True)
                choices.append((lboard.pieceBoard, lboard.lastMove, text))

        # Add main line next move to choice list also
        if choices:
            move = next_board.board.lastMove
            if self.fan:
                text = toFAN(base_board.board, move)
            else:
                text = toSAN(base_board.board, move, True)
            choices = [(next_board, move, text)] + choices

        # Remove previous choice buttons
        self.remove_choices()

        # Add nev choice buttons
        if self.choices_enabled and choices:
            for board, move, san in choices:
                button = Gtk.Button(san)
                button.set_name("rounded")
                button.connect("clicked", self.on_choice_clicked, board)
                button.connect("enter_notify_event", self.on_enter_notify_event, move)
                button.connect("leave_notify_event", self.on_leave_notify_event, move)
                self.choices_box.pack_start(button, False, False, 3)
            self.choices_box.show_all()
            preferencesDialog.SoundTab.playAction("variationChoice")

        if not self.choices_enabled:
            self.choices_enabled = True

    def show_lesson_comments(self):
        self.textbuffer.set_text('')
        self.nodelist = []
        view = self.boardview
        board = view.model.getBoardAtPly(view.shown, variation=view.shown_variation_idx)
        for index, child in enumerate(board.board.children):
            if isinstance(child, str):
                if child.lstrip().startswith("[%"):
                    continue
                end_iter = self.textbuffer.get_end_iter()
                self.textbuffer.insert_with_tags_by_name(
                    end_iter,
                    self.apply_symbols(child) + " ",
                    "lesson-comment")

    def on_shownChanged(self, view, shown):
        self.update_choices()
        self.update_selected_node()

    def on_moves_undone(self, game, moves):
        """
        This method is called once a move has been undone.
        """
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        for node in reversed(self.nodelist):
            if node["board"].pieceBoard == self.gamemodel.variations[0][-1]:
                start = self.textbuffer.get_iter_at_offset(node["end"])
                break
            else:
                self.nodelist.remove(node)

        if self.gamemodel.ply > 0:
            self.textbuffer.delete(start, end)
        self.update()

    def on_learn_success(self, model):
        self.update()

    def on_players_changed(self, model):
        self.update_header()

    def on_game_loaded(self, model, uri):
        """
        The method is called when a game is loaded.
        """
        for ply in range(min(40, model.ply, len(model.boards))):
            if ply >= model.lowply:
                model.setOpening(ply)
        self.update()

    def on_game_changed(self, game, ply):
        """
        The method is called when a game is changed, like by a move.
        """
        if self.hide_movelist():
            self.update()

        board = game.getBoardAtPly(ply, variation=0).board
        # if self.update() inserted all nodes before (f.e opening_changed), do nothing
        if self.nodelist and self.nodelist[-1]["board"] == board:
            return
        end_iter = self.textbuffer.get_end_iter
        start = end_iter().get_offset()
        movestr = self.__movestr(board)
        self.textbuffer.insert(end_iter(), "%s " % movestr)

        startIter = self.textbuffer.get_iter_at_offset(start)
        endIter = self.textbuffer.get_iter_at_offset(end_iter().get_offset())

        self.textbuffer.apply_tag_by_name("move", startIter, endIter)
        self.colorize_node(board.plyCount, startIter, endIter)

        node = {}
        node["board"] = board
        node["start"] = startIter.get_offset()
        node["end"] = end_iter().get_offset()
        node["parent"] = None
        node["level"] = 0

        self.nodelist.append(node)

        if self.showEmt and self.gamemodel.timed:
            elapsed = self.gamemodel.timemodel.getElapsedMoveTime(
                board.plyCount - self.gamemodel.lowply)
            self.textbuffer.insert_with_tags_by_name(
                end_iter(), "%s " % formatTime(elapsed), "emt")

        self.update_selected_node()

    def __movestr(self, board):
        move = board.lastMove
        if self.fan:
            movestr = toFAN(board.prev, move)
        else:
            movestr = toSAN(board.prev, move, True)
        nagsymbols = "".join([nag2symbol(nag) for nag in board.nags])
        # To prevent wrap castling we will use hyphen bullet (U+2043)
        return "%s%s%s" % (move_count(board), movestr.replace(
            '-', u'⁃'), nagsymbols)
