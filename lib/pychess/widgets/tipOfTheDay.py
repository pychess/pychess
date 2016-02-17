from pychess.System import conf
from pychess.System import uistuff
from random import randrange


class TipOfTheDay:
    @classmethod
    def _init(cls):
        cls.widgets = uistuff.GladeWidgets("tipoftheday.glade")

        uistuff.keepWindowSize("tipoftheday", cls.widgets["window1"],
                               (320, 240), uistuff.POSITION_CENTER)

        cls.widgets["checkbutton1"].set_active(conf.get("show_tip_at_startup",
                                                        False))
        cls.widgets["checkbutton1"].connect(
            "toggled",
            lambda w: conf.set("show_tip_at_startup", w.get_active()))

        cls.widgets["close_button"].connect(
            "clicked",
            lambda w: cls.widgets["window1"].emit("delete-event", None))
        cls.widgets["window1"].connect(
            "delete_event", lambda w, a: cls.widgets["window1"].hide())

        cls.widgets["back_button"].connect(
            "clicked", lambda w: cls.set_currentIndex(cls.currentIndex - 1))
        cls.widgets["forward_button"].connect(
            "clicked", lambda w: cls.set_currentIndex(cls.currentIndex + 1))

        cls.currentIndex = 0

    @classmethod
    def show(cls):
        if not hasattr(cls, "widgets"):
            cls._init()
        cls.set_currentIndex(randrange(len(tips)))
        cls.widgets["window1"].show()

    @classmethod
    def set_currentIndex(cls, value):
        if len(tips) == 0:
            return
        if value < 0:
            value = len(tips) - 1
        elif value >= len(tips):
            value = 0
        cls.currentIndex = value
        cls.widgets["tipfield"].set_markup(tips[value])


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
