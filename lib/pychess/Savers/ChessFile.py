import datetime
from pychess.Utils.const import RUNNING


class LoadingError(Exception):
    pass


class ChessFile:
    """ This class describes an opened chessfile.
        It is lazy in the sense of not parsing any games,
        that the user don't request.
        It has no catching. """

    def __init__(self, games):
        """ Games should be a list of the raw file data,
            split such that games[0] is used for game 0 etc.
            SourceUri must be the
            """
        self.games = games
        self.sourceUri = None

    def loadToModel(self, gameno, position, model=None):
        """ Load the data of game "gameno" into the gamemodel
            If no model is specified, a new one will be created, loaded and
            returned """
        raise NotImplementedError

    def __len__(self):
        return len(self.games)

    def get_player_names(self, gameno):
        """ Returns a tuple of the players names
            Default is ("Unknown", "Unknown") if nothing is specified """
        return ("Unknown", "Unknown")

    def get_elo(self, gameno):
        """ Returns a tuple of the players rating in ELO format
            Default is 1600 if nothing is specified in the file """
        return (1600, 1600)

    def get_date(self, gameno):
        """ Returns a tuple (year,month,day) of the game date
            Default is current time if nothing is specified in the file """
        today = datetime.date.today()
        return today.timetuple()[:3]

    def get_site(self, gameno):
        """ Returns the location at which the game took place
            Default is "?" if nothing is specified in the file """
        return "?"

    def get_event(self, gameno):
        """ Returns the event at which the game took place
            Could be "World Chess Cup" or "My local tournament"
            Default is "?" if nothing is specified in the file """
        return "?"

    def get_round(self, gameno):
        """ Returns the round of the event at which the game took place
            Pgn supports having subrounds like 2.1.5,
            but as of writing, only the first int is returned.
            Default is 1 if nothing is specified in the file """
        return 1

    def get_result(self, gameno):
        """ Returns the result of the game
            Can be any of: RUNNING, DRAW, WHITEWON or BLACKWON
            Default is RUNNING if nothing is specified in the file """
        return RUNNING
