from .lutils.attack import getAttacks, piecesAttackingCord
from .const import NB_OF_CASES
from .lutils.ldata import PIECE_VALUES
from .Cord import Cord
from pychess.Utils.const import KING


# This file contains algorithm helping the users to choose the right decisions
# The first algorithm gives to the user all the pieces attacked and not protected by the foe
class DecisionSupportAlgorithm:
    def __init__(self):
        self.local_game = False
        self.activationEnabled = False

        # to avoid calculating once more the coordinates, we save them
        self.coordinate_in_danger = []

    def enableDisableAlgo(self, enable_algorithm):
        self.activationEnabled = enable_algorithm

    def set_foe_as_bot(self):
        self.local_game = True

    def calculate_coordinate_in_danger(self, board, mycolor, newTurn=True):
        """this function should be used for applying the algorithm"""
        if not newTurn:
            return self.coordinate_in_danger

        self.coordinate_in_danger = []

        self.coordinate_in_danger = self.__apply_algorithm(
            board, mycolor, self.__not_protected
        )
        self.coordinate_in_danger += self.__apply_algorithm(
            board, mycolor, self.__attacked_and_not_protected
        )

        return self.coordinate_in_danger

    def __apply_algorithm(self, board, mycolor, algorithm):
        """returns the list of coordinate in danger for player playing with mycolor pieces
         according to the algorithm used
        args : board of type Board, coordinate of type Cord, algorithm : function taking two arguments
        board, mycolor and the current coordinate we are looking

        WARNING : The king is currently excluded of the calculus => it is never considered as in danger
        """
        coordinate_in_danger = []

        if self.local_game and self.activationEnabled:
            # TODO: tests
            for i in range(NB_OF_CASES):
                c = Cord(i)
                number, letter = c.cords
                piece = board.data[letter][number]
                if piece is not None and piece.piece is not KING:
                    if piece.color == mycolor:
                        coordinate_in_color = algorithm(board, mycolor, c)
                        if coordinate_in_color is not None:
                            coordinate_in_danger.append(coordinate_in_color)

        return coordinate_in_danger

    def __not_protected(self, board, mycolor, coordinate):
        """returns the coord with the color yellow if the coord is not protected, None if it is
        args : board of type Board, coordinate of type Cord, mycolor of value BLACK or WHITE
        which is the color of the player who will play the next move"""

        c_colored = None
        attacks = getAttacks(board.board, coordinate.cord, 1 - mycolor)
        defense = getAttacks(board.board, coordinate.cord, mycolor)

        # if one of the piece is not protected but not attacked, danger
        # means that towers are highlighted at the start of the game
        if attacks == 0 and defense == 0:
            c_colored = Cord(coordinate.cord, color="Y")

        return c_colored

    def __attacked_and_not_protected(self, board, mycolor, coordinate):
        """returns the coord with the color red if the coord is not protected and attacked, None if it is not
        args : board of type Board, cord of type Cord, mycolor of value BLACK or WHITE
        which is the color of the player who will play the next move"""

        pieces_attacking = piecesAttackingCord(
            board.board, coordinate.cord, 1 - mycolor
        )
        defense = getAttacks(board.board, coordinate.cord, mycolor)

        c_colored = None

        number, letter = coordinate.cords
        piece = board.data[letter][number]

        if len(pieces_attacking) != 0:
            # if one of the piece is not protected and attacked, very dangerous
            if defense == 0:
                c_colored = Cord(coordinate.cord, color="R")
            else:
                # if one of the piece attacking is weaker than piece attacked, very dangerous

                # in this part we find the weakest ennemy pieces attacking our piece
                piece_attacking = pieces_attacking[0]
                min_value = PIECE_VALUES[piece_attacking]
                for piece_found in pieces_attacking:
                    if PIECE_VALUES[piece_found] <= min_value:
                        min_value = PIECE_VALUES[piece_found]
                        piece_attacking = piece_found

                # then we compare it to the value of the piece
                # currently, we consider trades as not dangerous, this behaviour could be changed
                if PIECE_VALUES[piece_attacking] < PIECE_VALUES[piece.piece]:
                    c_colored = Cord(coordinate.cord, color="R")

        return c_colored
