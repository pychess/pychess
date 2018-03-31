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
ENGINES = namedtuple('ENGINES', 'name, protocol, country, elo')
ENGINES_LIST = [
    ENGINES("toledo-uci", "uci", "mx", "1212"),
    ENGINES("gnuchessu", "uci", "us", "2808"),
    ENGINES("stockfish", "uci", "no", "3562"),
    ENGINES("amundsen", "xboard", "sw", ""),
    ENGINES("andscacs", "uci", "ad", "3318"),
    ENGINES("anticrux", "uci", "fr", ""),
    ENGINES("boochess", "xboard1", "de", ""),
    ENGINES("fairymax", "xboard", "nl", ""),
    ENGINES("glaurung", "uci", "no", "2802"),
    ENGINES("gnuchess", "xboard", "us", "2808"),
    ENGINES("hoichess", "xboard", "de", "1788"),
    ENGINES("shredder", "uci", "de", "3328"),
    ENGINES("houdini", "uci", "be", "3536"),
    ENGINES("phalanx", "xboard1", "cz", "2653"),
    ENGINES("pychess", "xboard", "dk", ""),
    ENGINES("sjaakii", "xboard", "nl", "2194"),
    ENGINES("crafty", "xboard", "us", "3060"),
    ENGINES("diablo", "uci", "us", "2385"),
    ENGINES("hiarcs", "uci", "gb", "3110"),
    ENGINES("togaii", "uci", "de", "2933"),
    ENGINES("toledo", "xboard", "mx", "1212"),
    ENGINES("faile", "xboard1", "ca", "1974"),
    ENGINES("fruit", "uci", "fr", ""),
    ENGINES("rybka", "uci", "cz", "3208"),
    ENGINES("sjeng", "xboard", "be", "2941"),
    ENGINES("toga2", "uci", "de", "2933"),
    ENGINES("gull", "uci", "ru", "3264")
]

# TODO List of engines to be extended
# TODO Copy ELO to new local game
