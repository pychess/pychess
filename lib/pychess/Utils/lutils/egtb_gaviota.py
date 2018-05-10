import os
import re
from ctypes import byref, c_byte, c_char_p, c_int, c_uint, c_ulong, c_size_t, c_double, Structure,\
    CDLL, CFUNCTYPE, POINTER

from .bitboard import firstBit, clearBit
from .lmovegen import genAllMoves, genCheckEvasions
from pychess.Utils.const import WHITE, BLACK, DRAW, WHITEWON, BLACKWON
from pychess.System import conf
from pychess.System.prefix import getDataPrefix
from pychess.System.Log import log


class TbStats(Structure):
    _fields_ = [
        ('wdl_easy_hits', c_ulong * 2),
        ('wdl_hard_prob', c_ulong * 2),
        ('wdl_soft_prob', c_ulong * 2),
        ('wdl_cachesize', c_size_t),
        ('wdl_occupancy', c_double),
        ('dtm_easy_hits', c_ulong * 2),
        ('dtm_hard_prob', c_ulong * 2),
        ('dtm_soft_prob', c_ulong * 2),
        ('dtm_cachesize', c_size_t),
        ('dtm_occupancy', c_double),
        ('total_hits', c_ulong * 2),
        ('memory_hits', c_ulong * 2),
        ('drive_hits', c_ulong * 2),
        ('drive_miss', c_ulong * 2),
        ('bytes_read', c_ulong * 2),
        ('files_opened', c_ulong),
        ('memory_efficiency', c_double),
    ]


class EgtbGaviota:
    def __init__(self):
        self.libgtb = None
        self.initialized = False

        # Get a list of files in the tablebase folder.
        configuredTbPath = conf.get("egtb_path")
        tbPath = configuredTbPath or getDataPrefix()
        try:
            tbPathContents = os.listdir(tbPath)
        except OSError as e:
            if configuredTbPath:
                log.warning("Unable to open Gaviota TB folder: %s" % repr(e))
            return

        # Find files named *.gtb.cp# and pick the most common "#".
        # (This is the compression scheme; the library currently only uses one at a time.)
        schemeCount = [0] * 10
        for filename in tbPathContents:
            match = re.search("\.gtb\.cp(\d)$", filename)
            if match:
                schemeCount[int(match.group(1))] += 1
        compressionScheme = max(zip(schemeCount, range(10)))
        if compressionScheme[0] == 0:
            if configuredTbPath:
                log.warning("Could not find any Gaviota TB files in %s" %
                            configuredTbPath)
            return
        compressionScheme = compressionScheme[1]

        # Locate and load the library.
        if not self._loadLibrary():
            return
        self._setupFunctionPrototypes()

        self.pathList = self.tbpaths_init()
        self.pathList = self.tbpaths_add(self.pathList, tbPath.encode())
        initInfo = self.tb_init(True, compressionScheme, self.pathList)
        self.initialized = (self.tb_is_initialized() != 0)
        if not self.initialized:
            log.warning(initInfo or
                        "Failed to initialize Gaviota EGTB library")
            self.pathList = self.tbpaths_done(self.pathList)
            return
        elif initInfo:
            log.info(initInfo)

        # TODO: Set up a WDL cache area once the engine can use it.
        self.initialized &= self.tbcache_init(4 * 1024 * 1024, 0)
        if not self.initialized:
            log.warning("Failed to initialize Gaviota EGTB cache")
            self.tb_done()
            self.pathList = self.tbpaths_done(self.pathList)
            return

        self.availability = self.tb_availability()

    def _del(self):
        if self.initialized:
            self.tb_done()
            self.pathList = self.tbpaths_done(self.pathList)

    def supports(self, size):
        return self.initialized and (
            sum(size) <= 2 or (self.availability & (3 << (2 * sum(size) - 6))) != 0)

    def scoreAllMoves(self, board):
        result, depth = self.scoreGame(board, False, False)
        if result is None:
            return []

        scores = []
        gen = board.isChecked() and genCheckEvasions or genAllMoves
        for move in gen(board):
            board.applyMove(move)
            if not board.opIsChecked():
                result, depth = self.scoreGame(board, False, False)
                if result is None:
                    log.warning(
                        "An EGTB file does not have all its dependencies")
                    board.popMove()
                    return []
                scores.append((move, result, depth))
            board.popMove()

        def mateScore(mrd):
            if mrd[1] == DRAW:
                return 0
            absScore = 32767 - mrd[2]
            if (board.color == WHITE) ^ (mrd[1] == WHITEWON):
                return absScore
            return -absScore

        scores.sort(key=mateScore)
        return scores

    def scoreGame(self, board, omitDepth, probeSoft):
        stm = board.color
        epsq = board.enpassant or 64  # 64 is tb_NOSQUARE
        castles = (board.castling >> 2 & 3) | (board.castling << 2 & 12)
        tbinfo = c_uint()
        depth = c_uint()

        SqArray = c_uint * 65
        PcArray = c_byte * 65
        pc, sq = [], []
        for color in (WHITE, BLACK):
            sq.append(SqArray())
            pc.append(PcArray())
            i = 0
            bb = board.friends[color]
            while bb:
                b = firstBit(bb)
                bb = clearBit(bb, b)
                sq[-1][i] = b
                pc[-1][i] = board.arBoard[b]
                i += 1
            sq[-1][i] = 64  # tb_NOSQUARE, terminates the list
            pc[-1][i] = 0  # tb_NOPIECE,  terminates the list

        if omitDepth and probeSoft:
            ok = self.tb_probe_WDL_soft(stm, epsq, castles, sq[WHITE],
                                        sq[BLACK], pc[WHITE], pc[BLACK],
                                        byref(tbinfo))
        elif omitDepth and not probeSoft:
            ok = self.tb_probe_WDL_hard(stm, epsq, castles, sq[WHITE],
                                        sq[BLACK], pc[WHITE], pc[BLACK],
                                        byref(tbinfo))
        elif not omitDepth and probeSoft:
            ok = self.tb_probe_soft(stm, epsq, castles, sq[WHITE], sq[BLACK],
                                    pc[WHITE], pc[BLACK], byref(tbinfo),
                                    byref(depth))
        elif not omitDepth and not probeSoft:
            ok = self.tb_probe_hard(stm, epsq, castles, sq[WHITE], sq[BLACK],
                                    pc[WHITE], pc[BLACK], byref(tbinfo),
                                    byref(depth))

        resultMap = [DRAW, WHITEWON, BLACKWON]
        if not ok or not 0 <= tbinfo.value <= 2:
            return None, None
        result = resultMap[tbinfo.value]
        if omitDepth or result == DRAW:
            depth = None
        else:
            depth = depth.value
        return result, depth

    def _loadLibrary(self):
        libName = "libgaviotatb.so.1.0.1"
        try:
            self.libgtb = CDLL(libName)
        except OSError:
            log.warning("Failed to load Gaviota EGTB library %s" % libName)
            return None
        return self.libgtb

    # Prototypes from gtb-probe.h follow.

    def _setupFunctionPrototypes(self):
        def proto(name, returnType, *args):
            argTypes = map(lambda x: x[0], args)
            argNames = map(lambda x: x[1], args)
            funcType = CFUNCTYPE(returnType, *argTypes)
            paramFlags = tuple(zip([1] * len(args), argNames))
            setattr(self, name, funcType((name, self.libgtb), paramFlags))

        paths_t = POINTER(c_char_p)
        uip = POINTER(c_uint)
        ucp = POINTER(c_byte)

        proto("tb_init", c_char_p, (c_int, "verbosity"),
              (c_int, "compression_scheme"), (paths_t, "paths"))
        proto("tb_restart", c_char_p, (c_int, "verbosity"),
              (c_int, "compression_scheme"), (paths_t, "paths"))
        proto("tb_done", None)
        proto("tb_probe_hard", c_int, (c_uint, "stm"), (c_uint, "epsq"),
              (c_uint, "castles"), (uip, "wSQ"), (uip, "bSQ"), (ucp, "wPC"),
              (ucp, "bPC"), (uip, "tbinfo"), (uip, "plies"))
        proto("tb_probe_soft", c_int, (c_uint, "stm"), (c_uint, "epsq"),
              (c_uint, "castles"), (uip, "wSQ"), (uip, "bSQ"), (ucp, "wPC"),
              (ucp, "bPC"), (uip, "tbinfo"), (uip, "plies"))
        proto("tb_probe_WDL_hard", c_int, (c_uint, "stm"), (c_uint, "epsq"),
              (c_uint, "castles"), (uip, "wSQ"), (uip, "bSQ"), (ucp, "wPC"),
              (ucp, "bPC"), (uip, "tbinfo"))
        proto("tb_probe_WDL_soft", c_int, (c_uint, "stm"), (c_uint, "epsq"),
              (c_uint, "castles"), (uip, "wSQ"), (uip, "bSQ"), (ucp, "wPC"),
              (ucp, "bPC"), (uip, "tbinfo"))
        proto("tb_is_initialized", c_int)
        proto("tb_availability", c_uint)
        proto("tb_indexmemory", c_size_t)
        proto("tbcache_init", c_int, (c_size_t, "cache_mem"),
              (c_int, "wdl_fraction"))
        proto("tbcache_restart", c_int, (c_size_t, "cache_mem"),
              (c_int, "wdl_fraction"))
        proto("tbcache_done", None)
        proto("tbcache_is_on", c_int)
        proto("tbcache_flush", None)
        proto("tbstats_reset", None)
        proto("tbstats_get", None, (POINTER(TbStats), "stats"))
        proto("tbpaths_init", paths_t)
        proto("tbpaths_add", paths_t, (paths_t, "ps"), (c_char_p, "newpath"))
        proto("tbpaths_done", paths_t, (paths_t, "ps"))
        proto("tbpaths_getmain", c_char_p)
