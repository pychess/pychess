# Chess960 (Fischer Random Chess) utils
# http://en.wikipedia.org/wiki/Chess960

import random


def shuffle_start():
  """ Create a random initial position"""
  
  positions = [1, 2, 3, 4, 5, 6, 7, 8]
  tmp = [''] * 8
  
  bishop = random.choice((1, 3, 5, 7))
  tmp[bishop-1] = 'b'
  positions.remove(bishop)

  bishop = random.choice((2, 4, 6, 8))
  tmp[bishop-1] = 'b'
  positions.remove(bishop)

  queen = random.choice(positions)
  tmp[queen-1] = 'q'
  positions.remove(queen)
  
  knight = random.choice(positions)
  tmp[knight-1] = 'n'
  positions.remove(knight)

  knight = random.choice(positions)
  tmp[knight-1] = 'n'
  positions.remove(knight)

  rook = positions[0]
  tmp[rook-1] = 'r'

  king = positions[1]
  tmp[king-1] = 'k'

  rook = positions[2]
  tmp[rook-1] = 'r'
  
  tmp = ''.join(tmp)
  tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w KQkq - 0 1'
  
  return tmp


if __name__ == '__main__':
  for i in range(10):
    print shuffle_start()
