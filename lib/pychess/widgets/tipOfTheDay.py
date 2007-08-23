import gtk.glade, os
from pychess.System import conf
from pychess.System.WidgetDic import WidgetDic
from pychess.Utils.const import prefix
from random import randrange

widgets = WidgetDic(gtk.glade.XML(prefix("glade/tipoftheday.glade")))

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
    "You can start a new game by pressing <b>Game -> New Game</b>",
    "A tip a day keeps the doctor away",
    "If you want to win all your chessmatches...",
    "<b>England</b> is the largest and most populous of the constituent countries of the United Kingdom. The division dates from the arrival of the Anglo-Saxons in the 5th century. The territory of England has been politically united since the 10th century. This article concerns that territory. However, before the 10th century and after the accession of James VI of Scotland to the throne of England in 1603, it becomes less convenient to distinguish Scottish and Welsh from English history since the union of these nations with England.",
)
