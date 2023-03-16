from pychess.Utils.const import (
    EUROSHOGICHESS,
    VARIANTS_OTHER_NONSTANDARD,
    A8,
    B8,
    C8,
    D8,
    E8,
    F8,
    G8,
    H8,
    A7,
    B7,
    C7,
    D7,
    E7,
    F7,
    G7,
    H7,
    A6,
    B6,
    C6,
    D6,
    E6,
    F6,
    G6,
    H6,
    A1,
    B1,
    C1,
    D1,
    E1,
    F1,
    G1,
    H1,
    A2,
    B2,
    C2,
    D2,
    E2,
    F2,
    G2,
    H2,
    A3,
    B3,
    C3,
    D3,
    E3,
    F3,
    G3,
    H3,
)


from pychess.Utils.Board import Board

EUROSHOGISTART = "1nbqkqn1/1r4b1/pppppppp/8/8/PPPPPPPP/1B4R1/1NQKQBN1 w - - 0 1"


class EuroShogiBoard(Board):
    variant = EUROSHOGICHESS
    __desc__ = _("EuroShogi: http://en.wikipedia.org/wiki/EuroShogi")
    name = _("EuroShogi")
    cecp_name = "euroshogi"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    PROMOTION_ZONE = (
        (
            A8,
            B8,
            C8,
            D8,
            E8,
            F8,
            G8,
            H8,
            A7,
            B7,
            C7,
            D7,
            E7,
            F7,
            G7,
            H7,
            A6,
            B6,
            C6,
            D6,
            E6,
            F6,
            G6,
            H6,
        ),
        (
            A1,
            B1,
            C1,
            D1,
            E1,
            F1,
            G1,
            H1,
            A2,
            B2,
            C2,
            D2,
            E2,
            F2,
            G2,
            H2,
            A3,
            B3,
            C3,
            D3,
            E3,
            F3,
            G3,
            H3,
        ),
    )

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=EUROSHOGISTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)
