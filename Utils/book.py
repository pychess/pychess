from time import time

from Utils.History import History
from Utils.Move import movePool

MAXMOVES = 14
PROFILE = False
FILESMAX = 0

def stripBrackets (string):
    brackets = 0
    end = 0
    result = ""
    for i, c in enumerate(string):
        if c == '(':
            if brackets == 0:
                result += string[end:i]
            brackets += 1
        elif c == ')':
            brackets -= 1
            if brackets == 0:
                end = i+1
    result += string[end:-1]
    return result

import re
tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.+?)\"\]")
movre = re.compile(r"([a-hxOKQRBN0-8+#=-]{2,7})\s")
comre = re.compile(r"(?:\{.*?\})|(?:;.*?[\n\r])|(?:\$[0-9]+)", re.DOTALL)
resultDic = {"1-0":0, "1/2-1/2":1, "0-1":2}
def load (file):
    files = []
    inTags = False
    for line in file:
        if FILESMAX and len(files) > FILESMAX: break
    
        line = line.lstrip()
        if not line: continue
        elif line.startswith("%"): continue
        
        if line.startswith("["):
            if not inTags:
                files.append(["",""])
                inTags = True
            files[-1][0] += line
        
        else:
            inTags = False
            files[-1][1] += line
    
    history = History(False)
    max = str(len(files))
    start = time()
    for i, myFile in enumerate(files):
        number = str(i).rjust(len(max))
        procent = ("%.1f%%" % (i/float(len(files))*100)).rjust(4)
        if i == 0: estimation = "etr: N/A"
        else:
            s = round((time()-start)/i*(len(files)-i))
            estimation = ("etr: %d:%02d" % (s / 60, s % 60)).rjust(5)
        print number, "/", max, "-", procent, "-", estimation
        try:
            #These tags won't be used for a lot atm.
            tags = dict(tagre.findall(myFile[0]))
            if not tags["Result"] in ("1/2-1/2", "1-0", "0-1"):
                continue
            moves = comre.sub("", myFile[1])
            moves = stripBrackets(moves)
            moves = movre.findall(moves+" ")
            if moves[-1] in ("*", "1/2-1/2", "1-0", "0-1"):
                del moves[-1]
        except:
            # Could not parse game
            continue
        
        mcatch = []
        if MAXMOVES: moves = moves[:MAXMOVES]
        for move in moves:
            try:
                m = movePool.pop(history,move)
            except:
                continue
            epd = fen(history)
            res = resultDic[tags["Result"]]
            if epd.endswith("b"): res = 2-res
            history.add(m, False)
            yield epd, m.algNotat(history), res
            mcatch.append(m)
        history.reset(False)
        for move in mcatch:
            movePool.add(move)
        del mcatch[:]
            
def fen (history, no=-1):
    r = ""

    pieces = history[no].data
    sign = lambda p: p.color == "white" and p.sign.upper() or p.sign
    for i in range(len(pieces))[::-1]:
        row = pieces[i]
        empty = 0
        for j in range(len(row)):
            piece = row[j]
            if piece == None:
                empty += 1
                if j == 7:
                    r += str(empty)
            else:
                if empty > 0:
                    r += str(empty)
                    empty = 0
                r += sign(piece)
        if i != 0:
            r += "/"
    r += " "
    
    if no < 0: l = len(history)+no+history.curColModi
    else: l = no
    r += l % 2 == 0 and "w" or "b"
    
    return r

from System.ThreadPool import pool
from threading import Condition
cond = Condition()

import sqlite, sys, os
path = os.path.join(os.path.split(__file__)[0], "open.db")
def do(none):
    cond.acquire()
    global con
    con = sqlite.connect(path)
    con.db.execute("PRAGMA default_synchronous=OFF")
    con.db.execute("PRAGMA cache_size=10000")
    cond.release()
pool.start(do,None)

sql1 = "select * from openings WHERE fen = '%s' AND move = '%s'"
sql2 = "UPDATE openings SET %s = %s+1 WHERE fen = '%s' AND move = '%s'"
sql3 = "INSERT INTO openings (fen,move,%s) VALUES ('%s','%s',1)"

def toDb (fenstr, move, res):
    cond.acquire()
    if con.db.execute(sql1 % (fenstr, move)).rowcount:
        con.db.execute(sql2 % (res, res, fenstr, move))
    else: con.db.execute(sql3 % (res, fenstr, move))
    cond.release()
    
def do ():
    con.db.execute("drop table if exists openings")
    con.db.execute("create table openings( fen varchar(73), move varchar(7), \
                wins int DEFAULT 0, draws int DEFAULT 0, loses int DEFAULT 0)")
    
    resd = ["wins","draws","loses"]
    
    for fenstr, move, score in load(open(sys.argv[1])):
        pool.start(toDb,fenstr, move, resd[score])
    
    cond.acquire()
    for fen, move, w, l, d in con.db.execute("select * from openings").row_list:
        print fen.ljust(65), move.ljust(7), w, "\t", l, "\t", d
    cond.release()
    con.close()

if __name__ == "__main__":
    if not PROFILE:
        do()
    else:
        import profile
        profile.run("do()", "/tmp/pychessprofile")
        from pstats import Stats
        s = Stats("/tmp/pychessprofile")
        s.sort_stats("time")

def getOpenings (history, no=-1):
    cond.acquire()
    r = con.db.execute("select move,wins,draws,loses from openings \
        where fen = '%s'" % fen(history, no)).row_list
    cond.release()
    return r
