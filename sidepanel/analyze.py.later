import gtk
from System.Log import log

__title__ = _("Analyzis")

label = gtk.Label()
__widget__ = gtk.ScrolledWindow()
__widget__.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
__widget__.add_with_viewport(label)
__widget__.show_all()

def ready (window):
    window.oracle.connect("foretold_move", foretold_move)
    window.oracle.connect("foretold_end", foretold_end)
    window.oracle.connect("clear", clear)
    window.oracle.connect("rmfirst", rmfirst)
    label.set_text("Waiting...")

import gobject
def once (func):
    def helper():
        func()
        return False
    gobject.idle_add(helper)

def foretold_move (oracle, move, score):
    no = len(oracle.history.moves)
    if label.get_text() != "Waiting...":
        text = "%s\n%d: %s\t%d" % (label.get_text(), no, str(move), score)
    else: text = "%d: %s\t%d" % (no, str(move), score)
    once (lambda: label.set_text(text))

def clear (oracle):
    once (lambda: label.set_text("Waiting..."))

def rmfirst (oracle):
    text = "\n".join(label.get_text().split("\n")[1:])
    once (lambda: label.set_text(text))

from Utils.validator import DRAW, WHITEWON, BLACKWON
def foretold_end (oracle, moves, endtype):
    endtype = endtype == DRAW and "draw" or "mate"
    log.warn("Foresaw %s in %d moves!" % (endtype, moves))
