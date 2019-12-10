from .lutils.attack import getAttacks, piecesAttackingCord
from .const import NB_OF_CASES
from .lutils.ldata import PIECE_VALUES
from .Cord import Cord


# This file contains algorithm helping the users to choose the right decisions
# The first algorithm gives to the user all the pieces attacked and not protected by the foe
class DecisionSupportAlgorithm:

    def __init__(self):
        self.against_bot = False
        self.already_calculated = False

    def is_against_bot(self):
        return self.against_bot

    def set_foe_as_bot(self):
        self.against_bot = True

    def newTurn(self):
        self.already_calculated = False

    def calcul_done(self):
        return self.already_calculated

    def end_turn(self):
        self.already_calculated = True

    def attacked_and_not_protected(self, board, mycolor):
        """returns a list of coord containing all the cord attacked but not protected
        args : board of type Board, cord of type Cord, mycolor of value BLACK or WHITE

        1- board.color is the color that played last, and that is considered as below (white) in getAttacks"""

        coordinate_in_danger = []

        if self.is_against_bot():
            # TODO: tests
            for i in range(NB_OF_CASES):
                c = Cord(i)
                number, letter = c.cords
                piece = board.data[letter][number]
                if piece is not None:
                    if piece.color == mycolor:
                        attacks = getAttacks(board.board, c.cord, 1 - mycolor)
                        defense = getAttacks(board.board, c.cord, mycolor)

                        # if one of the piece is not protected but not attacked, danger
                        # means that towers are highlighted at the start of the game
                        if attacks == 0 and defense == 0:
                            c_colored = Cord(i, color="Y")
                            coordinate_in_danger.append(c_colored)
                            pass

                        # if one of the piece is not protected and attacked, very dangerous
                        if attacks != 0 and defense == 0:
                            c_colored = Cord(i, color="R")
                            coordinate_in_danger.append(c_colored)

                        # if one of the piece attacking is weaker than piece attacked, very dangerous
                        if attacks != 0:
                            pieces_attacking = piecesAttackingCord(board.board, c.cord, 1 - mycolor)
                            piece_attacking = pieces_attacking[0]
                            min_value = PIECE_VALUES[piece_attacking]
                            for piece_found in pieces_attacking:
                                if PIECE_VALUES[piece_found] <= min_value:
                                    min_value = PIECE_VALUES[piece_found]
                                    piece_attacking = piece_found
                            if PIECE_VALUES[piece_attacking] <= PIECE_VALUES[piece.piece]:
                                c_colored = Cord(i, color="R")
                                coordinate_in_danger.append(c_colored)

        return coordinate_in_danger
