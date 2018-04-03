import sys
from collections import namedtuple


# Constants
PYTHONBIN = sys.executable.split("/")[-1]


# List of known interpreters
VM = namedtuple('VM', 'name, ext, args')
VM_LIST = [
    VM("node", ".js", None),
    VM("java", ".jar", ["-jar"]),
    VM(PYTHONBIN, ".py", ["-u"])
]


# List of engines sorted by descending length of name
# ELO from http://www.computerchess.org.uk/ccrl/404/
ENGINES = namedtuple('ENGINES', 'name, protocol, country, elo, depthDependent')
ENGINES_LIST = [
    ENGINES("toledo-uci", "uci", "mx", "1212", True),
    ENGINES("gnuchessu", "uci", "us", "2808", False),
    ENGINES("stockfish", "uci", "no", "3562", False),
    ENGINES("amundsen", "xboard", "sw", "", False),
    ENGINES("andscacs", "uci", "ad", "3318", False),
    ENGINES("anticrux", "uci", "fr", "", False),
    ENGINES("boochess", "xboard1", "de", "", False),
    ENGINES("fairymax", "xboard", "nl", "", False),
    ENGINES("glaurung", "uci", "no", "2802", False),
    ENGINES("gnuchess", "xboard", "us", "2808", False),
    ENGINES("hoichess", "xboard", "de", "1788", False),
    ENGINES("shredder", "uci", "de", "3328", False),
    ENGINES("houdini", "uci", "be", "3536", False),
    ENGINES("phalanx", "xboard1", "cz", "2653", False),
    ENGINES("pychess", "xboard", "dk", "", True),
    ENGINES("sjaakii", "xboard", "nl", "2194", False),
    ENGINES("crafty", "xboard", "us", "3060", False),
    ENGINES("diablo", "uci", "us", "2385", False),
    ENGINES("hiarcs", "uci", "gb", "3110", False),
    ENGINES("togaii", "uci", "de", "2933", False),
    ENGINES("toledo", "xboard", "mx", "1212", True),
    ENGINES("faile", "xboard1", "ca", "1974", False),
    ENGINES("fruit", "uci", "fr", "", False),
    ENGINES("rybka", "uci", "cz", "3208", False),
    ENGINES("sjeng", "xboard", "be", "2941", False),
    ENGINES("toga2", "uci", "de", "2933", False),
    ENGINES("gull", "uci", "ru", "3264", False)
]

# TODO List of engines to be extended
