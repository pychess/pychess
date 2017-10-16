import datetime
from pychess.Utils.const import RUNNING


class LoadingError(Exception):
    pass


class ChessFile:
    """ This class describes an opened chessfile.
        It is lazy in the sense of not parsing any games,
        that the user don't request.
        It has no catching. """

    def __init__(self, file):
        self.file = file
        self.path = file.name if hasattr(file, "name") else None
        self.games = []
        self.offs_ply = {}

    def close(self):
        try:
            self.file.close()
        except OSError:
            pass

    def set_tags_filter(self, text):
        pass

    def set_fen_filter(self, fen):
        pass

    def set_scout_filter(self, query):
        pass

    def get_id(self, gameno):
        return gameno

    def get_records(self, direction=0):
        return self.games, self.offs_ply

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

    def get_variant(self, gameno):
        return 0

    def get_book_moves(self, fen=None):
        return []

    def get_info(self, gameno):
        return None
