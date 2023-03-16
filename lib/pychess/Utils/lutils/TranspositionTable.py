from ctypes import create_string_buffer, memset
from struct import Struct

from pychess.Utils.const import hashfALPHA, hashfBETA, hashfEXACT, hashfBAD
from pychess.Utils.lutils.ldata import MATE_VALUE, MAXPLY

# Store hash entries in buckets of 4. An entry consists of:
# key         32 bits derived from the board hash
# search_id   counter used to determine entry's age
# hashf       bound type (one of the hashf* constants)
# depth       search depth
# score       search score
# move        best move (or cutoff move)
entryType = Struct("=I B B H h H")


class TranspositionTable:
    def __init__(self, maxSize):
        assert maxSize > 0
        self.buckets = maxSize // (4 * entryType.size)
        self.data = create_string_buffer(self.buckets * 4 * entryType.size)
        self.search_id = 0

        self.killer1 = [-1] * 80
        self.killer2 = [-1] * 80
        self.hashmove = [-1] * 80

        self.butterfly = [0] * (64 * 64)

    def clear(self):
        memset(self.data, 0, self.buckets * 4 * entryType.size)
        self.killer1 = [-1] * 80
        self.killer2 = [-1] * 80
        self.hashmove = [-1] * 80
        self.butterfly = [0] * (64 * 64)

    def newSearch(self):
        self.search_id = (self.search_id + 1) & 0xFF
        # TODO: consider clearing butterfly table

    def probe(self, board, depth, alpha, beta):
        baseIndex = (board.hash % self.buckets) * 4
        key = (board.hash // self.buckets) & 0xFFFFFFFF
        for i in range(baseIndex, baseIndex + 4):
            tkey, search_id, hashf, tdepth, score, move = entryType.unpack_from(
                self.data, i * entryType.size
            )
            if tkey == key:
                # Mate score bounds are guaranteed to be accurate at any depth.
                if tdepth < depth and abs(score) < MATE_VALUE - MAXPLY:
                    return move, score, hashfBAD
                if hashf == hashfEXACT:
                    return move, score, hashf
                if hashf == hashfALPHA and score <= alpha:
                    return move, alpha, hashf
                if hashf == hashfBETA and score >= beta:
                    return move, beta, hashf

    def record(self, board, move, score, hashf, depth):
        baseIndex = (board.hash % self.buckets) * 4
        key = (board.hash // self.buckets) & 0xFFFFFFFF
        # We always overwrite *something*: an empty slot, this position's last entry, or else the least relevant.
        staleIndex = baseIndex
        staleRelevance = 0xFFFF
        for i in range(baseIndex, baseIndex + 4):
            tkey, search_id, thashf, tdepth, tscore, tmove = entryType.unpack_from(
                self.data, i * entryType.size
            )
            if tkey == 0 or tkey == key:
                staleIndex = i
                break
            relevance = (
                (0x8000 if search_id != self.search_id and thashf == hashfEXACT else 0)
                + (0x4000 if ((self.search_id - search_id) & 0xFF) > 1 else 0)
                + tdepth
            )
            if relevance < staleRelevance:
                staleIndex = i
                staleRelevance = relevance
        entryType.pack_into(
            self.data,
            staleIndex * entryType.size,
            key,
            self.search_id,
            hashf,
            depth,
            score,
            move,
        )

    def addKiller(self, ply, move):
        if self.killer1[ply] == -1:
            self.killer1[ply] = move
        elif move != self.killer1[ply]:
            self.killer2[ply] = move

    def isKiller(self, ply, move):
        if self.killer1[ply] == move:
            return 10
        elif self.killer2[ply] == move:
            return 8
        if ply >= 2:
            if self.killer1[ply - 2] == move:
                return 6
            elif self.killer2[ply - 2] == move:
                return 4
        return 0

    def setHashMove(self, ply, move):
        self.hashmove[ply] = move

    def isHashMove(self, ply, move):
        return self.hashmove[ply] == move

    def addButterfly(self, move, depth):
        self.butterfly[move & 0xFFF] += 1 << depth

    def getButterfly(self, move):
        return self.butterfly[move & 0xFFF]
