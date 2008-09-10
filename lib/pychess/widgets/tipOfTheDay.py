import gtk.glade, os
from pychess.System import conf
from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix
from random import randrange

uistuff.cacheGladefile("tipoftheday.glade")

class TipOfTheDay:
    
    @classmethod
    def _init (cls):
        cls.widgets = uistuff.GladeWidgets("tipoftheday.glade")
        
        uistuff.keepWindowSize("tipoftheday", cls.widgets["window1"],
                               (320,240), uistuff.POSITION_CENTER)
        
        cls.widgets["checkbutton1"].set_active(conf.get("show_tip_at_startup", False))
        cls.widgets["checkbutton1"].connect("toggled",
            lambda w: conf.set("show_tip_at_startup", w.get_active()))
        
        cls.widgets["close_button"].connect("clicked",
            lambda w: cls.widgets["window1"].emit("delete-event", None))
        cls.widgets["window1"].connect("delete_event",
            lambda w, a: cls.widgets["window1"].hide())
        
        cls.widgets["back_button"].connect("clicked",
            lambda w: cls.set_currentIndex(cls.currentIndex-1))
        cls.widgets["forward_button"].connect("clicked",
            lambda w: cls.set_currentIndex(cls.currentIndex+1))
        
        cls.currentIndex = 0
    
    
    @classmethod
    def show (cls):
        if not hasattr(cls, "widgets"):
            cls._init()
        cls.set_currentIndex(randrange(len(tips)))
        cls.widgets["window1"].show()
    
    
    @classmethod
    def set_currentIndex (cls, value):
        if len(tips) == 0: return
        if value < 0: value = len(tips)-1
        elif value >= len(tips): value = 0
        cls.currentIndex = value
        cls.widgets["tipfield"].set_markup(tips[value])

tips = (
    _("You can start a new game by pressing <b>Game -> New Game</b>"),
    _("Do you know that it is possible to finish a chess game in just 2 turns?"),
    _("The number of Shannon as rough estimates of the number of possible bids in the game of chess, which is 10<sup>123</sup> and, as comparison, the number of atoms in the universe is estimated in 4x10<sup>78</sup> and 6x10<sup>79</sup>."),
    _("A tip a day keeps the doctor away"),
    _("Do you can help translate Pychess in your language, pressing <b>Help -> Translate Pychess</b>"),
    _("Do you can call flag when the clock is with you, pressing <b>Actions -> Call Flag</b>"),
    _("If you want to win all your chessmatches..."),
)
