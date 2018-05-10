from random import randrange

from pychess.System import conf
from pychess.System import uistuff
from pychess.widgets import mainwindow


class TipOfTheDay:
    def __init__(self):
        self.widgets = uistuff.GladeWidgets("tipoftheday.glade")
        self.widgets["window1"].set_transient_for(mainwindow())
        uistuff.keepWindowSize("tipoftheday", self.widgets["window1"], (320, 240), uistuff.POSITION_CENTER)

        self.widgets["checkbutton1"].set_active(conf.get("show_tip_at_startup"))
        self.widgets["checkbutton1"].connect("toggled", lambda w: conf.set("show_tip_at_startup", w.get_active()))
        self.widgets["close_button"].connect("clicked", lambda w: self.widgets["window1"].emit("delete-event", None))
        self.widgets["window1"].connect("delete_event", lambda w, a: self.widgets["window1"].destroy())
        self.widgets["back_button"].connect("clicked", lambda w: self.set_currentIndex(self.currentIndex - 1))
        self.widgets["forward_button"].connect("clicked", lambda w: self.set_currentIndex(self.currentIndex + 1))

        self.currentIndex = 0

    def show(self):
        self.set_currentIndex(randrange(len(tips)))
        self.widgets["window1"].show()
        self.widgets["window1"].present()

    def set_currentIndex(self, value):
        if len(tips) == 0:
            return
        if value < 0:
            value = len(tips) - 1
        elif value >= len(tips):
            value = 0
        self.currentIndex = value
        self.widgets["tipfield"].set_markup(tips[value])


tips = (
    _("You can start a new game by <b>Game</b> > <b>New Game</b>, in New Game window do \
      you can choose <b>Players</b>, <b>Time Control</b> and <b>Chess Variants</b>."),
    _("You can choose from 20 different difficulties to play against the computer."),
    _("Chess Variants are like the pieces of the last line will be placed on the board."),
    _("To save a game <b>Game</b> > <b>Save Game As</b>, give the filename and choose where \
      you want to be saved. At the bottom choose extension type of the file, and <b>Save</b>."),
    _("Do you know that you can call flag when the clock is with you, <b>Actions</b> > <b>Call Flag</b>."),
    _("Pressing <b>Ctrl+Z</b> to offer opponent the possible rollback moves."),
    _("To play on <b>Fullscreen mode</b>, just type <b>F11</b>. Coming back, F11 again."),
    _("<b>Hint mode</b> analyzing your game, enable this type <b>Ctrl+H</b>."),
    _("<b>Spy mode</b> analyzing the oponnent game, enable this type <b>Ctrl+Y</b>."),
    _("You can play chess listening to the sounds of the game, for that, <b>Settings</b> > <b>Preferences</b> >\
      <b>Sound tab</b>, enable <b>Use sounds in PyChess</b> and choose your preferred sounds."),
    _("Do you know that you can help translate Pychess in your language, <b>Help</b> > <b>Translate Pychess</b>."),
    _("Do you know that it is possible to finish a chess game in just 2 turns?"),
    _("Do you know that the number of possible chess games exceeds the number of atoms in the Universe?"),
)
