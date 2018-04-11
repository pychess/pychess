import platform
import sys
from collections import namedtuple


# Constants
PYTHONBIN = sys.executable.split("/")[-1]

BITNESS = "64" if platform.machine().endswith('64') else "32"

if sys.platform == "win32":
    stockfish_name = "stockfish_9_x%s.exe" % BITNESS
    sjaakii_name = "sjaakii_win%s_ms.exe" % BITNESS
else:
    stockfish_name = "stockfish"
    sjaakii_name = "jaakii"

# List of known interpreters
VM = namedtuple('VM', 'name, ext, args')
VM_LIST = [
    VM("node", ".js", None),
    VM("java", ".jar", ["-jar"]),
    VM(PYTHONBIN, ".py", ["-u"])
]


# List of engines sorted by descending length of name
ENGINES = namedtuple('ENGINES', 'name, protocol, country, depthDependent')
ENGINES_LIST = [
    ENGINES("pychess-engine", "xboard", "dk", True),
    ENGINES("PyChess.py", "xboard", "dk", True),
    ENGINES("toledo-uci", "uci", "mx", True),
    ENGINES("gnuchessu", "uci", "us", False),
    ENGINES(stockfish_name, "uci", "no", False),
    ENGINES("amundsen", "xboard", "sw", False),
    ENGINES("andscacs", "uci", "ad", False),
    ENGINES("anticrux", "uci", "fr", True),
    ENGINES("boochess", "xboard1", "de", False),
    ENGINES("fairymax", "xboard", "nl", False),
    ENGINES("glaurung", "uci", "no", False),
    ENGINES("gnuchess", "xboard", "us", False),
    ENGINES("hoichess", "xboard", "de", False),
    ENGINES("shredder", "uci", "de", False),
    ENGINES("Houdini.exe", "uci", "be", False),
    ENGINES("phalanx", "xboard1", "cz", False),
    ENGINES(sjaakii_name, "xboard", "nl", False),
    ENGINES("crafty", "xboard", "us", False),
    ENGINES("diablo", "uci", "us", False),
    ENGINES("hiarcs", "uci", "gb", False),
    ENGINES("togaii", "uci", "de", False),
    ENGINES("toledo", "xboard", "mx", True),
    ENGINES("faile", "xboard1", "ca", False),
    ENGINES("fruit", "uci", "fr", False),
    ENGINES("Rybka.exe", "uci", "cz", False),
    ENGINES("sjeng", "xboard", "be", False),
    ENGINES("toga2", "uci", "de", False),
    ENGINES("gull", "uci", "ru", False)
]

# TODO List of engines to be extended
