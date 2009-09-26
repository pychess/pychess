from const import *

reprResult_long = {
    DRAW: _("The game ended in a draw"),
    WHITEWON: _("%(white)s won the game"),
    BLACKWON: _("%(black)s won the game"),
    KILLED: _("The game has been killed"),
    ADJOURNED: _("The game has been adjourned"),
    ABORTED: _("The game has been aborted"),
}

reprReason_long = {
    DRAW_INSUFFICIENT: _("Because no players had sufficient material to mate"),
    DRAW_REPITITION: _("Because the same position was repeated three times in a row"),
    DRAW_50MOVES: _("Because the last 50 moves brought nothing new"),
    DRAW_CALLFLAG: _("Because both players ran out of time"),
    DRAW_STALEMATE: _("Because %(mover)s stalemated"),
    DRAW_AGREE: _("Because the players agreed to"),
    DRAW_ADJUDICATION: _("Because of adjudication by an admin"),
    DRAW_LENGTH: _("Because the game exceed the max length"),
    DRAW_BLACKINSUFFICIENTANDWHITETIME: _("Because %(white)s ran out of time and %(black)s has insufficient material to mate"),
    DRAW_WHITEINSUFFICIENTANDBLACKTIME: _("Because %(black)s ran out of time and %(white)s has insufficient material to mate"),

    WON_RESIGN: _("Because %(loser)s resigned"),
    WON_CALLFLAG: _("Because %(loser)s ran out of time"),
    WON_MATE: _("Because %(loser)s was checkmated"),
    WON_DISCONNECTION: _("Because %(loser)s disconnected"),
    WON_ADJUDICATION:  _("Because of adjudication by an admin"),
    WON_NOMATERIAL: _("Because %(loser)s lost all pieces but the king"),

    ADJOURNED_LOST_CONNECTION: _("Because a player lost connection"),
    ADJOURNED_AGREEMENT: _("Because the players agreed to"),
    ADJOURNED_SERVER_SHUTDOWN: _("Because the server was shutdown"),
    ADJOURNED_COURTESY: _("Because a player lost connection and the other player requested adjournment"),

    ABORTED_ADJUDICATION: _("Because of adjudication by an admin"),
    ABORTED_AGREEMENT: _("Because the players agreed to"),
    ABORTED_COURTESY: _("Because of courtesy by a player"),
    ABORTED_EARLY: _("Because a player quit. No winner was found due to the early phase of the game"),
    ABORTED_SERVER_SHUTDOWN: _("Because the server was shutdown"),

    WHITE_ENGINE_DIED: _("Because the %(white)s engine died"),
    BLACK_ENGINE_DIED: _("Because the %(white)s engine died"),
    DISCONNECTED: _("Because the connection to the server was lost"),
    UNKNOWN_REASON: _("The reason is unknown")
}
