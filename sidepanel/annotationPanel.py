# -*- coding: UTF-8 -*-

import datetime

import gtk
import pango

from pychess.Utils.const import *
from pychess.System import conf
from pychess.System.glock import glock_connect
from pychess.System.prefix import addDataPrefix
from pychess.Utils.Move import Move, toSAN, toFAN
from pychess.Savers.pgn import nag2symbol, symbol2nag, move_count

__title__ = _("Annotation")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _("Annotated game")


class Sidepanel(gtk.TextView):
    def __init__(self):
        gtk.TextView.__init__(self)

        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(gtk.WRAP_WORD)

        self.cursor_standard = gtk.gdk.Cursor(gtk.gdk.LEFT_PTR)
        self.cursor_hand = gtk.gdk.Cursor(gtk.gdk.HAND2)
        
        self.textview = self
        
        self.nodeIters = []
        self.commentIters = []
        self.oldWidth = 0
        self.autoUpdateSelected = True
        
        self.connect("motion-notify-event", self.motion_notify_event)
        self.connect("button-press-event", self.button_press_event)
        
        self.textbuffer = self.get_buffer()
        
        self.textbuffer.create_tag("head1")
        self.textbuffer.create_tag("head2", weight=pango.WEIGHT_BOLD)
        self.textbuffer.create_tag("node", weight=pango.WEIGHT_BOLD)
        self.textbuffer.create_tag("comment", foreground="darkblue")
        self.textbuffer.create_tag("variation-toplevel")
        self.textbuffer.create_tag("variation-even", foreground="darkgreen", style="italic")
        self.textbuffer.create_tag("variation-uneven", foreground="darkred", style="italic")
        self.textbuffer.create_tag("selected", background_full_height=True, background="black", foreground="white")
        self.textbuffer.create_tag("margin", left_margin=4)
        self.textbuffer.create_tag("variation-margin0", left_margin=20)
        self.textbuffer.create_tag("variation-margin1", left_margin=36)
        self.textbuffer.create_tag("variation-margin2", left_margin=52)

    def load(self, gmwidg):
        __widget__ = gtk.ScrolledWindow()
        __widget__.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
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
        glock_connect(self.gamemodel, "players_changed", self.update)
        glock_connect(self.gamemodel, "variations_changed", self.update)

        # Connect to preferences
        
        def figuresInNotationCallback(none):
            self.update()
        conf.notify_add("figuresInNotation", figuresInNotationCallback)

        return __widget__

    def motion_notify_event(self, widget, event):
        if (event.is_hint):
            (x, y, state) = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
            
        if self.textview.get_window_type(event.window) != gtk.TEXT_WINDOW_TEXT:
            event.window.set_cursor(self.cursor_standard)
            return True
            
        (x, y) = self.textview.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, int(x), int(y))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
                event.window.set_cursor(self.cursor_hand)
                return True
        for ci in self.commentIters:
            if offset >= ci["start"] and offset < ci["end"]:
                event.window.set_cursor(self.cursor_hand)
                return True
        event.window.set_cursor(self.cursor_standard)
        return True

    def button_press_event(self, widget, event):
        (wx, wy) = event.get_coords()
        (x, y) = self.textview.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, int(wx), int(wy))
        it = self.textview.get_iter_at_location(x, y)
        offset = it.get_offset()

        node = None
        for ni in self.nodeIters:
            if offset >= ni["start"] and offset < ni["end"]:
                node = ni
                board = ni["node"]
                parent = ni["parent"]
                if event.button == 1:
                    self.setShown(board)
                    self.update_selected_node()
                break
        
        if node is None and event.button == 1:
            for ci in self.commentIters:
                if offset >= ci["start"] and offset < ci["end"]:
                    self.edit_comment(board=ci["node"], index=ci["index"])
                    break

        elif event.button == 3:
            if node is not None:
                menu = gtk.Menu()
                position = -1
                for index, child in enumerate(board.children):
                    if isinstance(child, basestring):
                        position = index
                        break

                if board == self.gamemodel.boards[1] and not self.gamemodel.boards[0].children:
                    menuitem = gtk.MenuItem(_("Add start comment"))
                    menuitem.connect('activate', self.edit_comment, self.gamemodel.boards[0], 0)
                    menu.append(menuitem)

                if position == -1:
                    menuitem = gtk.MenuItem(_("Add comment"))
                    menuitem.connect('activate', self.edit_comment, board, 0)
                    menu.append(menuitem)
                else:
                    menuitem = gtk.MenuItem(_("Edit comment"))
                    menuitem.connect('activate', self.edit_comment, board, position)
                    menu.append(menuitem)

                symbol_menu1 = gtk.Menu()
                for symbol in ("!", "?", "!?", "?!", "!!", "??"):
                    menuitem = gtk.MenuItem(symbol)
                    menuitem.connect('activate', self.symbol_menu1_activate, board, symbol)
                    symbol_menu1.append(menuitem)

                menuitem = gtk.MenuItem(_("Add move symbol"))
                menuitem.set_submenu(symbol_menu1)
                menu.append(menuitem)
                
                symbol_menu2 = gtk.Menu()
                for symbol in ("=", "∞", "+=", "=+", "±", "∓", "+-", "-+"):
                    menuitem = gtk.MenuItem(symbol)
                    menuitem.connect('activate', self.symbol_menu2_activate, board, symbol)
                    symbol_menu2.append(menuitem)

                menuitem = gtk.MenuItem(_("Add evaluation symbol"))
                menuitem.set_submenu(symbol_menu2)
                menu.append(menuitem)

                menuitem = gtk.MenuItem(_("Remove symols"))
                menuitem.connect('activate', self.remove_symbols, board)
                menu.append(menuitem)

                if board not in self.gamemodel.variations[0]:
                    for vari in self.gamemodel.variations[1:]:
                        if board in vari:
                            menuitem = gtk.MenuItem(_("Remove variation"))
                            menuitem.connect('activate', self.remove_variation, board, parent, vari)
                            menu.append(menuitem)
                            break

                menu.show_all()
                menu.popup( None, None, None, event.button, event.time)
        return True

    def edit_comment(self, widget=None, board=None, index=0):
        dialog = gtk.Dialog(_("Edit comment"),
                     None,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        textedit = gtk.TextView()
        textedit.set_editable(True)
        textedit.set_cursor_visible(True)
        textedit.set_wrap_mode(gtk.WRAP_WORD)

        textbuffer = textedit.get_buffer()
        if not board.children:
            board.children.append("")
        elif not isinstance(board.children[index], basestring):
            board.children.insert(index, "")
        textbuffer.set_text(board.children[index])
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(textedit)

        dialog.vbox.add(sw)
        dialog.resize(300, 200)
        dialog.show_all()

        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT:
            dialog.destroy()
            (iter_first, iter_last) = textbuffer.get_bounds()
            comment = textbuffer.get_text(iter_first, iter_last)
            if board.children[index] != comment:
                board.children[index] = comment
                self.gamemodel.needsSave = True
                self.update()
        else:
            dialog.destroy()

    def symbol_menu1_activate(self, widget, board, symbol):
        if len(board.nags) == 0:
            board.nags.append(symbol2nag(symbol))
            self.gamemodel.needsSave = True
        else:
            if board.nags[0] != symbol2nag(symbol):
                board.nags[0] = symbol2nag(symbol)
                self.gamemodel.needsSave = True
        if self.gamemodel.needsSave:
            self.update()

    def symbol_menu2_activate(self, widget, board, symbol):
        if len(board.nags) == 0:
            board.nags.append("")
            board.nags.append(symbol2nag(symbol))
            self.gamemodel.needsSave = True
        if len(board.nags) == 1:
            board.nags.append(symbol2nag(symbol))
            self.gamemodel.needsSave = True
        else:
            if board.nags[1] != symbol2nag(symbol):
                board.nags[1] = symbol2nag(symbol)
                self.gamemodel.needsSave = True
        if self.gamemodel.needsSave:
            self.update()

    def remove_symbols(self, widget, board):
        if board.nags:
            board.nags = []
            self.update()
            self.gamemodel.needsSave = True

    def remove_variation(self, widget, board, parent, vari):
        self.gamemodel.variations.remove(vari)
        for child in parent.children:
            if isinstance(child, list) and board in child:
                parent.children.remove(child)
                break
        self.update()
        self.gamemodel.needsSave = True
        
        if self.gamemodel.getBoardAtPly(self.boardview.shown) in vari:
            self.setShown(parent)

    def setShown(self, board):
        if board in self.gamemodel.boards:
            self.boardview.shown = self.gamemodel.boards.index(board) + self.gamemodel.lowply
        else:
            for vari in self.gamemodel.variations:
                if board in vari:
                    # Go back to the common board of variations to let animation system work
                    board_in_vari = board
                    while board_in_vari not in self.gamemodel.boards:
                        board_in_vari = vari[board_in_vari.ply-self.gamemodel.lowply-1]
                    self.autoUpdateSelected = False
                    self.boardview.shown = board_in_vari.ply
                    break
            self.gamemodel.boards = vari
            self.autoUpdateSelected = True
            self.boardview.shown = self.gamemodel.boards.index(board) + self.gamemodel.lowply

    # Update the selected node highlight
    def update_selected_node(self):
        self.textbuffer.remove_tag_by_name("selected", self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter())
        start = None
        for ni in self.nodeIters:
            if ni["node"] == self.gamemodel.getBoardAtPly(self.boardview.shown):
                start = self.textbuffer.get_iter_at_offset(ni["start"])
                end = self.textbuffer.get_iter_at_offset(ni["end"])
                self.textbuffer.apply_tag_by_name("selected", start, end)
                break

        if start:
            self.textview.scroll_to_iter(start, 0, use_align=False, yalign=0.1)

    # Recursively insert the node tree
    def insert_nodes(self, node, level=0, ply=0, parent=None, result=None):
        buf = self.textbuffer
        end_iter = buf.get_end_iter # Convenience shortcut to the function
        new_line = False

        fan = conf.get("figuresInNotation", False)
        
        while True: 
            start = end_iter().get_offset()
            
            if node is None:
                break
            
            # Initial game or variation comment
            if node.prev is None:
                for index, child in enumerate(node.children):
                    if isinstance(child, basestring):
                        if node.ply == self.gamemodel.lowply:
                            self.insert_comment(child + "\n", node, index, level)
                        else:
                            self.insert_comment(child, node, index, level)
                node = node.next
                continue
            
            if ply > 0 and not new_line:
                buf.insert(end_iter(), " ")
            
            ply += 1

            movestr = self.__movestr(node, fan)
            buf.insert(end_iter(), movestr)
            
            startIter = buf.get_iter_at_offset(start)
            endIter = buf.get_iter_at_offset(end_iter().get_offset())
            
            if level == 0:
                buf.apply_tag_by_name("node", startIter, endIter)
                buf.apply_tag_by_name("margin", startIter, endIter)
            elif level == 1:
                buf.apply_tag_by_name("variation-toplevel", startIter, endIter)
                buf.apply_tag_by_name("variation-margin0", startIter, endIter)
            elif level % 2 == 0:
                buf.apply_tag_by_name("variation-even", startIter, endIter)
                buf.apply_tag_by_name("variation-margin1", startIter, endIter)
            else:
                buf.apply_tag_by_name("variation-uneven", startIter, endIter)
                buf.apply_tag_by_name("variation-margin2", startIter, endIter)

            if self.boardview.shown >= self.gamemodel.lowply and \
               node == self.gamemodel.getBoardAtPly(self.boardview.shown):
                buf.apply_tag_by_name("selected", startIter, endIter)
                
            ni = {}
            ni["node"] = node
            ni["start"] = start       
            ni["end"] = end_iter().get_offset()
            ni["parent"] = parent
            self.nodeIters.append(ni)
            
            buf.insert(end_iter(), " ")

            new_line = False
            for index, child in enumerate(node.children):
                if isinstance(child, basestring):
                    # comment
                    self.insert_comment(child, node, index, level)
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

    def insert_comment(self, comment, node, index, level=0):
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        start = end_iter().get_offset()

        if level > 0:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment", "margin")
        else:
            buf.insert_with_tags_by_name(end_iter(), comment, "comment")

        ci = {}
        ci["node"] = node
        ci["comment"] = comment
        ci["index"] = index
        ci["start"] = start     
        ci["end"] = end_iter().get_offset()
        self.commentIters.append(ci)
        
        buf.insert(end_iter(), " ")

    def insert_header(self, gm):
        buf = self.textbuffer
        end_iter = buf.get_end_iter

        #try:
        #    text = gm.tags['White']
        #except:
        #    # pgn not processed yet
        #    return
        text = repr(gm.players[0])

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
        self.insert_nodes(self.gamemodel.boards[0], result=reprResult[self.gamemodel.status])

    def shown_changed(self, board, shown):
        if self.autoUpdateSelected:
            self.update_selected_node()

    def moves_undoing(self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        for ni in reversed(self.nodeIters):
            if ni["node"] == self.gamemodel.variations[0][-moves]:
                start = self.textbuffer.get_iter_at_offset(ni["start"])
                break
        self.textbuffer.delete(start, end)

    def game_changed(self, game):
        if game.status != RUNNING:
            return

        node = game.getBoardAtPly(game.ply)
        buf = self.textbuffer
        end_iter = buf.get_end_iter
        start = end_iter().get_offset()
        fan = conf.get("figuresInNotation", False)

        buf.insert(end_iter(), self.__movestr(node, fan) + " ")

        startIter = buf.get_iter_at_offset(start)
        endIter = buf.get_iter_at_offset(end_iter().get_offset())

        buf.apply_tag_by_name("node", startIter, endIter)

        ni = {}
        ni["node"] = node
        ni["start"] = startIter.get_offset()        
        ni["end"] = end_iter().get_offset()

        self.nodeIters.append(ni)
        self.update_selected_node()

    def __movestr(self, node, fan):
        move = Move(node.board.history[-1][0])
        if fan:
            movestr = toFAN(node.prev, move)
        else:
            movestr =  toSAN(node.prev, move, True)
        nagsymbols = "".join([nag2symbol(nag) for nag in node.nags])
        # To prevent wrap castling we will use hyphen bullet (U+2043)
        return "%s%s%s" % (move_count(node), movestr.replace("-","⁃"), nagsymbols)
