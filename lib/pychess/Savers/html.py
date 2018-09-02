# -*- coding: utf-8 -*-

from pychess.Utils.const import FAN_PIECES, BLACK, WHITE

__label__ = _("Html Diagram")
__ending__ = "html"
__append__ = False

SIZE = 40

style = """
.chessboard {
    width: %spx;
    height: %spx;
    border: %spx solid #333;
    font-family: "DejaVu Serif", "DejaVu", serif;
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
""" % (SIZE * 8, SIZE * 8, SIZE // 4, SIZE, SIZE, SIZE, SIZE, SIZE, SIZE)


def save(file, model, position=None):
    """Export the current position into a .html file using html+css"""

    print("<html><head><meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>", file=file)
    print("<style type='text/css'>%s" % style, file=file)
    print("</style></head><body><div class='chessboard'>", file=file)

    data = model.boards[position].data[:]

    board = ""
    for j, row in enumerate(reversed(data)):
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
        board += "\n"

    print(board, file=file)

    print("</div></body></html>", file=file)

    file.close()
