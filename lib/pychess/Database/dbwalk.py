from pychess.Utils.const import DROP
from pychess.Utils.lutils.lmovegen import newMove

MAXMOVE = newMove(63, 63, DROP)
COMMENT, VARI_START, VARI_END, NAG = (MAXMOVE + i + 1 for i in range(4))


def walk(node, arr, txt):
    """Prepares a game data for databse.
       Recursively walks the node tree to collect moves and comments.
       Arguments:
       node - list (a tree of lboards created by the pgn parser)
       arr - array("H") (2 byte unsigned ints representing lmove objects
                        or COMMENT, VARI_START, VARI_END, NAG+nag)
       txt - list (comment strings)"""

    arr_append = arr.append
    while True:
        if node is None:
            break

        # Initial game or variation comment
        if node.prev is None:
            for child in node.children:
                if isinstance(child, str):
                    arr_append(COMMENT)
                    txt.append(child)
            node = node.next
            continue

        arr_append(node.lastMove)

        for nag in node.nags:
            if nag:
                arr_append(NAG + int(nag[1:]))

        for child in node.children:
            if isinstance(child, str):
                # comment
                arr_append(COMMENT)
                txt.append(child)
            else:
                # variations
                arr_append(VARI_START)
                walk(child[0], arr, txt)
                arr_append(VARI_END)

        if node.next:
            node = node.next
        else:
            break
