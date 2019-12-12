from .lutils.attack import getAttacks, piecesAttackingCord
from .const import NB_OF_CASES
from .lutils.ldata import PIECE_VALUES
from .Cord import Cord
from pychess.System import conf


# This file contains algorithm helping the users to choose the right decisions
# The first algorithm gives to the user all the pieces attacked and not protected by the foe
class DecisionSupportAlgorithm:

    def __init__(self):
        self.against_bot = False
        self.activationEnabled = False

        # to avoid calculating once more the coordinates, we save them
        self.coordinate_in_danger = []

    def enableDisableAlgo(self, enable_algorithm):
        self.activationEnabled = enable_algorithm

    def set_foe_as_bot(self):
        self.against_bot = True

    def calculate_coordinate_in_danger(self, board, mycolor, newTurn=True):
        '''this function should be used'''
        if not newTurn:
            return self.coordinate_in_danger

        self.coordinate_in_danger = []

        self.coordinate_in_danger = self.__not_protected(board, mycolor, newTurn)
        self.coordinate_in_danger += self.__attacked_and_not_protected(board, mycolor, newTurn)

        return self.coordinate_in_danger

    def __not_protected(self, board, mycolor, newTurn=True):
        """returns a list of coord containing all the cord not protected and not attacked
        args : board of type Board, cord of type Cord, mycolor of value BLACK or WHITE

        1- board.color is the color that played last, and that is considered as below (white) in getAttacks"""

        coordinate_in_danger = []

        if self.against_bot and self.activationEnabled:
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


        return coordinate_in_danger

    def __attacked_and_not_protected(self, board, mycolor, newTurn=True):
        """returns a list of coord containing all the cord attacked but not protected
        args : board of type Board, cord of type Cord, mycolor of value BLACK or WHITE

        1- board.color is the color that played last, and that is considered as below (white) in getAttacks"""

        coordinate_in_danger = []

        if self.against_bot and self.activationEnabled:
            # TODO: tests
            for i in range(NB_OF_CASES):
                c = Cord(i)
                number, letter = c.cords
                piece = board.data[letter][number]
                if piece is not None:
                    if piece.color == mycolor:
                        attacks = getAttacks(board.board, c.cord, 1 - mycolor)
                        defense = getAttacks(board.board, c.cord, mycolor)

                        if attacks != 0:
                            # if one of the piece is not protected and attacked, very dangerous
                            if defense == 0:
                                c_colored = Cord(i, color="R")
                                coordinate_in_danger.append(c_colored)
                            else:
                                # if one of the piece attacking is weaker than piece attacked, very dangerous

                                # in this part we find the weakest ennemy pieces attacking our piece
                                pieces_attacking = piecesAttackingCord(board.board, c.cord, 1 - mycolor)
                                piece_attacking = pieces_attacking[0]
                                min_value = PIECE_VALUES[piece_attacking]
                                for piece_found in pieces_attacking:
                                    if PIECE_VALUES[piece_found] <= min_value:
                                        min_value = PIECE_VALUES[piece_found]
                                        piece_attacking = piece_found

                                # then we compare it to the value of the piece
                                # currently, we consider trades as not dangerous, this behaviour could be changed
                                if PIECE_VALUES[piece_attacking] < PIECE_VALUES[piece.piece]:
                                    c_colored = Cord(i, color="R")
                                    coordinate_in_danger.append(c_colored)

        return coordinate_in_danger
