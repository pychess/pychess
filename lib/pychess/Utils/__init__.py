from pychess.Utils.lutils.ldata import MATE_VALUE

def prettyPrintScore(s):
    if s is None: return "?"
    if s == 0: return "0.00"
    if s > 0:
       pp = "+"
    else:
        pp = "-"
        s = -s
    
    if abs(s) == MATE_VALUE:
        return pp + "#%s" % MATE_VALUE
    else:
        return pp + "%0.2f" % (s / 100.0)
