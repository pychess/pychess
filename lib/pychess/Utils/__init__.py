from pychess.Utils.lutils.ldata import MATE_VALUE


def prettyPrintScore(s, depth):
    """The score parameter is an eval value form White point of view"""

    if s is None:
        return "?"

    if s == 0:
        return "0.00/%s" % depth

    if s > 0:
        pp = "+"
    else:
        pp = "-"
        s = -s

    if depth:
        depth = "/" + depth
    else:
        depth = ""

    if abs(s) == MATE_VALUE:
        return "%s#%s" % (pp, MATE_VALUE)
    else:
        return "%s%0.2f%s" % (pp, s / 100.0, depth)


def createStoryTextAppEvent(text):
    try:
        import storytext
        storytext.applicationEvent(text)
    except ImportError:
        pass
