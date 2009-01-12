from const import *

reprResult_long = {
    DRAW: _("The game ended in a draw"),
    WHITEWON: _("White player won the game"),
    BLACKWON: _("Black player won the game"),
    KILLED: _("The game has been killed"),
    ADJOURNED: _("The game has been adjourned"),
    ABORTED: _("The game has been aborted"),
}

reprReason_long = {
    DRAW_INSUFFICIENT: _("caused by insufficient material"),
    DRAW_REPITITION: _("as the same position was repeated three times in a row"),
    DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
    DRAW_CALLFLAG: _("as both players ran out of time"),
    DRAW_STALEMATE: _("because of stalemate"),
    DRAW_AGREE: _("as the players agreed to"),
    DRAW_ADJUDICATION: _("as decided by an admin"),
    DRAW_LENGTH: _("as game exceed the max length"),
    
    WON_RESIGN: _("as opponent resigned"),
    WON_CALLFLAG: _("as opponent ran out of time"),
    WON_MATE: _("on a mate"),
    WON_DISCONNECTION: _("as opponent disconnected"),
    WON_ADJUDICATION:  _("as decided by an admin"),
    WON_NOMATERIAL: _("by losing all pieces except the king"),
    
    ADJOURNED_LOST_CONNECTION: _("as a player lost connection"),
    ADJOURNED_AGREEMENT: _("as the players agreed to"),
    ADJOURNED_SERVER_SHUTDOWN: _("as the server was shut down"),
    
    ABORTED_ADJUDICATION: _("as decided by an admin"),
    ABORTED_AGREEMENT: _("as the players agreed to"),
    ABORTED_COURTESY: _("by courtesy by a player"),
    ABORTED_EARLY: _("in the early phase of the game"),
    ABORTED_SERVER_SHUTDOWN: _("as the server was shut down"),
    
    WHITE_ENGINE_DIED: _("as the white engine died"),
    BLACK_ENGINE_DIED: _("as the black engine died"),
    UNKNOWN_REASON: _("by no known reason")
}
