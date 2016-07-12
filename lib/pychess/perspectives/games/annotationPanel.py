# -*- coding: UTF-8 -*-

import re
import datetime

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Gdk

from pychess.compat import basestring, unicode
from pychess.Utils import prettyPrintScore
from pychess.Utils.const import WHITE, BLACK, FEN_EMPTY, reprResult

from pychess.System import conf
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import toSAN, toFAN
from pychess.Savers.pgn import move_count
from pychess.Savers.pgnbase import nag2symbol
from pychess.widgets.Background import set_textview_color
from pychess.widgets.ChessClock import formatTime

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_annotation.svg")
__desc__ = _("Annotated game")

EMPTY_BOARD = LBoard()
EMPTY_BOARD.applyFen(FEN_EMPTY)

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


class Sidepanel:
    def load(self, gmwidg):
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)

        self.cursor_standard = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
        self.cursor_hand = Gdk.Cursor.new(Gdk.CursorType.HAND2)

        self.nodelist = []
        self.oldWidth = 0
        self.autoUpdateSelected = True

        self.textview_cids = [
            self.textview.connect("motion-notify-event", self.motion_notify_event),
            self.textview.connect("button-press-event", self.button_press_event),
        ]
        bg_color, fg_color = set_textview_color(self.textview)

        self.textbuffer = self.textview.get_buffer()

        color0 = fg_color
        color1 = Gdk.RGBA(red=0.2, green=0.0, blue=0.0)
        color2 = Gdk.RGBA(red=0.4, green=0.0, blue=0.0)
        color3 = Gdk.RGBA(red=0.6, green=0.0, blue=0.0)
        color4 = Gdk.RGBA(red=0.8, green=0.0, blue=0.0)
        color5 = Gdk.RGBA(red=1.0, green=0.0, blue=0.0)

        self.remove_vari_tag = self.textbuffer.create_tag("remove-variation")
        self.rmv_cid = self.remove_vari_tag.connect("event", self.tag_event_handler)

        self.new_line_tag = self.textbuffer.create_tag("new_line")

        self.textbuffer.create_tag("head1")
        self.textbuffer.create_tag("head2", weight=Pango.Weight.BOLD)
        self.textbuffer.create_tag("move", weight=Pango.Weight.BOLD)
        self.textbuffer.create_tag("scored0", foreground_rgba=color0)
        self.textbuffer.create_tag("scored1", foreground_rgba=color1)
        self.textbuffer.create_tag("scored2", foreground_rgba=color2)
        self.textbuffer.create_tag("scored3", foreground_rgba=color3)
        self.textbuffer.create_tag("scored4", foreground_rgba=color4)
        self.textbuffer.create_tag("scored5", foreground_rgba=color5)
        self.textbuffer.create_tag("emt",
                                   foreground="darkgrey",
                                   weight=Pango.Weight.NORMAL)
        self.textbuffer.create_tag("comment", foreground="darkblue")
        self.textbuffer.create_tag("variation-toplevel",
                                   weight=Pango.Weight.NORMAL)
        self.textbuffer.create_tag("variation-even",
                                   foreground="darkgreen",
                                   style="italic")
        self.textbuffer.create_tag("variation-uneven",
                                   foreground="darkred",
                                   style="italic")
        self.textbuffer.create_tag("selected",
                                   background_full_height=True,
                                   background="grey")
        self.textbuffer.create_tag("margin", left_margin=4)
        self.textbuffer.create_tag("variation-margin0", left_margin=20)
        self.textbuffer.create_tag("variation-margin1", left_margin=36)
        self.textbuffer.create_tag("variation-margin2", left_margin=52)

        __widget__ = Gtk.ScrolledWindow()
        __widget__.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        __widget__.add(self.textview)

        self.boardview = gmwidg.board.view
        self.cid = self.boardview.connect("shownChanged", self.shownChanged)

        self.gamemodel = gmwidg.gamemodel
        self.model_cids = [
            self.gamemodel.connect_after("game_loaded", self.game_loaded),
            self.gamemodel.connect_after("game_changed", self.game_changed),
            self.gamemodel.connect_after("game_started", self.update),
            self.gamemodel.connect_after("game_ended", self.update),
            self.gamemodel.connect_after("moves_undone", self.moves_undone),
            self.gamemodel.connect_after("opening_changed", self.update),
            self.gamemodel.connect_after("players_changed", self.players_changed),
            self.gamemodel.connect_after("game_terminated", self.on_game_terminated),
            self.gamemodel.connect("variation_added", self.variation_added),
            self.gamemodel.connect("variation_extended", self.variation_extended),
            self.gamemodel.connect("analysis_changed", self.analysis_changed),
        ]

        # Connect to preferences
        self.conf_conids = []

        self.fan = conf.get("figuresInNotation", False)

        def figuresInNotationCallback(none):
            self.fan = conf.get("figuresInNotation", False)
            self.update()

        self.conf_conids.append(conf.notify_add("figuresInNotation", figuresInNotationCallback))

        # Elapsed move time
        self.showEmt = conf.get("showEmt", False)

        def showEmtCallback(none):
            self.showEmt = conf.get("showEmt", False)
            self.update()

        self.conf_conids.append(conf.notify_add("showEmt", showEmtCallback))

        # Blunders
        self.showBlunder = conf.get("showBlunder", False)

        def showBlunderCallback(none):
            self.showBlunder = conf.get("showBlunder", False)
            self.update()

        self.conf_conids.append(conf.notify_add("showBlunder", showBlunderCallback))

        # Eval values
        self.showEval = conf.get("showEval", False)

        def showEvalCallback(none):
            self.showEval = conf.get("showEval", False)
            self.update()

        self.conf_conids.append(conf.notify_add("showEval", showEvalCallback))

        return __widget__

    def on_game_terminated(self, model):
        for cid in self.textview_cids:
            self.textview.disconnect(cid)
        for conid in self.conf_conids:
            conf.notify_remove(conid)
        self.remove_vari_tag.disconnect(self.rmv_cid)
        for cid in self.model_cids:
            self.gamemodel.disconnect(cid)
        self.boardview.disconnect(self.cid)

    def tag_event_handler(self, tag, widget, event, iter):
        """ Calls variation remover when clicking on remove marker """

        tag_name = tag.get_property("name")
        if event.type == Gdk.EventType.BUTTON_PRESS and tag_name == "remove-variation":
            offset = iter.get_offset()
            node = None
            for n in self.nodelist:
                if offset >= n["start"] and offset < n["end"]:
                    node = n
                    break
            if node is None:
                return

            self.remove_variation(node)

        return False

    def motion_notify_event(self, widget, event):
        """ Handles mouse cursor changes (standard/hand) """

        if (event.is_hint):
            # (x, y, state) = event.window.get_pointer()
            (ign, x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            # state = event.get_state()

        if self.textview.get_window_type(
                event.window) != Gtk.TextWindowType.TEXT:
            event.window.set_cursor(self.cursor_standard)
            return True

        (x, y) = self.textview.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y))
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
        """ Calls setShownBoard() or edit_comment() on mouse click, or pops-up local menu """

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
        # left mouse click
        if event.button == 1:
            if "vari" in node:
                # tag_event_handler() will handle
                return True
            elif "comment" in node:
                self.edit_comment(board=board, index=node["index"])
            else:
                self.boardview.setShownBoard(board.pieceBoard)

        # local menu on right mouse click
        elif event.button == 3:
            self.menu = Gtk.Menu()

            menuitem = Gtk.MenuItem(_("Copy PGN"))
            menuitem.connect('activate', self.copy_pgn)
            self.menu.append(menuitem)

            if node is not None:
                position = -1
                for index, child in enumerate(board.children):
                    if isinstance(child, basestring):
                        position = index
                        break

                if len(self.gamemodel.boards) > 1 and board == self.gamemodel.boards[1].board and \
                        not self.gamemodel.boards[0].board.children:
                    menuitem = Gtk.MenuItem(_("Add start comment"))
                    menuitem.connect('activate', self.edit_comment,
                                     self.gamemodel.boards[0].board, 0)
                    self.menu.append(menuitem)

                if position == -1:
                    menuitem = Gtk.MenuItem(_("Add comment"))
                    menuitem.connect('activate', self.edit_comment, board, 0)
                    self.menu.append(menuitem)
                else:
                    menuitem = Gtk.MenuItem(_("Edit comment"))
                    menuitem.connect('activate', self.edit_comment, board,
                                     position)
                    self.menu.append(menuitem)

                symbol_menu1 = Gtk.Menu()
                for nag, menutext in (("$1", "!"), ("$2", "?"), ("$3", "!!"),
                                      ("$4", "??"), ("$5", "!?"), ("$6", "?!"),
                                      ("$7", _("Forced move"))):
                    menuitem = Gtk.MenuItem(menutext)
                    menuitem.connect('activate', self.symbol_menu1_activate,
                                     board, nag)
                    symbol_menu1.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add move symbol"))
                menuitem.set_submenu(symbol_menu1)
                self.menu.append(menuitem)

                symbol_menu2 = Gtk.Menu()
                for nag, menutext in (("$10", "="), ("$13", _("Unclear position")),
                                      ("$14", "+="), ("$15", "=+"), ("$16", "±"), ("$17", "∓"),
                                      ("$18", "+-"), ("$19", "-+"), ("$20", "+--"),
                                      ("$21", "--+"), ("$22", _("Zugzwang")),
                                      ("$32", _("Development adv.")), ("$36", _("Initiative")),
                                      ("$40", _("With attack")), ("$44", _("Compensation")),
                                      ("$132", _("Counterplay")), ("$138", _("Time pressure"))):
                    menuitem = Gtk.MenuItem(menutext)
                    menuitem.connect('activate', self.symbol_menu2_activate,
                                     board, nag)
                    symbol_menu2.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add evaluation symbol"))
                menuitem.set_submenu(symbol_menu2)
                self.menu.append(menuitem)

                menuitem = Gtk.MenuItem(_("Remove symbols"))
                menuitem.connect('activate', self.remove_symbols, board)
                self.menu.append(menuitem)

                self.menu.show_all()
                self.menu.popup(None, None, None, None, event.button,
                                event.time)
        return True

    def copy_pgn(self, widget):
        self.gamewidget.copy_pgn()

    def edit_comment(self, widget=None, board=None, index=0):
        dialog = Gtk.Dialog(
            _("Edit comment"), None, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT, Gtk.STOCK_OK,
                Gtk.ResponseType.ACCEPT))

        textedit = Gtk.TextView()
        textedit.set_editable(True)
        textedit.set_cursor_visible(True)
        textedit.set_wrap_mode(Gtk.WrapMode.WORD)

        textbuffer = textedit.get_buffer()
        if not board.children:
            board.children.append("")
        elif not isinstance(board.children[index], basestring):
            board.children.insert(index, "")
        textbuffer.set_text(board.children[index])

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(textedit)

        dialog.get_content_area().pack_start(sw, True, True, 0)
        dialog.resize(300, 200)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            dialog.destroy()
            (iter_first, iter_last) = textbuffer.get_bounds()
            comment = textbuffer.get_text(iter_first, iter_last, False)
            if board.children[index] != comment:
                if comment:
                    board.children[index] = comment
                else:
                    del board.children[index]
                self.gamemodel.needsSave = True
                self.update()
        else:
            dialog.destroy()

    # Add move symbol menu
    def symbol_menu1_activate(self, widget, board, nag):
        if len(board.nags) == 0:
            board.nags.append(nag)
            self.gamemodel.needsSave = True
        else:
            if board.nags[0] != nag:
                board.nags[0] = nag
                self.gamemodel.needsSave = True

        if self.gamemodel.needsSave:
            self.update_node(board)

    # Add evaluation symbol menu
    def symbol_menu2_activate(self, widget, board, nag):
        color = board.color
        if color == WHITE and nag in ("$22", "$32", "$36", "$40", "$44",
                                      "$132", "$138"):
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

    def remove_symbols(self, widget, board):
        if board.nags:
            board.nags = []
            self.update_node(board)
            self.gamemodel.needsSave = True

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
        # shown_board = self.gamemodel.getBoardAtPly(self.boardview.shown, self.boardview.shown_variation_idx)
        # TODO
        in_vari = True  # shown_board in vari

        board = node["board"]
        parent = node["parent"]
        # Set new shown board if needed
        if in_vari:
            if parent.pieceBoard is None:
                # variation without played move at game end
                self.boardview.setShownBoard(self.gamemodel.boards[-1])
            else:
                self.boardview.setShownBoard(parent.pieceBoard)

        # Remove the variation (list of lboards) containing board from parent's children list
        for child in parent.children:
            if isinstance(child, list) and board in child:
                parent.children.remove(child)
                break

        # Remove all variations from gamemodel's variations list which contains this board
        for vari in self.gamemodel.variations[1:]:
            if board.pieceBoard in vari:
                self.gamemodel.variations.remove(vari)

        last_node = self.nodelist[-1] == node

        # remove null_board if variation was added on last played move
        if not parent.fen_was_applied:
            parent.prev.next = None

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

        self.gamemodel.needsSave = True

    def variation_start(self, iter, index, level):
        start = iter.get_offset()
        if not iter.ends_tag(tag=self.new_line_tag):
            self.textbuffer.insert_with_tags_by_name(iter, "\n", "new_line")
        if level == 0:
            self.textbuffer.insert_with_tags_by_name(
                iter, "[", "variation-toplevel", "variation-margin0")
        elif (level + 1) % 2 == 0:
            self.textbuffer.insert_with_tags_by_name(
                iter, "(", "variation-even", "variation-margin1")
        else:
            self.textbuffer.insert_with_tags_by_name(
                iter, "(", "variation-uneven", "variation-margin2")

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

    def variation_end(self, iter, index, level, firstboard, parent,
                      opening_node):
        start = iter.get_offset()
        if level == 0:
            self.textbuffer.insert_with_tags_by_name(
                iter, "]", "variation-toplevel", "variation-margin0")
        elif (level + 1) % 2 == 0:
            self.textbuffer.insert_with_tags_by_name(
                iter, ")", "variation-even", "variation-margin1")
        else:
            self.textbuffer.insert_with_tags_by_name(
                iter, ")", "variation-uneven", "variation-margin2")

        self.textbuffer.insert_with_tags_by_name(iter, unicode("✖ "),
                                                 "remove-variation")
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
        """ Called after adding/removing evaluation simbols """
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
        elif level == 1:
            self.textbuffer.apply_tag_by_name("variation-toplevel", startIter,
                                              endIter)
            self.textbuffer.apply_tag_by_name("variation-margin0", startIter,
                                              endIter)
        elif level % 2 == 0:
            self.textbuffer.apply_tag_by_name("variation-even", startIter,
                                              endIter)
            self.textbuffer.apply_tag_by_name("variation-margin1", startIter,
                                              endIter)
        else:
            self.textbuffer.apply_tag_by_name("variation-uneven", startIter,
                                              endIter)
            self.textbuffer.apply_tag_by_name("variation-margin2", startIter,
                                              endIter)

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

    @idle_add
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

    @idle_add
    def variation_added(self, gamemodel, boards, parent, comment, score):
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

        ini_board = None
        for i, board in enumerate(boards):
            # do we have initial variation comment?
            if (board.prev is None):
                if comment:
                    board.children.append(comment)
                    ini_board = board
                continue
            else:
                # insert variation move
                inserted_node = self.insert_node(
                    board, end, next_node_index + i, level + 1, parent)
                diff += inserted_node["end"] - inserted_node["start"]
                end = self.textbuffer.get_iter_at_offset(inserted_node["end"])

                if ini_board is not None:
                    # insert initial variation comment
                    inserted_comment = self.insert_comment(comment,
                                                           board,
                                                           parent,
                                                           level=level + 1,
                                                           ini_board=ini_board)
                    comment_diff = inserted_comment["end"] - inserted_comment[
                        "start"]
                    inserted_node["start"] += comment_diff
                    inserted_node["end"] += comment_diff
                    end = self.textbuffer.get_iter_at_offset(inserted_node[
                        "end"])
                    diff += comment_diff
                    # leading = False
                    next_node_index += 1
                    ini_board = None

        if score:
            # insert score of variation latest move as comment
            board.children.append(score)
            inserted_node = self.insert_comment(score,
                                                board,
                                                parent,
                                                level=level + 1)
            diff += inserted_node["end"] - inserted_node["start"]
            end = self.textbuffer.get_iter_at_offset(inserted_node["end"])
            next_node_index += 1

        diff += self.variation_end(end, next_node_index + len(boards), level,
                                   boards[1], parent, opening_node)

        # adjust remaining stuff offsets
        if next_node_index > 0:
            for node in self.nodelist[next_node_index + len(boards) + 1:]:
                node["start"] += diff
                node["end"] += diff

        # if new variation is coming from clicking in book panel
        # we want to jump into the first board in new vari
        if not comment:
            self.boardview.setShownBoard(boards[1].pieceBoard)

        self.gamemodel.needsSave = True

    def colorize_node(self, ply, start, end):
        """ Update the node color """

        if self.gamemodel is None:
            return

        self.textbuffer.remove_tag_by_name("emt", start, end)
        self.textbuffer.remove_tag_by_name("scored5", start, end)
        self.textbuffer.remove_tag_by_name("scored4", start, end)
        self.textbuffer.remove_tag_by_name("scored3", start, end)
        self.textbuffer.remove_tag_by_name("scored2", start, end)
        self.textbuffer.remove_tag_by_name("scored1", start, end)
        if self.showBlunder and ply - 1 in self.gamemodel.scores and ply in self.gamemodel.scores:
            color = (ply - 1) % 2
            oldmoves, oldscore, olddepth = self.gamemodel.scores[ply - 1]
            oldscore = oldscore * -1 if color == BLACK else oldscore
            moves, score, depth = self.gamemodel.scores[ply]
            score = score * -1 if color == WHITE else score
            diff = score - oldscore
            if (diff > 400 and color == BLACK) or (diff < -400 and
                                                   color == WHITE):
                self.textbuffer.apply_tag_by_name("scored5", start, end)
            elif (diff > 200 and color == BLACK) or (diff < -200 and
                                                     color == WHITE):
                self.textbuffer.apply_tag_by_name("scored4", start, end)
            elif (diff > 90 and color == BLACK) or (diff < -90 and
                                                    color == WHITE):
                self.textbuffer.apply_tag_by_name("scored3", start, end)
            elif (diff > 50 and color == BLACK) or (diff < -50 and
                                                    color == WHITE):
                self.textbuffer.apply_tag_by_name("scored2", start, end)
            elif (diff > 20 and color == BLACK) or (diff < -20 and
                                                    color == WHITE):
                self.textbuffer.apply_tag_by_name("scored1", start, end)
            else:
                self.textbuffer.apply_tag_by_name("scored0", start, end)
        else:
            self.textbuffer.apply_tag_by_name("scored0", start, end)

    @idle_add
    def analysis_changed(self, gamemodel, ply):
        if self.boardview.animating:
            return

        if not self.boardview.shownIsMainLine():
            return

        board = gamemodel.getBoardAtPly(ply).board
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
                emt_eval += "%s " % prettyPrintScore(score, depth)

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

        if self.gamemodel is None:
            return

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
                self.textbuffer.apply_tag_by_name("selected", start, end)
                break

        if start:
            # self.textview.scroll_to_iter(start, within_margin=0.03)
            self.textview.scroll_to_iter(start, 0.03, False, 0.00, 0.00)

    def insert_nodes(self, board, level=0, parent=None, result=None):
        """ Recursively builds the node tree """

        end_iter = self.textbuffer.get_end_iter  # Convenience shortcut to the function

        while True:
            # start = end_iter().get_offset()

            if board is None:
                break

            # Initial game or variation comment
            if board.prev is None:
                for index, child in enumerate(board.children):
                    if isinstance(child, basestring):
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
                    end_iter(), "%s " % prettyPrintScore(score, depth), "emt")

            for index, child in enumerate(board.children):
                if isinstance(child, basestring):
                    # comment
                    self.insert_comment(child,
                                        board,
                                        parent,
                                        index=index,
                                        level=level)
                else:
                    # variation
                    diff, opening_node = self.variation_start(end_iter(), -1,
                                                              level)
                    self.insert_nodes(child[0], level + 1, parent=board)
                    self.variation_end(end_iter(), -1, level, child[1], board,
                                       opening_node)

            if board.next:
                board = board.next
            else:
                break

        if result and result != "*":
            self.textbuffer.insert_with_tags_by_name(end_iter(), " " + result,
                                                     "move")

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
                if ini_board is not None:
                    end_iter = self.textbuffer.get_iter_at_offset(n["start"])
                else:
                    end_iter = self.textbuffer.get_iter_at_offset(n["end"])
                pos = self.nodelist.index(n)
                break
        start = end_iter.get_offset()

        self.textbuffer.insert_with_tags_by_name(end_iter, comment + " ",
                                                 "comment")

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

    def insert_header(self, gm):

        if gm.players:
            text = repr(gm.players[0])
        else:
            return
        end_iter = self.textbuffer.get_end_iter

        self.textbuffer.insert_with_tags_by_name(end_iter(), text, "head2")
        white_elo = gm.tags.get('WhiteElo')
        if white_elo:
            self.textbuffer.insert_with_tags_by_name(end_iter(), " %s" %
                                                     white_elo, "head1")

        self.textbuffer.insert_with_tags_by_name(end_iter(), " - ", "head1")

        # text = gm.tags['Black']
        text = repr(gm.players[1])
        self.textbuffer.insert_with_tags_by_name(end_iter(), text, "head2")
        black_elo = gm.tags.get('BlackElo')
        if black_elo:
            self.textbuffer.insert_with_tags_by_name(end_iter(), " %s" %
                                                     black_elo, "head1")

        status = reprResult[gm.status]
        if status != '*':
            result = status
        else:
            result = gm.tags['Result']
        self.textbuffer.insert_with_tags_by_name(end_iter(),
                                                 ' ' + result + '\n', "head2")

        text = ""
        time_control = gm.tags.get('TimeControl')
        if time_control:
            mins, inc = time_control.split('+')
            mins = int(mins) / 60
            mins = "{:.0f}".format(mins)
            if inc != '0':
                text += mins + ' mins + ' + inc + ' secs '
            else:
                text += mins + ' mins '

        event = gm.tags['Event']
        if event and event != "?":
            text += event

        site = gm.tags['Site']
        if site and site != "?":
            if len(text) > 0:
                text += ', '
            text += site

        round = gm.tags['Round']
        if round and round != "?":
            if len(text) > 0:
                text += ', '
            text += _('round %s') % round

        game_date = gm.tags.get('Date')
        if game_date is None:
            game_date = "%02d.%02d.%02d" % (gm.tags['Year'], gm.tags['Month'],
                                            gm.tags['Day'])
        if ('?' not in game_date) and game_date.count('.') == 2:
            y, m, d = map(int, game_date.split('.'))
            # strftime() is limited to > 1900 dates
            try:
                text += ', ' + datetime.date(y, m, d).strftime('%x')
            except ValueError:
                text += ', ' + game_date
        elif '?' not in game_date[:4]:
            text += ', ' + game_date[:4]
        self.textbuffer.insert_with_tags_by_name(end_iter(), text, "head1")

        eco = gm.tags.get('ECO')
        if eco:
            self.textbuffer.insert_with_tags_by_name(end_iter(), "\n" + eco,
                                                     "head2")
            opening = gm.tags.get('Opening')
            if opening:
                self.textbuffer.insert_with_tags_by_name(end_iter(), " - ",
                                                         "head1")
                self.textbuffer.insert_with_tags_by_name(end_iter(), opening,
                                                         "head2")
            variation = gm.tags.get('Variation')
            if variation:
                self.textbuffer.insert_with_tags_by_name(end_iter(), ", ",
                                                         "head1")
                self.textbuffer.insert_with_tags_by_name(end_iter(), variation,
                                                         "head2")

        self.textbuffer.insert(end_iter(), "\n\n")

    @idle_add
    def update(self, *args):
        """ Update the entire notation tree """

        if self.gamemodel is None:
            return

        self.textbuffer.set_text('')
        self.nodelist = []
        self.insert_header(self.gamemodel)

        status = reprResult[self.gamemodel.status]
        if status != '*':
            result = status
        else:
            result = self.gamemodel.tags['Result']

        self.insert_nodes(self.gamemodel.boards[0].board, result=result)
        self.update_selected_node()

    @idle_add
    def shownChanged(self, boardview, shown):
        self.update_selected_node()

    @idle_add
    def moves_undone(self, game, moves):
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        for node in reversed(self.nodelist):
            if node["board"].pieceBoard == self.gamemodel.variations[0][-1]:
                start = self.textbuffer.get_iter_at_offset(node["end"])
                break
            else:
                self.nodelist.remove(node)

        self.textbuffer.delete(start, end)

    @idle_add
    def game_changed(self, game, ply):
        board = game.getBoardAtPly(ply, variation=0).board
        # if self.update() insterted all nodes before (f.e opening_changed), do nothing
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

    def players_changed(self, model):
        log.debug("annotationPanel.players_changed: starting")
        self.update()
        log.debug("annotationPanel.players_changed: returning")

    def game_loaded(self, model, uri):
        for ply in range(min(40, model.ply, len(model.boards))):
            model.setOpening(ply)
        self.update()

    def __movestr(self, board):
        move = board.lastMove
        if self.fan:
            movestr = unicode(toFAN(board.prev, move))
        else:
            movestr = unicode(toSAN(board.prev, move, True))
        nagsymbols = "".join([nag2symbol(nag) for nag in board.nags])
        # To prevent wrap castling we will use hyphen bullet (U+2043)
        return "%s%s%s" % (move_count(board), movestr.replace(
            '-', unicode('⁃')), nagsymbols)
