#!/usr/bin/python
# -*- coding: UTF-8 -*-

#from unittest import TestCase
#from unittest import main

#class Validator (TestCase):
#    
#    def 

from pychess.Utils.History import startBoard
from pychess.Utils.validator import findMoves2

def moves2String (board):
    moves = [move for move in findMoves2(board)]
    return sorted(str(moves)[1:-1].split(", "))

[('a2a3',
    ["":None,"":None]),
 ('a2a4',
    ["":None,"":None]),
 ('b1a3':
    ["":None,"":None]),
 'b1c3':, 'b2b3':, 'b2b4':, 'c2c3':, 'c2c4':, 'd2d3':, 'd2d4':, 'e2e3':, 'e2e4':, 'f2f3':, 'f2f4':, 'g1f3':, 'g1h3':, 'g2g3':, 'g2g4':, 'h2h3':, 'h2h4':]

print moves2String(startBoard())
