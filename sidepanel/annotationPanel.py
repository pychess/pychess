# -*- coding: UTF-8 -*-
import re
import datetime

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import Gdk

from pychess.Utils import prettyPrintScore
from pychess.Utils.const import *
from pychess.System import conf
from pychess.System.glock import glock_connect
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.lutils.lmove import toSAN, toFAN
from pychess.Savers.pgn import move_count
from pychess.Savers.pgnbase import nag2symbol
from pychess.widgets.ChessClock import formatTime

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_annotation.svg")
__desc__ = _("Annotated game")


class Sidepanel(Gtk.TextView):
    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(Gtk.WrapMode.WORD)

        self.cursor_standard = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
        #self.cursor_hand = Gdk.Cursor.new(Gdk.HAND2)
        self.cursor_hand = Gdk.Cursor.new(Gdk.CursorType.HAND2)
        
        self.textview = self
        
        self.nodeIters = []
        self.oldWidth = 0
        self.autoUpdateSelected = True
        
        self.connect("motion-notify-event", self.motion_notify_event)
        self.connect("button-press-event", self.button_press_event)
        
        self.textbuffer = self.get_buffer()
        
        color0 = Gdk.Color(red=0.0, green=0.0, blue=0.0)
        color1 = Gdk.Color(red=0.2, green=0.0, blue=0.0)
        color2 = Gdk.Color(red=0.4, green=0.0, blue=0.0)
        color3 = Gdk.Color(red=0.6, green=0.0, blue=0.0)
        color4 = Gdk.Color(red=0.8, green=0.0, blue=0.0)
        color5 = Gdk.Color(red=1.0, green=0.0, blue=0.0)

        self.textbuffer.create_tag("head1")
        self.textbuffer.create_tag("head2", weight=Pango.Weight.BOLD)
        self.textbuffer.create_tag("node", weight=Pango.Weight.BOLD, background="white")
        self.textbuffer.create_tag("scored0", foreground_gdk=color0)
        self.textbuffer.create_tag("scored1", foreground_gdk=color1)
        self.textbuffer.create_tag("scored2", foreground_gdk=color2)
        self.textbuffer.create_tag("scored3", foreground_gdk=color3)
        self.textbuffer.create_tag("scored4", foreground_gdk=color4)
        self.textbuffer.create_tag("scored5", foreground_gdk=color5)
        self.textbuffer.create_tag("emt", foreground="darkgrey", weight=Pango.Weight.NORMAL)
        self.textbuffer.create_tag("comment", foreground="darkblue")
        self.textbuffer.create_tag("variation-toplevel")
        self.textbuffer.create_tag("variation-even", foreground="darkgreen", style="italic")
        self.textbuffer.create_tag("variation-uneven", foreground="darkred", style="italic")
        self.textbuffer.create_tag("selected", background_full_height=True, background="grey")
        self.textbuffer.create_tag("margin", left_margin=4)
        self.textbuffer.create_tag("variation-margin0", left_margin=20)
        self.textbuffer.create_tag("variation-margin1", left_margin=36)
        self.textbuffer.create_tag("variation-margin2", left_margin=52)

    def load(self, gmwidg):
        __widget__ = Gtk.ScrolledWindow()
        __widget__.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        __widget__.add(self.textview)

        self.boardview = gmwidg.board.view
        self.boardview.connect("shown_changed", self.shown_changed)

        self.gamemodel = gmwidg.board.view.model
        glock_connect(self.gamemodel, "game_loaded", self.update)
        glock_connect(self.gamemodel, "game_changed", self.game_changed)
        glock_connect(self.gamemodel, "game_started", self.update)
        glock_connect(self.gamemodel, "game_ended", self.update)
        glock_connect(self.gamemodel, "moves_undoing", self.moves_undoing)
        glock_connect(self.gamemodel, "opening_changed", self.update)
        glock_connect(self.gamemodel, "players_changed", self.players_changed)
        glock_connect(self.gamemodel, "variations_changed", self.update)
        glock_connect(self.gamemodel, "analysis_changed", self.analysis_changed)

        # Connect to preferences
        self.fan = conf.get("figuresInNotation", False)
        def figuresInNotationCallback(none):
            self.fan = conf.get("figuresInNotation", False)
            self.update()
        conf.notify_add("figuresInNotation", figuresInNotationCallback)
        
        # Elapsed move time
        self.showEmt = conf.get("showEmt", False)
        def showEmtCallback(none):
            self.showEmt = conf.get("showEmt", False)
            self.update()
        conf.notify_add("showEmt", showEmtCallback)

        # Blunders
        self.showBlunder = conf.get("showBlunder", False)
        def showBlunderCallback(none):
            self.showBlunder = conf.get("showBlunder", False)
            self.update()
        conf.notify_add("showBlunder", showBlunderCallback)

        # Eval values
        self.showEval = conf.get("showEval", False)
        def showEvalCallback(none):
            self.showEval = conf.get("showEval", False)
            self.update()
        conf.notify_add("showEval", showEvalCallback)

        return __widget__

    def motion_notify_event(self, widget, event):
        if (event.is_hint):
            #(x, y, state) = event.window.get_pointer()
            (ign, x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.get_state()
            
        if self.textview.get_window_type(event.window) != Gtk.TextWindowType.TEXT:
            event.window.set_cursor(self.cursor_standard)
            return True
            
        (x, y) = self.textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
                event.window.set_cursor(self.cursor_hand)
                return True
        event.window.set_cursor(self.cursor_standard)
        return True

    def button_press_event(self, widget, event):
        (wx, wy) = event.get_coords()
        (x, y) = self.textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(wx), int(wy))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()

        node = None
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
                node = ni
                board = ni["node"]
                break
        
        if node is None:
            return True
            
        if event.button == 1:
            if "comment" in node:
                self.edit_comment(board=board, index=node["index"])
            else:
                self.boardview.setShownBoard(board.pieceBoard)
                self.update_selected_node()

        elif event.button == 3:
            if node is not None:
                menu = Gtk.Menu()
                position = -1
                for index, child in enumerate(board.children):
                    if isinstance(child, basestring):
                        position = index
                        break

                if len(self.gamemodel.boards) > 1 and board == self.gamemodel.boards[1].board and \
                    not self.gamemodel.boards[0].board.children:
                    menuitem = Gtk.MenuItem(_("Add start comment"))
                    menuitem.connect('activate', self.edit_comment, self.gamemodel.boards[0].board, 0)
                    menu.append(menuitem)

                if position == -1:
                    menuitem = Gtk.MenuItem(_("Add comment"))
                    menuitem.connect('activate', self.edit_comment, board, 0)
                    menu.append(menuitem)
                else:
                    menuitem = Gtk.MenuItem(_("Edit comment"))
                    menuitem.connect('activate', self.edit_comment, board, position)
                    menu.append(menuitem)

                symbol_menu1 = Gtk.Menu()
                for nag, menutext in (("$1", "!"),
                                      ("$2", "?"),
                                      ("$3", "!!"),
                                      ("$4", "??"),
                                      ("$5", "!?"),
                                      ("$6", "?!"),
                                      ("$7", _("Forced move"))):
                    menuitem = Gtk.MenuItem(menutext)
                    menuitem.connect('activate', self.symbol_menu1_activate, board, nag)
                    symbol_menu1.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add move symbol"))
                menuitem.set_submenu(symbol_menu1)
                menu.append(menuitem)
                
                symbol_menu2 = Gtk.Menu()
                for nag, menutext in (("$10", "="),
                                      ("$13", _("Unclear position")),
                                      ("$14", "+="),
                                      ("$15", "=+"),
                                      ("$16", "±"),
                                      ("$17", "∓"),
                                      ("$18", "+-"),
                                      ("$19", "-+"),
                                      ("$20", "+--"),
                                      ("$21", "--+"),
                                      ("$22", _("Zugzwang")),
                                      ("$32", _("Development adv.")),
                                      ("$36", _("Initiative")),
                                      ("$40", _("With attack")),
                                      ("$44", _("Compensation")),
                                      ("$132", _("Counterplay")),
                                      ("$138", _("Time pressure"))):
                    menuitem = Gtk.MenuItem(menutext)
                    menuitem.connect('activate', self.symbol_menu2_activate, board, nag)
                    symbol_menu2.append(menuitem)

                menuitem = Gtk.MenuItem(_("Add evaluation symbol"))
                menuitem.set_submenu(symbol_menu2)
                menu.append(menuitem)

                menuitem = Gtk.MenuItem(_("Remove symols"))
                menuitem.connect('activate', self.remove_symbols, board)
                menu.append(menuitem)

                if board.pieceBoard not in self.gamemodel.variations[0]:
                    for vari in self.gamemodel.variations[1:]:
                        if board.pieceBoard in vari:
                            menuitem = Gtk.MenuItem(_("Remove variation"))
                            menuitem.connect('activate', self.remove_variation, board, node["parent"], vari)
                            menu.append(menuitem)
                            break

                menu.show_all()
                menu.popup( None, None, None, event.button, event.time)
        return True

    def edit_comment(self, widget=None, board=None, index=0):
        dialog = Gtk.Dialog(_("Edit comment"),
                     None,
                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                     (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                      Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))

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

        dialog.vbox.add(sw)
        dialog.resize(300, 200)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            dialog.destroy()
            (iter_first, iter_last) = textbuffer.get_bounds()
            comment = textbuffer.get_text(iter_first, iter_last)
            if board.children[index] != comment:
                board.children[index] = comment
                self.gamemodel.needsSave = True
                self.update()
        else:
            dialog.destroy()

    def symbol_menu1_activate(self, widget, board, nag):
        if len(board.nags) == 0:
            board.nags.append(nag)
            self.gamemodel.needsSave = True
        else:
            if board.nags[0] != nag:
                board.nags[0] = nag
                self.gamemodel.needsSave = True
        if self.gamemodel.needsSave:
            self.update()

    def symbol_menu2_activate(self, widget, board, nag):
        color = board.color
        if color == WHITE and nag in ("$22", "$32", "$36", "$40", "$44", "$132", "$138"):
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
            self.update()

    def remove_symbols(self, widget, board):
        if board.nags:
            board.nags = []
            self.update()
            self.gamemodel.needsSave = True

    def remove_variation(self, widget, board, parent, vari):
        shown_board = self.gamemodel.getBoardAtPly(self.boardview.shown, self.boardview.shownVariationIdx)
        in_vari = shown_board in vari

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

        # Set new shownVariationIdx
        if parent.pieceBoard is None:
            self.boardview.shownVariationIdx = 0
            parent.prev.next = None
        else:
            for vari in self.gamemodel.variations:
                if in_vari:
                    if parent.pieceBoard in vari:
                        self.boardview.shownVariationIdx = self.gamemodel.variations.index(vari)
                        break
                else:
                    if shown_board in vari:
                        self.boardview.shownVariationIdx = self.gamemodel.variations.index(vari)
                        break

        self.update()
        self.gamemodel.needsSave = True

    def colorize_node(self, ply, start, end):
        self.textbuffer.remove_tag_by_name("scored5", start, end)
        self.textbuffer.remove_tag_by_name("scored4", start, end)
        self.textbuffer.remove_tag_by_name("scored3", start, end)
        self.textbuffer.remove_tag_by_name("scored2", start, end)
        self.textbuffer.remove_tag_by_name("scored1", start, end)
        if self.showBlunder and ply-1 in self.gamemodel.scores and ply in self.gamemodel.scores:
            color = (ply-1) % 2
            oldmoves, oldscore, olddepth = self.gamemodel.scores[ply-1]
            oldscore = oldscore * -1 if color == BLACK else oldscore
            moves, score, depth = self.gamemodel.scores[ply]
            score = score * -1 if color == WHITE else score
            diff = score-oldscore
            if (diff > 400 and color==BLACK) or (diff < -400 and color==WHITE):
                self.textbuffer.apply_tag_by_name("scored5", start, end)
            elif (diff > 200 and color==BLACK) or (diff < -200 and color==WHITE):
                self.textbuffer.apply_tag_by_name("scored4", start, end)
            elif (diff > 90 and color==BLACK) or (diff < -90 and color==WHITE):
                self.textbuffer.apply_tag_by_name("scored3", start, end)
            elif (diff > 50 and color==BLACK) or (diff < -50 and color==WHITE):
                self.textbuffer.apply_tag_by_name("scored2", start, end)
            elif (diff > 20 and color==BLACK) or (diff < -20 and color==WHITE):
                self.textbuffer.apply_tag_by_name("scored1", start, end)
            else:
                self.textbuffer.apply_tag_by_name("scored0", start, end)
        else:
            self.textbuffer.apply_tag_by_name("scored0", start, end)

    # Update the score chenged node color
    def analysis_changed(self, gamemodel, ply):
        if not self.boardview.shownIsMainLine():
            return
            
        started = False
        node = gamemodel.getBoardAtPly(ply).board
        iter = None
        if self.showEval or self.showBlunder:
            for ni in self.nodeIters:
                if ni["node"] == node:
                    start = self.textbuffer.get_iter_at_offset(ni["start"])
                    end = self.textbuffer.get_iter_at_offset(ni["end"])
                    iter = ni
                    started = True
                    break
        
        if not started:
            return
            
        if self.showBlunder:
            self.colorize_node(ply, start, end)

        emt_eval = ""
        if self.showEmt and self.gamemodel.timemodel.hasTimes:
            elapsed = gamemodel.timemodel.getElapsedMoveTime(node.plyCount - gamemodel.lowply)
            emt_eval = "%s " % formatTime(elapsed)

        if self.showEval:
            if node.plyCount in gamemodel.scores:
                moves, score, depth = gamemodel.scores[node.plyCount]
                score = score * -1 if node.color == BLACK else score
                emt_eval += "%s " % prettyPrintScore(score, depth)
        
        if emt_eval:
            if iter == self.nodeIters[-1]:
                next_iter = None
                self.textbuffer.delete(end, self.textbuffer.get_end_iter())
            else:
                next_iter = self.nodeIters[self.nodeIters.index(iter)+1]
                next_start = self.textbuffer.get_iter_at_offset(next_iter["start"])
                self.textbuffer.delete(end, next_start)
                
            self.textbuffer.insert_with_tags_by_name(end, emt_eval, "emt")

            if next_iter is not None:
                if next_iter.has_key("vari"):
                    self.textbuffer.insert_with_tags_by_name(end, "\n[", "variation-toplevel", "variation-margin0")
                diff = end.get_offset() - next_iter["start"]
                for ni in self.nodeIters[self.nodeIters.index(next_iter):]:
                    ni["start"] += diff
                    ni["end"] += diff
                
    # Update the selected node highlight
    def update_selected_node(self):
        self.textbuffer.remove_tag_by_name("selected", self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter())
        shown_board = self.gamemodel.getBoardAtPly(self.boardview.shown, self.boardview.shownVariationIdx)
        start = None
        for ni in self.nodeIters:
            if ni["node"] == shown_board.board:
                start = self.textbuffer.get_iter_at_offset(ni["start"])
                end = self.textbuffer.get_iter_at_offset(ni["end"])
                self.textbuffer.apply_tag_by_name("selected", start, end)
                break

        if start:
            #self.textview.scroll_to_iter(start, within_margin=0.03)
            self.textview.scroll_to_iter(start, 0.03, False, 0.00, 0.00)

    # Recursively insert the node tree
    def insert_nodes(self, node, level=0, ply=0, parent=None, result=None):
        buf = self.textbuffer
        end_iter = buf.get_end_iter # Convenience shortcut to the function
        new_line = False

        if self.boardview.shown >= self.gamemodel.lowply:
            shown_board = self.gamemodel.getBoardAtPly(self.boardview.shown, self.boardview.shownVariationIdx)
        
        while True: 
            start = end_iter().get_offset()
            
            if node is None:
                break
            
            # Initial game or variation comment
            if node.prev is None:
                for index, child in enumerate(node.children):
                    if isinstance(child, basestring):
                        if 0: # TODO node.plyCount == self.gamemodel.lowply:
                            self.insert_comment(child + "\n", node, index, parent, level)
                        else:
                            self.insert_comment(child, node, index, parent, level)
                node = node.next
                continue
            
            if node.fen_was_applied:
                ply += 1

                movestr = self.__movestr(node)
                buf.insert(end_iter(), "%s " % movestr)
                
                startIter = buf.get_iter_at_offset(start)
                endIter = buf.get_iter_at_offset(end_iter().get_offset())

                if level == 0:
                    buf.apply_tag_by_name("node", startIter, endIter)
                    buf.apply_tag_by_name("margin", startIter, endIter)
                    self.colorize_node(ply, startIter, endIter)
                elif level == 1:
                    buf.apply_tag_by_name("variation-toplevel", startIter, endIter)
                    buf.apply_tag_by_name("variation-margin0", startIter, endIter)
                elif level % 2 == 0:
                    buf.apply_tag_by_name("variation-even", startIter, endIter)
                    buf.apply_tag_by_name("variation-margin1", startIter, endIter)
                else:
                    buf.apply_tag_by_name("variation-uneven", startIter, endIter)
                    buf.apply_tag_by_name("variation-margin2", startIter, endIter)

                if self.boardview.shown >= self.gamemodel.lowply and node == shown_board.board:
                    buf.apply_tag_by_name("selected", startIter, endIter)
                    
                ni = {}
                ni["node"] = node
                ni["start"] = start       
                ni["end"] = end_iter().get_offset()
                ni["parent"] = parent
                if level == 1:
                    ni["vari"] = True
                self.nodeIters.append(ni)
                
            if self.showEmt and level == 0 and node.fen_was_applied and self.gamemodel.timemodel.hasTimes:
                elapsed = self.gamemodel.timemodel.getElapsedMoveTime(node.plyCount - self.gamemodel.lowply)
                self.textbuffer.insert_with_tags_by_name(end_iter(), "%s " % formatTime(elapsed), "emt")

            if self.showEval and level == 0 and node.fen_was_applied and node.plyCount in self.gamemodel.scores:
                moves, score, depth = self.gamemodel.scores[node.plyCount]
                score = score * -1 if node.color == BLACK else score
                endIter = buf.get_iter_at_offset(end_iter().get_offset())
                self.textbuffer.insert_with_tags_by_name(end_iter(), "%s " % prettyPrintScore(score, depth), "emt")

            new_line = False
            for index, child in enumerate(node.children):
                if isinstance(child, basestring):
                    # comment
                    self.insert_comment(child, node, index, parent, level)
                else:
                    # variation
                    if not new_line:
                        buf.insert(end_iter(), "\n")
                        new_line = True
                    
                    if level == 0:
                        buf.insert_with_tags_by_name(end_iter(), "[", "variation-toplevel", "variation-margin0")
                    elif (level+1) % 2 == 0:
                        buf.insert_with_tags_by_name(end_iter(), "(", "variation-even", "variation-margin1")
                    else:
                        buf.insert_with_tags_by_name(end_iter(), "(", "variation-uneven", "variation-margin2")
                    
                    self.insert_nodes(child[0], level+1, ply-1, parent=node)

                    if level == 0:
                        buf.insert_with_tags_by_name(end_iter(), "]\n", "variation-toplevel", "variation-margin0")
                    elif (level+1) % 2 == 0:
                        buf.insert_with_tags_by_name(end_iter(), ")\n", "variation-even", "variation-margin1")
                    else:
                        buf.insert_with_tags_by_name(end_iter(), ")\n", "variation-uneven", "variation-margin2")
            
            if node.next:
                node = node.next
            else:
                break

        if result and result != "*":
            buf.insert_with_tags_by_name(end_iter(), " "+result, "node")

    def insert_comment(self, comment, node, index, parent, level=0):
        comment = re.sub("\[%.*?\]", "", comment)
        if not comment:
            return
            
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        start = end_iter().get_offset()

        if level > 0:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment", "margin")
        else:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment")

        ni = {}
        ni["node"] = node
        ni["comment"] = comment
        ni["index"] = index
        ni["start"] = start     
        ni["end"] = end_iter().get_offset()
        ni["parent"] = parent
        self.nodeIters.append(ni)
        
        buf.insert(end_iter(), " ")

    def insert_header(self, gm):
        if gm.players:
            text = repr(gm.players[0])
        else:
            return

        buf = self.textbuffer
        end_iter = buf.get_end_iter

        buf.insert_with_tags_by_name(end_iter(), text, "head2")
        white_elo = gm.tags.get('WhiteElo')
        if white_elo:
            buf.insert_with_tags_by_name(end_iter(), " %s" % white_elo, "head1")

        buf.insert_with_tags_by_name(end_iter(), " - ", "head1")

        #text = gm.tags['Black']
        text = repr(gm.players[1])
        buf.insert_with_tags_by_name(end_iter(), text, "head2")
        black_elo = gm.tags.get('BlackElo')
        if black_elo:
            buf.insert_with_tags_by_name(end_iter(), " %s" % black_elo, "head1")

        status = reprResult[gm.status]
        if status != '*':
            result = status
        else:
            result = gm.tags['Result']
        buf.insert_with_tags_by_name(end_iter(), ' ' + result + '\n', "head2")

        text = ""
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
            game_date = "%02d.%02d.%02d" % (gm.tags['Year'], gm.tags['Month'], gm.tags['Day'])
        if (not '?' in game_date) and game_date.count('.') == 2:
            y, m, d = map(int, game_date.split('.'))
            # strftime() is limited to > 1900 dates
            try:
                text += ', ' + datetime.date(y, m, d).strftime('%x')
            except ValueError:
                text += ', ' + game_date
        elif not '?' in game_date[:4]:
            text += ', ' + game_date[:4]
        buf.insert_with_tags_by_name(end_iter(), text, "head1")

        eco = gm.tags.get('ECO')
        if eco:
            buf.insert_with_tags_by_name(end_iter(), "\n" + eco, "head2")
            opening = gm.tags.get('Opening')
            if opening:
                buf.insert_with_tags_by_name(end_iter(), " - ", "head1")
                buf.insert_with_tags_by_name(end_iter(), opening, "head2")
            variation = gm.tags.get('Variation')
            if variation:
                buf.insert_with_tags_by_name(end_iter(), ", ", "head1")
                buf.insert_with_tags_by_name(end_iter(), variation, "head2")

        buf.insert(end_iter(), "\n\n")

    # Update the entire notation tree
    def update(self, *args):
        self.textbuffer.set_text('')
        self.nodeIters = []
        self.insert_header(self.gamemodel)

        status = reprResult[self.gamemodel.status]
        if status != '*':
            result = status
        else:
            result = self.gamemodel.tags['Result']

        self.insert_nodes(self.gamemodel.boards[0].board, result=result)

    def shown_changed(self, boardview, shown):
        self.update_selected_node()

    def moves_undoing(self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        for ni in reversed(self.nodeIters):
            self.nodeIters.remove(ni)
            if ni["node"].pieceBoard == self.gamemodel.variations[0][-moves]:
                start = self.textbuffer.get_iter_at_offset(ni["start"])
                break
        self.textbuffer.delete(start, end)

    def game_changed(self, game):
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        start = end_iter().get_offset()
        node = game.getBoardAtPly(game.ply, variation=0).board

        buf.insert(end_iter(), "%s " % self.__movestr(node))

        startIter = buf.get_iter_at_offset(start)
        endIter = buf.get_iter_at_offset(end_iter().get_offset())

        buf.apply_tag_by_name("node", startIter, endIter)

        ni = {}
        ni["node"] = node
        ni["start"] = startIter.get_offset()        
        ni["end"] = end_iter().get_offset()
        ni["parent"] = None

        self.nodeIters.append(ni)

        if self.showEmt and self.gamemodel.timed:
            elapsed = self.gamemodel.timemodel.getElapsedMoveTime(node.plyCount - self.gamemodel.lowply)
            self.textbuffer.insert_with_tags_by_name(end_iter(), "%s " % formatTime(elapsed), "emt")

        self.update_selected_node()
    
    def players_changed(self, model):
        log.debug("annotationPanel.players_changed: starting")
        self.update
        log.debug("annotationPanel.players_changed: returning")
    
    def __movestr(self, node):
        move = node.lastMove
        if self.fan:           
            movestr = toFAN(node.prev, move)
        else:           
            movestr =  toSAN(node.prev, move, True)          
        nagsymbols = "".join([nag2symbol(nag) for nag in node.nags])     

        # To prevent wrap castling we will use hyphen bullet (U+2043)
        #return "%s%s%s" % (move_count(node), movestr.replace("-","⁃"), nagsymbols)
        return "%s%s%s" % (move_count(node), movestr.decode('utf-8').replace(u'-', u'\u2043'), nagsymbols)
