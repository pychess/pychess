# -*- coding: UTF-8 -*-

from pychess.Utils.const import WHITE, WHITEWON, BLACK, BLACKWON, DRAW


def get_elo_rating_change(model, overridden_welo, overridden_belo):
    """ http://www.fide.com/fide/handbook.html?id=197&view=article (§8.5, July 2017) """

    def individual_elo_change(elo_player, elo_opponent, blitz):
        result = {}

        # Adaptation of the inbound parameters
        pprov = '?' in elo_player
        try:
            pval = int(elo_player.replace("?", ""))
        except ValueError:
            pval = 0
        try:
            oval = int(elo_opponent.replace("?", ""))
        except ValueError:
            oval = 0
        if pval == 0 or oval == 0:
            return None

        # Development coefficient - We ignore the age of the player and we assume that
        # he is already rated. The provisional flag '?' just denotes that he has not
        # played his first 30 games, but it may also denotes that he never had any
        # ranking. The calculation being based on the current game only, we can't
        # handle that second specific case
        if blitz:
            k = 20
        else:
            if pprov:
                k = 40
            else:
                if pval >= 2400:
                    k = 10
                else:
                    k = 20

        # Probability of gain
        d = pval - oval
        d = max(-400, d)
        d = min(400, d)
        # The approximate formula should not be used : result["pd"] = 1.0/(1+10**(-d/400))
        pd = [50, 50, 50, 50, 51, 51, 51, 51, 51, 51, 51, 52, 52, 52, 52, 52, 52, 52, 53, 53,
              53, 53, 53, 53, 53, 53, 54, 54, 54, 54, 54, 54, 54, 55, 55, 55, 55, 55, 55, 55,
              56, 56, 56, 56, 56, 56, 56, 57, 57, 57, 57, 57, 57, 57, 58, 58, 58, 58, 58, 58,
              58, 58, 59, 59, 59, 59, 59, 59, 59, 60, 60, 60, 60, 60, 60, 60, 60, 61, 61, 61,
              61, 61, 61, 61, 62, 62, 62, 62, 62, 62, 62, 62, 63, 63, 63, 63, 63, 63, 63, 64,
              64, 64, 64, 64, 64, 64, 64, 65, 65, 65, 65, 65, 65, 65, 66, 66, 66, 66, 66, 66,
              66, 66, 67, 67, 67, 67, 67, 67, 67, 67, 68, 68, 68, 68, 68, 68, 68, 68, 69, 69,
              69, 69, 69, 69, 69, 69, 70, 70, 70, 70, 70, 70, 70, 70, 71, 71, 71, 71, 71, 71,
              71, 71, 71, 72, 72, 72, 72, 72, 72, 72, 72, 73, 73, 73, 73, 73, 73, 73, 73, 73,
              74, 74, 74, 74, 74, 74, 74, 74, 74, 75, 75, 75, 75, 75, 75, 75, 75, 75, 76, 76,
              76, 76, 76, 76, 76, 76, 76, 77, 77, 77, 77, 77, 77, 77, 77, 77, 78, 78, 78, 78,
              78, 78, 78, 78, 78, 78, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 80, 80, 80, 80,
              80, 80, 80, 80, 80, 80, 81, 81, 81, 81, 81, 81, 81, 81, 81, 81, 81, 82, 82, 82,
              82, 82, 82, 82, 82, 82, 82, 82, 83, 83, 83, 83, 83, 83, 83, 83, 83, 83, 83, 84,
              84, 84, 84, 84, 84, 84, 84, 84, 84, 84, 84, 85, 85, 85, 85, 85, 85, 85, 85, 85,
              85, 85, 85, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 87, 87, 87, 87,
              87, 87, 87, 87, 87, 87, 87, 87, 87, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88, 88,
              88, 88, 88, 88, 88, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 90, 90,
              90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 91, 91, 91, 91, 91,
              91, 91, 91, 91, 91, 91, 91, 91, 91, 91, 91, 91, 92, 92, 92, 92, 92, 92, 92, 92,
              92][abs(d)] / 100.0
        result["pd"] = pd if pval >= oval else 1.0 - pd

        # New difference in Elo for loss, draw, win
        for score in [0, 1, 2]:
            result["diff%d" % score] = round(k * ([0, 0.5, 1][score] - result["pd"]), 1)

        # Result
        return result

    # Gathering of the data
    welo = model.tags["WhiteElo"] if overridden_welo is None else overridden_welo
    belo = model.tags["BlackElo"] if overridden_belo is None else overridden_belo
    blitz = model.timemodel.isBlitzFide()

    # Result
    result = [None, None]
    result[WHITE] = individual_elo_change(welo, belo, blitz)
    result[BLACK] = individual_elo_change(belo, welo, blitz)
    return None if result[WHITE] is None or result[BLACK] is None else result


def get_elo_rating_change_str(model, player, overridden_welo, overridden_belo):
    """ Determination of the ELO rating change """

    erc = get_elo_rating_change(model, overridden_welo, overridden_belo)
    if erc is None:
        return ""
    erc = erc[player]

    # Status of the game
    if (model.status == WHITEWON and player == WHITE) or (model.status == BLACKWON and player == BLACK):
        d = 2
    else:
        if (model.status == WHITEWON and player == BLACK) or (model.status == BLACKWON and player == WHITE):
            d = 0
        else:
            if model.status == DRAW:
                d = 1
            else:
                return "%.0f%%, %.1f / %.1f / %.1f" % (100 * erc["pd"], erc["diff0"], erc["diff1"], erc["diff2"])

    # Result
    return "%s%.1f" % ("+" if erc["diff%d" % d] > 0 else "", erc["diff%d" % d])


def get_elo_rating_change_pgn(model, player):
    # One move must occur to validate the rating
    if model.ply == 0:
        return ""

    # Retrieval of the statistics for the player
    data = get_elo_rating_change(model, None, None)
    if data is None:
        return ""
    data = data[player]

    # Status of the game
    if (model.status == WHITEWON and player == WHITE) or (model.status == BLACKWON and player == BLACK):
        d = 2
    else:
        if (model.status == WHITEWON and player == BLACK) or (model.status == BLACKWON and player == WHITE):
            d = 0
        else:
            if model.status == DRAW:
                d = 1
            else:
                return ""

    # Result is rounded to the nearest integer
    r = int(round(data["diff%s" % d], 0))
    return "+%d" % r if r > 0 else str(r)
