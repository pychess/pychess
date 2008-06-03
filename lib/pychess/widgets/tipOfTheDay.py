import gtk.glade, os
from pychess.System import conf
from pychess.System.uistuff import GladeWidgets
from pychess.System.prefix import addDataPrefix
from random import randrange

widgets = GladeWidgets("tipoftheday.glade")

widgets["checkbutton1"].set_active(conf.get("show_tip_at_startup", True))
widgets["checkbutton1"].connect("toggled",
    lambda w: conf.set("show_tip_at_startup", w.get_active()))

widgets["close_button"].connect("clicked",
    lambda w: widgets["window1"].hide())
widgets["window1"].connect("delete_event",
    lambda w, a: widgets["window1"].hide() or True)

widgets["back_button"].connect("clicked",
    lambda w: set_currentIndex(currentIndex-1))
widgets["forward_button"].connect("clicked",
    lambda w: set_currentIndex(currentIndex+1))

def show ():
    set_currentIndex(randrange(len(tips)))
    widgets["window1"].show()

currentIndex = 0
def set_currentIndex (value):
    if len(tips) == 0: return
    if value < 0: value = len(tips)-1
    elif value >= len(tips): value = 0
    global currentIndex
    currentIndex = value
    widgets["tipfield"].set_markup(tips[value])

tips = (
    _("You can start a new game by pressing <b>Game -> New Game</b>"),
    _("You can start the Tips of the day in the start of Pychess by pressing <b>Settings -> Preferences -> Show tips at startup</b>"),
    _("Do you know that it is possible to finish a chess game in just 2 turns?"),
    _("The number of Shannon as rough estimates of the number of possible bids in the game of chess, which is 10<sup>123</sup> and, as comparison, the number of atoms in the universe is estimated in 4x10<sup>78</sup> and 6x10<sup>79</sup>."),
    _("A tip a day keeps the doctor away"),
    _("Do you can help translate Pychess in your language, pressing <b>Help -> Translate Pychess</b>"),
    _("Do you can call flag when the clock is with you, pressing <b>Actions -> Call Flag</b>"),
    _("If you want to win all your chessmatches..."),
)
