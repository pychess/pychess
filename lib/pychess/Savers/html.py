# -*- coding: utf-8 -*-

from pychess.System import conf
from pychess.Utils.const import FAN_PIECES, BLACK, WHITE

__label__ = _("Html Diagram")
__ending__ = "html"
__append__ = False

SIZE = 40
BORDER_SIZE = SIZE // 4 + SIZE // 8
FILL = SIZE - BORDER_SIZE
FONT_SIZE = SIZE - 4

#    font-family: "ChessMedium";

style = """
.chessboard {
    width: %spx;
    height: %spx;
    font-family: "DejaVu Serif", "DejaVu", serif;
    line-height: %spx;
}
.black {
    float: left;
    width: %spx;
    height: %spx;
    background-color: #999;
    font-size:%spx;
    text-align:center;
    display: table-cell;
    vertical-align:middle;
}
.white {
    float: left;
    width: %spx;
    height: %spx;
    background-color: #fff;
    font-size:%spx;
    text-align:center;
    display: table-cell;
    vertical-align:middle;
}
.fill-top {
    float: left;
    width: %spx;
    height: %spx;
    color: #ffff;
    display: table-cell;
}
.top-corner {
    float: left;
    width: %spx;
    height: %spx;
    background-color: #333;
    display: table-cell;
}
.top {
    float: left;
    width: %spx;
    height: %spx;
    background-color: #333;
    display: table-cell;
}
.fill-side {
    float: left;
    width: %spx;
    height: %spx;
    color: #ffff;
    display: table-cell;
}
.side {
    float: left;
    width: %spx;
    height: %spx;
    color: #ffff;
    background-color: #333;
    font-size: %spx;
    text-align:center;
    display: table-cell;
    vertical-align:middle;
}
.bottom-corner {
    float: left;
    width: %spx;
    height: %spx;
    background-color: #333;
    display: table-cell;
}
.bottom {
    float: left;
    width: %spx;
    height: %spx;
    color: #ffff;
    background-color: #333;
    font-size: %spx;
    line-height: %spx;
    text-align: center;
    display: table-cell;
}
""" % (
    SIZE * 10, SIZE * 10, SIZE,  # chessboard
    SIZE, SIZE, FONT_SIZE,  # black
    SIZE, SIZE, FONT_SIZE,  # white
    FILL, BORDER_SIZE,  # fill-top
    BORDER_SIZE, BORDER_SIZE,  # top-corner
    SIZE, BORDER_SIZE,  # top
    FILL, SIZE,  # fill-side
    BORDER_SIZE, SIZE, BORDER_SIZE,  # side
    BORDER_SIZE, BORDER_SIZE,  # bottom-corner
    SIZE, BORDER_SIZE, BORDER_SIZE, BORDER_SIZE  # bottom
)


def save(file, model, position=None, flip=False):
    """Export the current position into a .html file using html+css"""

    print("<html><head><meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>", file=file)
#    print('<link rel="stylesheet" media="screen" href="https://fontlibrary.org/face/chess" type="text/css"/>', file=file)
    print("<style type='text/css'>%s" % style, file=file)
    print("</style></head><body><div class='chessboard'>", file=file)

    show_cords = conf.get("showCords")
    cords_side = "12345678" if flip else "87654321"
    cords_bottom = "HGFEDCBA" if flip else "ABCDEFGH"

    data = model.boards[position].data[:]

    board = ""
    # header
    if show_cords:
        board += "<div class='fill-top'></div>"
        board += "<div class='top-corner'></div>"
        for cord in range(8):
            board += "<div class='top'></div>"
        board += "<div class='top-corner'></div>"
        board += "<div class='fill-top'></div>"
    for j, row in enumerate(data if flip else reversed(data)):
        if show_cords:
            board += "<div class='fill-side'></div>"
            board += "<div class='side'>%s</div>" % cords_side[j]
        for i in range(8):
            if j % 2 == 0:
                color = "white" if i % 2 == 0 else "black"
            else:
                color = "white" if i % 2 == 1 else "black"

            piece = row.get(i)
            if piece is not None:
                if piece.color == BLACK:
                    piece_fan = FAN_PIECES[BLACK][piece.piece]
                else:
                    piece_fan = FAN_PIECES[WHITE][piece.piece]
                board += "<div class='%s'>%s</div>" % (color, piece_fan)
            else:
                board += "<div class='%s'></div>" % color
        if show_cords:
            board += "<div class='side'></div>"
            board += "<div class='fill-side'></div>"
        board += "\n"

    if show_cords:
        board += "<div class='fill-top'></div>"
        board += "<div class='bottom-corner'></div>"
        for cord in cords_bottom:
            board += "<div class='bottom'>%s</div>" % cord
        board += "<div class='bottom-corner'></div>"
        board += "<div class='fill-top'></div>"

    print(board, file=file)

    print("</div></body></html>", file=file)

    file.close()


if __name__ == "__main__":
    from pychess.Utils.GameModel import GameModel
    model = GameModel()
    with open("/home/tamas/board.html", "w") as fi:
        save(fi, model, position=0, flip=True)
