import os
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
    sjaakii_name = "sjaakii"


# List of known interpreters
VM = namedtuple('VM', 'name, ext, args')
VM_LIST = [
    VM("node", ".js", None),
    VM("java", ".jar", ["-jar"]),
    VM(PYTHONBIN, ".py", ["-u"])
]

# Needed by shutil.which() on Windows to find .py engines
if sys.platform == "win32":
    for vm in VM_LIST:
        if vm.ext.upper() not in os.getenv("PATHEXT"):
            os.environ["PATHEXT"] += ";%s" % vm.ext.upper()

# List of engines later sorted by descending length of name
ENGINE = namedtuple('ENGINE', 'name, protocol, country, elo, depthDependent')
ENGINES_LIST = [
    # -- Full names for internal processing (TODO)
    ENGINE("PyChess.py", "xboard", "dk", 0, True),
    ENGINE("pychess-engine", "xboard", "dk", 0, True),
    ENGINE(stockfish_name, "uci", "no", 3559, False),
    ENGINE(sjaakii_name, "xboard", "nl", 2193, False),
    ENGINE("Houdini.exe", "uci", "be", 3534, False),
    ENGINE("Rybka.exe", "uci", "cz", 3207, False),

    # -- Engines from CCRL 40/4
    ENGINE("stockfish", "uci", "no", 3559, False),
    ENGINE("houdini", "uci", "be", 3534, False),
    ENGINE("komodo", "uci", "us", 3513, False),
    # fire in mesa-demos https://www.archlinux.org/packages/extra/x86_64/mesa-demos/files/
    # ENGINE("fire", "uci", "us", 3356, False),
    ENGINE("fizbo", "uci", "us", 3351, False),
    ENGINE("shredder", "uci", "de", 3327, False),
    ENGINE("andscacs", "uci", "ad", 3318, False),
    ENGINE("ethereal", "uci", "us", 3299, False),
    ENGINE("gull", "uci", "ru", 3263, False),
    ENGINE("booot", "uci", "ua", 3260, False),  # Formerly XB
    ENGINE("equinox", "uci", "it", 3254, False),
    ENGINE("chiron", "uci", "it", 3242, False),  # Allows XB
    ENGINE("critter", "uci", "sk", 3235, False),
    ENGINE("hannibal", "uci", "us", 3233, False),
    ENGINE("fritz", "uci", "nl", 3231, False),
    ENGINE("nirvana", "uci", "us", 3229, False),
    ENGINE("texel", "xboard", "se", 3210, False),  # UCI is an option in the command line
    ENGINE("rybka", "uci", "cz", 3207, False),
    ENGINE("blackmamba", "uci", "it", 3200, False),
    ENGINE("laser", "uci", "us", 3193, False),
    # ivanhoe, robbolito, panchess, bouquet, elektro
    ENGINE("senpai", "uci", "fr", 3178, False),
    ENGINE("naum", "uci", "rs", 3156, False),
    ENGINE("arasan", "uci", "us", 3147, False),
    ENGINE("strelka", "uci", "ru", 3143, False),
    ENGINE("xiphos", "uci", "us", 3139, False),
    ENGINE("pedone", "uci", "it", 3137, False),
    ENGINE("protector", "uci", "de", 3128, False),
    ENGINE("vajolet", "uci", "it", 3128, False),
    ENGINE("nemorino", "uci", "de", 3122, False),  # Allows XB
    ENGINE("defenchess", "uci", "tr", 3118, False),
    ENGINE("hiarcs", "uci", "gb", 3109, False),
    # ice @de (name too short)
    ENGINE("wasp", "uci", "us", 3077, False),
    ENGINE("cheng", "uci", "cz", 3071, False),
    ENGINE("crafty", "xboard", "us", 3058, False),
    ENGINE("bobcat", "uci", "nl", 3056, False),
    ENGINE("smarthink", "uci", "ru", 3053, False),  # Allows XB
    ENGINE("rodent", "uci", "pl", 3052, False),
    ENGINE("chess22k", "uci", "nl", 3043, False),
    ENGINE("spike", "uci", "de", 3038, False),  # Allows XB
    ENGINE("alfil", "uci", "es", 3031, False),
    ENGINE("spark", "uci", "nl", 3028, False),
    ENGINE("junior", "uci", "il", 3027, False),
    ENGINE("hakkapeliitta", "uci", "fi", 3016, False),
    ENGINE("exchess", "xboard", "us", 3012, False),
    ENGINE("demolito", "uci", "fr", 3005, False),
    ENGINE("tucano", "xboard", "br", 2999, False),
    ENGINE("scorpio", "xboard", "et", 2996, False),
    ENGINE("chessbrain", "uci", "de", 2982, False),  # Allows XB
    ENGINE("gaviota", "xboard", "ar", 2975, False),
    ENGINE("zappa", "uci", "us", 2971, False),
    ENGINE("togaii", "uci", "de", 2967, False),
    ENGINE("toga2", "uci", "de", 2967, False),
    ENGINE("onno", "uci", "de", 2955, False),
    ENGINE("thinker", "uci", "ca", 2951, False),
    ENGINE("amoeba", "uci", "fr", 2949, False),
    ENGINE("deuterium", "uci", "ph", 2943, False),
    ENGINE("sjeng", "xboard", "be", 2940, False),
    ENGINE("disasterarea", "uci", "de", 2932, False),
    ENGINE("atlas", "uci", "es", 2927, False),
    ENGINE("minko", "uci", "sv", 2923, False),
    ENGINE("discocheck", "uci", "fr", 2914, False),
    ENGINE("bright", "uci", "nl", 2910, False),
    ENGINE("daydreamer", "uci", "us", 2903, False),
    ENGINE("quazar", "uci", "ru", 2899, False),
    ENGINE("zurichess", "uci", "ro", 2894, False),
    ENGINE("loop", "uci", "de", 2881, False),
    ENGINE("murka", "uci", "by", 2881, False),
    ENGINE("baron", "xboard", "nl", 2880, False),
    ENGINE("pirarucu", "uci", "br", 2870, False),
    ENGINE("dirty", "xboard", "es", 2867, False),
    ENGINE("nemo", "uci", "de", 2857, False),
    ENGINE("tornado", "uci", "de", 2851, False),
    ENGINE("bugchess", "xboard", "fr", 2842, False),
    ENGINE("octochess", "uci", "de", 2813, False),  # Allows XB
    ENGINE("gnuchess", "xboard", "us", 2807, False),
    ENGINE("godel", "uci", "es", 2807, False),  # May allow XB
    ENGINE("rhetoric", "uci", "es", 2804, False),
    ENGINE("ruydos", "uci", "es", 2804, False),
    ENGINE("rofchade", "uci", "nl", 2791, False),
    ENGINE("marvin", "uci", "se", 2785, False),  # Allows XB
    ENGINE("ktulu", "uci", "ir", 2782, False),  # Allows XB
    ENGINE("prodeo", "uci", "nl", 2770, False),  # Allows XB
    ENGINE("twisted-logic", "uci", "ph", 2770, False),
    ENGINE("frenzee", "xboard", "dk", 2768, False),
    ENGINE("gogobello", "uci", "it", 2767, False),
    ENGINE("pawny", "uci", "bg", 2767, False),
    # bison - YACC-compatible parser generator
    # ENGINE("bison", "uci", "ru", 2758, False),
    ENGINE("chessmaster", "xboard", "nl", 2757, False),
    ENGINE("karballo", "uci", "es", 2756, False),
    ENGINE("jonny", "uci", "de", 2755, False),  # Formerly XB
    ENGINE("devel", "uci", "no", 2740, False),
    ENGINE("chronos", "uci", "ar", 2737, False),
    ENGINE("shield", "uci", "it", 2733, False),
    # cheese - tool to take pictures and videos from your webcam
    # ENGINE("cheese", "uci", "fr", 2730, False),  # Allows XB
    ENGINE("counter", "uci", "ru", 2715, False),
    ENGINE("tiger", "uci", "gp", 2713, False),
    ENGINE("greko", "uci", "ru", 2713, False),
    ENGINE("redqueen", "uci", "br", 2689, False),
    ENGINE("arminius", "xboard", "de", 2686, False),
    ENGINE("delfi", "uci", "it", 2681, False),  # Allows XB
    ENGINE("gandalf", "uci", "dk", 2675, False),  # Allows XB
    ENGINE("pharaon", "uci", "fr", 2675, False),  # Allows XB
    ENGINE("djinn", "xboard", "us", 2673, False),
    ENGINE("alaric", "uci", "se", 2664, False),  # Allows XB
    ENGINE("ece-x3", "uci", "it", 2656, False),
    ENGINE("nebula", "uci", "rs", 2655, False),
    ENGINE("naraku", "uci", "it", 2652, False),
    ENGINE("phalanx", "xboard1", "cz", 2652, False),
    ENGINE("rubichess", "uci", "de", 2652, False),
    ENGINE("donna", "uci", "us", 2650, False),
    ENGINE("colossus", "uci", "gb", 2641, False),
    ENGINE("cyrano", "uci", "no", 2641, False),
    ENGINE("sjakk", "uci", "no", 2639, False),
    ENGINE("et_chess", "xboard2", "fr", 2634, False),
    ENGINE("rodin", "xboard", "es", 2632, False),
    ENGINE("wyldchess", "uci", "in", 2632, False),  # Allows XB
    ENGINE("wildcat", "uci", "by", 2624, False),  # Formerly XB
    ENGINE("movei", "uci", "il", 2623, False),  # Allows XB
    ENGINE("philou", "uci", "fr", 2619, False),
    ENGINE("rotor", "uci", "nl", 2618, False),
    ENGINE("zarkov", "xboard", "us", 2618, False),
    ENGINE("tomitank", "uci", "hu", 2617, False),
    ENGINE("sloppy", "xboard", "fi", 2616, False),
    ENGINE("danasah", "uci", "es", 2615, False),  # Allows XB
    ENGINE("schess", "uci", "us", 2615, False),  # Allows XB
    ENGINE("sblitz", "uci", "us", 2615, False),  # Allows XB
    ENGINE("leela", "uci", "us", 2610, False),
    ENGINE("delocto", "uci", "at", 2609, False),
    ENGINE("garbochess", "uci", "us", 2609, False),
    ENGINE("glass", "uci", "pl", 2609, False),
    ENGINE("ruffian", "uci", "se", 2609, False),
    ENGINE("noragrace", "xboard", "us", 2607, False),
    ENGINE("jellyfish", "uci", "unknown", 2605, False),  # Allows XB
    ENGINE("winter", "uci", "ch", 2605, False),
    ENGINE("amyan", "uci", "cl", 2604, False),  # Allows XB
    ENGINE("monolith", "uci", "it", 2601, False),
    ENGINE("lemming", "xboard", "us", 2599, False),
    ENGINE("coiled", "uci", "es", 2593, False),
    # k2 @ru (name to short)
    # n2 @de (name to short)
    ENGINE("floyd", "uci", "nl", 2583, False),
    ENGINE("cuckoo", "xboard", "se", 2582, False),  # UCI is an option in the command line
    ENGINE("francesca", "xboard", "gb", 2581, False),
    ENGINE("muse", "xboard", "ch", 2581, False),  # May support UCI as well
    ENGINE("hamsters", "uci", "it", 2578, False),
    ENGINE("pseudo", "xboard", "cz", 2576, False),
    # sos @de (name too short)
    ENGINE("maverick", "uci", "gb", 2567, False),
    ENGINE("aristarch", "uci", "de", 2566, False),
    ENGINE("petir", "xboard", "id", 2566, False),
    ENGINE("capivara", "uci", "br", 2565, False),
    ENGINE("nanoszachy", "xboard", "pl", 2558, False),
    ENGINE("brutus", "xboard", "nl", 2554, False),
    ENGINE("ghost", "xboard", "de", 2546, False),
    ENGINE("anaconda", "uci", "de", 2545, False),
    ENGINE("betsabe", "xboard", "es", 2543, False),
    ENGINE("rebel", "uci", "nl", 2543, False),
    ENGINE("dorky", "xboard", "us", 2542, False),
    ENGINE("hermann", "uci", "de", 2540, False),
    ENGINE("anmon", "uci", "fr", 2538, False),
    ENGINE("ufim", "uci", "ru", 2538, False),  # Formerly XB
    ENGINE("pupsi", "uci", "se", 2536, False),
    ENGINE("fridolin", "uci", "de", 2535, False),  # Allows XB
    ENGINE("jikchess", "xboard2", "fi", 2524, False),
    ENGINE("pepito", "xboard", "es", 2520, False),
    ENGINE("schooner", "xboard", "ca", 2518, False),
    ENGINE("orion", "uci", "fr", 2511, False),
    ENGINE("danchess", "xboard", "et", 2508, False),
    ENGINE("greenlight", "xboard", "gb", 2507, False),
    ENGINE("goliath", "uci", "de", 2505, False),
    ENGINE("trace", "xboard", "au", 2503, False),
    ENGINE("yace", "uci", "de", 2503, False),  # Allows XB
    ENGINE("cyberpagno", "xboard", "it", 2492, False),
    ENGINE("magnum", "uci", "ca", 2490, False),
    ENGINE("bruja", "xboard", "us", 2487, False),
    ENGINE("drosophila", "xboard", "se", 2486, False),
    ENGINE("bagatur", "uci", "bg", 2484, False),
    # tao @nl (name too short)
    ENGINE("delphil", "uci", "fr", 2481, False),
    ENGINE("mephisto", "uci", "gb", 2475, False),
    ENGINE("bbchess", "uci", "si", 2472, False),
    ENGINE("topple", "uci", "unknown", 2472, False),
    ENGINE("cerebro", "xboard", "it", 2471, False),
    ENGINE("gothmog", "uci", "no", 2471, False),  # Allows XB
    ENGINE("jumbo", "xboard", "de", 2470, False),
    ENGINE("kiwi", "xboard", "it", 2466, False),
    ENGINE("xpdnt", "xboard", "us", 2465, False),
    ENGINE("dimitri", "uci", "it", 2459, False),  # May allow XB
    ENGINE("anatoli", "xboard", "nl", 2457, False),
    ENGINE("bumblebee", "uci", "us", 2456, False),
    ENGINE("pikoszachy", "xboard", "pl", 2456, False),
    ENGINE("littlethought", "uci", "au", 2454, False),
    ENGINE("matacz", "xboard", "pl", 2447, False),
    ENGINE("soldat", "xboard", "it", 2443, False),
    ENGINE("lozza", "uci", "gb", 2440, False),
    ENGINE("spider", "xboard", "nl", 2439, False),
    ENGINE("madchess", "uci", "us", 2438, False),
    ENGINE("ares", "uci", "us", 2437, False),
    ENGINE("abrok", "uci", "de", 2434, False),  # Allows XB
    ENGINE("kingofkings", "uci", "ca", 2433, False),
    ENGINE("lambchop", "uci", "nz", 2432, False),  # Formerly XB
    ENGINE("gromit", "uci", "de", 2429, False),
    ENGINE("shallow", "uci", "unknown", 2427, False),  # Allows XB
    ENGINE("eeyore", "uci", "ru", 2426, False),  # Allows XB
    ENGINE("nejmet", "uci", "fr", 2425, False),  # Allows XB
    ENGINE("gaia", "uci", "fr", 2424, False),
    ENGINE("quark", "xboard", "de", 2422, False),
    ENGINE("caligula", "uci", "es", 2420, False),
    ENGINE("nemeton", "xboard", "nl", 2420, False),
    ENGINE("dragon", "xboard", "fr", 2419, False),
    ENGINE("hussar", "uci", "hu", 2419, False),
    ENGINE("snitch", "xboard", "de", 2419, False),
    ENGINE("romichess", "xboard", "us", 2418, False),
    ENGINE("olithink", "xboard", "de", 2415, False),
    ENGINE("typhoon", "xboard", "us", 2413, False),
    ENGINE("simplex", "uci", "es", 2411, False),
    ENGINE("giraffe", "xboard", "gb", 2410, False),
    ENGINE("ifrit", "uci", "ru", 2401, False),
    ENGINE("teki", "uci", "in", 2401, False),
    ENGINE("tjchess", "uci", "us", 2397, False),  # Allows XB
    ENGINE("bearded", "xboard", "pl", 2394, False),
    ENGINE("knightdreamer", "xboard", "se", 2394, False),
    ENGINE("postmodernist", "xboard", "gb", 2391, False),
    ENGINE("comet", "xboard", "de", 2388, False),
    ENGINE("capture", "xboard", "fr", 2386, False),
    ENGINE("diablo", "uci", "us", 2386, False),
    ENGINE("leila", "xboard", "it", 2386, False),
    # amy @de (name too short)
    ENGINE("galjoen", "uci", "be", 2384, False),  # Allows XB
    ENGINE("gosu", "xboard", "pl", 2381, False),
    ENGINE("myrddin", "xboard", "us", 2377, False),
    ENGINE("patzer", "xboard", "de", 2376, False),
    ENGINE("jazz", "xboard", "nl", 2374, False),
    ENGINE("cmcchess", "uci", "zh", 2373, False),
    ENGINE("bringer", "xboard", "de", 2373, False),
    ENGINE("terra", "uci", "se", 2367, False),
    ENGINE("crazybishop", "xboard", "fr", 2362, False),  # Named as tcb
    ENGINE("homer", "uci", "de", 2357, False),
    ENGINE("betsy", "xboard", "us", 2356, False),
    ENGINE("amateur", "xboard", "us", 2352, False),
    ENGINE("jonesy", "xboard", "es", 2352, False),  # popochin
    ENGINE("popochin", "xboard", "es", 2347, False),
    ENGINE("tigran", "uci", "es", 2347, False),
    ENGINE("alex", "uci", "us", 2345, False),
    ENGINE("horizon", "xboard", "us", 2342, False),
    ENGINE("plisk", "uci", "us", 2341, False),  # Allows XB
    ENGINE("queen", "uci", "nl", 2338, False),  # Allows XB
    ENGINE("arion", "uci", "fr", 2333, False),
    ENGINE("eveann", "xboard", "es", 2333, False),
    ENGINE("gibbon", "uci", "fr", 2332, False),
    ENGINE("waxman", "xboard", "us", 2331, False),
    ENGINE("amundsen", "xboard", "se", 2330, False),
    ENGINE("thor", "xboard", "hr", 2330, False),
    ENGINE("sorgenkind", "xboard", "dk", 2329, False),
    ENGINE("sage", "xboard", "unknown", 2326, False),
    ENGINE("chezzz", "xboard", "dk", 2324, False),
    ENGINE("barbarossa", "uci", "at", 2322, False),
    # isa @fr (name too short)
    ENGINE("mediocre", "uci", "se", 2317, False),
    ENGINE("aice", "xboard", "gr", 2314, False),
    ENGINE("absolute-zero", "uci", "zh", 2311, False),
    ENGINE("sungorus", "uci", "es", 2311, False),
    # TODO: wine crash on Ubuntu 1804 with NebiyuAlien.exe
    # ENGINE("nebiyu", "xboard", "et", 2310, False),
    ENGINE("averno", "xboard", "es", 2309, False),
    ENGINE("asterisk", "uci", "hu", 2307, False),  # Allows XB
    ENGINE("joker", "xboard", "nl", 2305, False),
    ENGINE("tytan", "xboard", "pl", 2304, False),
    ENGINE("zevra", "uci", "ru", 2302, False),
    ENGINE("resp", "xboard", "de", 2298, False),
    ENGINE("knightx", "xboard2", "fr", 2297, False),
    ENGINE("ayito", "uci", "es", 2287, False),  # Formerly XB
    ENGINE("chaturanga", "xboard", "it", 2286, False),
    ENGINE("matilde", "xboard", "it", 2282, False),
    ENGINE("fischerle", "uci", "de", 2281, False),
    ENGINE("paladin", "uci", "in", 2274, False),
    ENGINE("rival", "uci", "gb", 2274, False),
    ENGINE("scidlet", "xboard", "nz", 2269, False),
    # esc @it (name too short)
    ENGINE("butcher", "xboard", "pl", 2264, False),
    ENGINE("kmtchess", "xboard", "es", 2263, False),
    ENGINE("natwarlal", "xboard", "in", 2262, False),
    ENGINE("zeus", "xboard", "ru", 2260, False),
    ENGINE("napoleon", "uci", "it", 2257, False),
    # doctor @de (unknown protocol)
    ENGINE("firefly", "uci", "hk", 2252, False),
    ENGINE("ct800", "uci", "de", 2241, False),
    ENGINE("robocide", "uci", "gb", 2240, False),
    ENGINE("gopher_check", "uci", "us", 2239, False),
    # ant @nl (name too short)
    ENGINE("anechka", "uci", "ru", 2235, False),
    ENGINE("dorpsgek", "xboard", "en", 2234, False),
    ENGINE("alichess", "uci", "de", 2232, False),
    ENGINE("joker2", "uci", "it", 2225, False),
    ENGINE("obender", "xboard", "ru", 2224, False),
    ENGINE("adam", "xboard", "fr", 2222, False),
    ENGINE("exacto", "xboard", "us", 2219, False),
    ENGINE("ramjet", "uci", "it", 2217, False),
    ENGINE("buzz", "xboard", "us", 2212, False),
    ENGINE("chessalex", "uci", "ru", 2205, False),
    ENGINE("chispa", "uci", "ar", 2205, False),  # Allows XB
    ENGINE("beowulf", "xboard", "gb", 2200, False),
    ENGINE("ng-play", "xboard", "gr", 2200, False),
    ENGINE("rattate", "xboard", "it", 2198, False),
    ENGINE("latista", "xboard", "us", 2195, False),
    ENGINE("sinobyl", "xboard", "us", 2195, False),
    ENGINE("sjaakii", "xboard", "nl", 2193, False),
    ENGINE("feuerstein", "uci", "de", 2191, False),
    # uralochka (blacklisted)
    ENGINE("atak", "xboard", "pl", 2184, False),
    ENGINE("neurosis", "xboard", "nl", 2184, False),
    ENGINE("madeleine", "uci", "it", 2183, False),  # Allows XB
    ENGINE("mango", "xboard", "ve", 2181, False),
    ENGINE("protej", "uci", "it", 2177, False),
    ENGINE("asymptote", "uci", "de", 2175, False),
    ENGINE("genesis", "xboard", "il", 2172, False),
    ENGINE("baislicka", "uci", "unknown", 2170, False),
    ENGINE("blackbishop", "uci", "de", 2163, False),  # Allows XB
    ENGINE("inmichess", "xboard", "at", 2161, False),
    ENGINE("kurt", "xboard", "de", 2159, False),
    ENGINE("blitzkrieg", "uci", "in", 2156, False),
    ENGINE("nagaskaki", "xboard", "za", 2154, False),
    ENGINE("chesley", "xboard", "us", 2147, False),
    ENGINE("alarm", "xboard", "se", 2144, False),
    ENGINE("lime", "uci", "gb", 2143, False),  # Allows XB
    ENGINE("tinychess", "uci", "unknown", 2143, False),
    ENGINE("hedgehog", "uci", "ru", 2141, False),
    ENGINE("sunsetter", "xboard", "de", 2139, False),
    ENGINE("fortress", "xboard", "it", 2135, False),
    ENGINE("chesskiss", "xboard", "unknown", 2132, False),
    ENGINE("nesik", "xboard", "pl", 2131, False),
    ENGINE("wjchess", "uci", "fr", 2131, False),
    ENGINE("invictus", "uci", "ph", 2129, False),
    ENGINE("uragano", "xboard", "it", 2128, False),
    ENGINE("prophet", "xboard", "us", 2124, False),
    ENGINE("clever-girl", "uci", "us", 2117, False),
    ENGINE("embla", "uci", "nl", 2113, False),
    # gk @nl (name too short)
    # alf @dk (name too short)
    ENGINE("knockout", "xboard", "de", 2108, False),
    ENGINE("bikjump", "uci", "nl", 2104, False),
    ENGINE("clarabit", "uci", "es", 2100, False),  # Allows XB
    ENGINE("wing", "xboard", "nl", 2100, False),
    ENGINE("adroitchess", "uci", "gb", 2084, False),
    ENGINE("parrot", "xboard", "us", 2077, False),
    ENGINE("weini", "xboard", "fr", 2075, False),  # Allows UCI
    ENGINE("abbess", "xboard", "us", 2067, False),
    ENGINE("alcibiades", "uci", "bg", 2066, False),
    ENGINE("little-wing", "uci", "fr", 2064, False),  # Allows XB
    ENGINE("gunborg", "uci", "unknown", 2060, False),
    ENGINE("chessmind", "uci", "de", 2058, False),
    ENGINE("monarch", "uci", "gb", 2057, False),
    ENGINE("matheus", "uci", "br", 2056, False),  # Allows XB
    ENGINE("crabby", "uci", "us", 2055, False),
    ENGINE("dolphin", "xboard", "vn", 2054, False),
    ENGINE("kingsout", "xboard", "de", 2054, False),
    ENGINE("bodo", "uci", "au", 2049, False),
    ENGINE("vice", "uci", "unknown", 2044, False),
    ENGINE("gerbil", "xboard", "us", 2042, False),
    ENGINE("rdchess", "xboard", "at", 2042, False),
    # ax @vn (name too short)
    ENGINE("jabba", "uci", "gb", 2034, False),
    ENGINE("cinnamon", "uci", "it", 2030, False),
    # plp @no (name too short)
    ENGINE("plywood", "xboard", "unknown", 2029, False),
    ENGINE("prochess", "uci", "it", 2027, False),
    ENGINE("bestia", "xboard", "ua", 2025, False),
    # zct @us (name too short)
    ENGINE("zetadva", "xboard", "de", 2022, False),
    ENGINE("detroid", "uci", "at", 2021, False),
    ENGINE("cupcake", "xboard", "us", 2012, False),
    ENGINE("delphimax", "uci", "de", 2012, False),
    ENGINE("freyr", "xboard", "ro", 2011, False),
    ENGINE("ecce", "uci", "ru", 2010, False),
    ENGINE("oberon", "xboard", "pl", 2010, False),
    ENGINE("bismark", "uci", "il", 2003, False),
    ENGINE("requiem", "xboard", "fi", 2002, False),
    ENGINE("leonidas", "xboard", "nl", 2000, False),
    ENGINE("ceibo", "uci", "ar", 1998, False),
    ENGINE("snowy", "uci", "us", 1994, False),
    ENGINE("potato", "xboard", "at", 1992, False),
    ENGINE("elephant", "xboard", "de", 1990, False),
    ENGINE("frank-walter", "xboard", "nl", 1989, False),
    ENGINE("gullydeckel", "xboard", "de", 1988, False),
    ENGINE("biglion", "uci", "cm", 1987, False),
    ENGINE("armageddon", "xboard", "pl", 1985, False),
    ENGINE("arabian-knight", "xboard", "pl", 1984, False),
    ENGINE("bubble", "uci", "br", 1983, False),
    ENGINE("faile", "xboard1", "ca", 1977, False),
    ENGINE("slibo", "xboard", "de", 1975, False),
    ENGINE("ladameblanche", "xboard", "fr", 1971, False),
    ENGINE("matant", "xboard", "pl", 1971, False),
    ENGINE("ssechess", "xboard", "us", 1965, False),
    ENGINE("monik", "xboard", "unknown", 1964, False),
    ENGINE("etude", "uci", "us", 1963, False),
    ENGINE("cilian", "xboard", "ch", 1962, False),
    ENGINE("chess4j", "xboard", "us", 1961, False),
    # bsc @fr (name too short)
    # eia @ru (name too short)
    ENGINE("sissa", "uci", "fr", 1956, False),
    ENGINE("alchess", "uci", "ru", 1955, False),
    ENGINE("mustang", "xboard", "by", 1953, False),
    ENGINE("micro-max", "xboard", "nl", 1950, False),
    ENGINE("janwillem", "xboard", "nl", 1948, False),
    ENGINE("pleco", "uci", "us", 1945, False),
    ENGINE("sharper", "xboard", "se", 1937, False),
    ENGINE("bibichess", "uci", "fr", 1925, False),
    ENGINE("smash", "uci", "it", 1922, False),
    ENGINE("smirf", "xboard", "de", 1919, False),
    ENGINE("heracles", "uci", "fr", 1918, False),
    ENGINE("samchess", "xboard", "us", 1917, False),
    ENGINE("dabbaba", "xboard", "dk", 1914, False),
    ENGINE("iach", "xboard", "unknown", 1914, False),
    ENGINE("eagle", "uci", "uci", 1912, False),
    ENGINE("bambam", "xboard", "at", 1911, False),
    ENGINE("reger", "xboard", "nl", 1911, False),
    ENGINE("warrior", "xboard", "lv", 1904, False),
    ENGINE("clueless", "uci", "de", 1903, False),
    ENGINE("claudia", "uci", "es", 1900, False),
    ENGINE("morphy", "xboard", "us", 1898, False),
    ENGINE("snailchess", "xboard", "sg", 1896, False),
    ENGINE("tyrell", "uci", "us", 1892, False),
    ENGINE("mrchess", "xboard", "sg", 1891, False),
    # freechess @ru (blacklisted)
    ENGINE("matmoi", "xboard", "ca", 1885, False),
    ENGINE("surprise", "xboard", "de", 1880, False),
    ENGINE("purplehaze", "xboard", "fr", 1878, False),
    ENGINE("presbyter", "uci", "unknown", 1857, False),  # Allows XB
    ENGINE("simontacchi", "uci", "us", 1855, False),
    ENGINE("butter", "uci", "unknown", 1853, False),
    ENGINE("roce", "uci", "ch", 1848, False),
    ENGINE("ranita", "uci", "fr", 1840, False),
    ENGINE("deepov", "uci", "fr", 1832, False),
    ENGINE("sayuri", "uci", "jp", 1828, False),
    ENGINE("heavychess", "uci", "ar", 1823, False),
    ENGINE("ajedreztactico", "xboard", "mx", 1821, False),
    ENGINE("celes", "uci", "nl", 1821, False),
    ENGINE("rataaeroespacial", "xboard", "ar", 1819, False),
    ENGINE("jars", "xboard", "fr", 1817, False),
    ENGINE("skiull", "uci", "ve", 1813, False),
    ENGINE("noonian", "uci", "us", 1808, False),
    ENGINE("ziggurat", "uci", "us", 1808, False),
    ENGINE("predateur", "uci", "fr", 1807, False),
    ENGINE("chenard", "xboard", "us", 1804, False),
    ENGINE("morphychess", "xboard", "us", 1801, False),
    ENGINE("beaches", "xboard", "us", 1800, False),
    ENGINE("milady", "xboard", "fr", 1797, False),
    ENGINE("pigeon", "uci", "ca", 1795, False),
    ENGINE("hoichess", "xboard", "de", 1794, False),
    ENGINE("macromix", "uci", "ua", 1791, False),
    ENGINE("enigma", "xboard", "pl", 1788, False),
    ENGINE("bremboce", "xboard", "it", 1786, False),
    ENGINE("mobmat", "uci", "us", 1784, False),
    ENGINE("cecir", "xboard", "uy", 1781, False),
    ENGINE("grizzly", "xboard", "de", 1779, False),
    ENGINE("embracer", "xboard", "se", 1777, False),
    ENGINE("fauce", "xboard", "it", 1772, False),
    ENGINE("berochess", "uci", "de", 1768, False),
    ENGINE("pulsar", "xboard", "us", 1761, False),
    ENGINE("mint", "xboard", "se", 1760, False),
    ENGINE("robin", "xboard", "pl", 1756, False),
    ENGINE("lodocase", "xboard", "be", 1754, False),
    ENGINE("laurifer", "xboard", "pl", 1742, False),
    ENGINE("rocinante", "uci", "es", 1737, False),
    # elf @tr (name too short)
    ENGINE("ziggy", "uci", "is", 1731, False),
    ENGINE("vicki", "xboard", "za", 1728, False),
    ENGINE("adamant", "xboard", "ru", 1723, False),
    ENGINE("kanguruh", "xboard", "at", 1723, False),
    ENGINE("zzzzzz", "xboard", "nl", 1720, False),
    ENGINE("gchess", "xboard", "it", 1717, False),
    ENGINE("kitteneitor", "xboard", "es", 1717, False),
    ENGINE("zoidberg", "xboard", "es", 1717, False),
    ENGINE("jaksah", "uci", "rs", 1713, False),  # Allows XB
    ENGINE("tscp", "xboard", "us", 1709, False),
    # see @au (name too short)
    ENGINE("aldebaran", "xboard", "it", 1706, False),
    ENGINE("enkochess", "uci", "unknown", 1698, False),
    ENGINE("tristram", "xboard", "us", 1691, False),
    ENGINE("testina", "uci", "it", 1689, False),
    ENGINE("jester", "xboard", "us", 1686, False),
    # chess @it (name too generic)
    ENGINE("sharpchess", "xboard", "unknown", 1682, False),
    ENGINE("gargamella", "xboard", "it", 1681, False),
    ENGINE("bace", "xboard", "us", 1671, False),
    ENGINE("mizar", "xboard", "it", 1671, False),
    ENGINE("polarchess", "xboard", "no", 1668, False),
    ENGINE("golem", "xboard", "it", 1663, False),
    ENGINE("belzebub", "xboard", "pl", 1649, False),
    ENGINE("dchess", "xboard", "us", 1642, False),
    ENGINE("pooky", "uci", "us", 1642, False),
    ENGINE("adachess", "xboard", "it", 1641, False),
    ENGINE("simon", "xboard", "us", 1635, False),
    ENGINE("iq23", "uci", "de", 1633, False),
    ENGINE("vapor", "uci", "us", 1630, False),
    ENGINE("spartan", "uci", "unknown", 1629, False),
    ENGINE("chessrikus", "xboard", "us", 1624, False),
    ENGINE("mscp", "xboard", "nl", 1623, False),
    ENGINE("storm", "xboard", "us", 1616, False),
    ENGINE("monochrome", "uci", "unknown", 1614, False),
    ENGINE("philemon", "uci", "ch", 1608, False),
    ENGINE("revati", "uci", "de", 1608, False),
    ENGINE("kasparov", "uci", "ca", 1607, False),
    ENGINE("darky", "uci", "mx", 1603, False),
    ENGINE("rainman", "xboard", "se", 1597, False),
    ENGINE("saruman", "uci", "unknown", 1597, False),
    ENGINE("marginal", "uci", "ru", 1592, False),
    ENGINE("bullitchess", "uci", "unknown", 1587, False),
    ENGINE("pulse", "uci", "ch", 1583, False),
    ENGINE("zotron", "xboard", "us", 1575, False),
    ENGINE("damas", "xboard", "br", 1566, False),
    ENGINE("sdbc", "xboard", "de", 1566, False),
    ENGINE("needle", "xboard", "fi", 1565, False),
    ENGINE("vanilla", "xboard", "au", 1565, False),
    ENGINE("violet", "uci", "unknown", 1564, False),
    ENGINE("shallowblue", "uci", "ca", 1563, False),
    ENGINE("cicada", "uci", "us", 1562, False),
    ENGINE("hokus", "xboard", "pl", 1545, False),
    ENGINE("larsen", "xboard", "it", 1532, False),
    ENGINE("mace", "uci", "de", 1531, False),
    ENGINE("trappist", "uci", "unknown", 1519, False),
    ENGINE("alibaba", "uci", "nl", 1515, False),
    ENGINE("yawce", "xboard", "dk", 1506, False),
    ENGINE("supra", "uci", "pt", 1497, False),
    ENGINE("apep", "xboard", "us", 1496, False),
    ENGINE("koedem", "uci", "de", 1486, False),
    ENGINE("piranha", "uci", "de", 1486, False),
    ENGINE("tarrasch", "uci", "us", 1480, False),
    ENGINE("andersen", "xboard", "se", 1477, False),
    ENGINE("gedeone", "xboard", "unknown", 1472, False),
    ENGINE("pwned", "uci", "us", 1472, False),
    ENGINE("apil", "xboard", "de", 1470, False),
    ENGINE("pentagon", "xboard", "it", 1468, False),
    ENGINE("roque", "xboard", "es", 1457, False),
    ENGINE("numpty", "xboard", "gb", 1455, False),
    ENGINE("blikskottel", "xboard", "za", 1443, False),
    ENGINE("nero", "xboard", "de", 1435, False),
    ENGINE("hactar", "uci", "de", 1433, False),
    ENGINE("suff", "uci", "at", 1410, False),
    ENGINE("sabrina", "xboard", "it", 1403, False),
    ENGINE("quokka", "uci", "us", 1398, False),
    ENGINE("tony", "xboard", "ca", 1397, False),
    ENGINE("satana", "xboard", "it", 1395, False),
    ENGINE("goyaz", "xboard", "br", 1393, False),
    ENGINE("eden", "uci", "de", 1391, False),
    ENGINE("minimardi", "xboard", "unknown", 1391, False),
    ENGINE("jchess", "xboard", "pl", 1382, False),
    ENGINE("nanook", "uci", "fr", 1376, False),
    ENGINE("skaki", "xboard", "us", 1363, False),
    ENGINE("virutor", "uci", "cz", 1360, False),
    ENGINE("minichessai", "xboard", "pl", 1348, False),
    ENGINE("apollo", "uci", "us", 1332, False),
    ENGINE("joanna", "xboard", "pl", 1332, False),
    ENGINE("ozwald", "xboard", "fi", 1328, False),
    ENGINE("gladiator", "xboard", "es", 1318, False),
    ENGINE("fimbulwinter", "xboard", "us", 1306, False),
    ENGINE("cerulean", "xboard", "ca", 1291, False),
    ENGINE("killerqueen", "uci", "it", 1284, False),
    # chess (name too generic)
    ENGINE("trex", "uci", "fr", 1279, False),
    ENGINE("qutechess", "uci", "si", 1267, False),
    ENGINE("tikov", "uci", "gb", 1236, False),
    ENGINE("raffaela", "xboard", "it", 1223, False),
    ENGINE("dragontooth", "uci", "us", 1222, False),
    # gringo - grounding tools for (disjunctive) logic programs
    # ENGINE("gringo", "xboard", "at", 1222, False),
    ENGINE("pierre", "xboard", "ca", 1221, False),
    ENGINE("toledo-uci", "uci", "mx", 1218, True),
    ENGINE("toledo", "xboard", "mx", 1218, False),
    ENGINE("neurone", "xboard", "it", 1205, False),
    ENGINE("gray-matter", "xboard", "unknown", 1198, False),
    ENGINE("darkfusch", "uci", "de", 1177, False),
    ENGINE("project-invincible", "xboard", "fi", 1174, False),
    ENGINE("cassandre", "uci", "fr", 1148, False),  # Allows XB
    ENGINE("jchecs", "xboard", "fr", 1132, False),
    ENGINE("brama", "xboard", "it", 1130, False),
    ENGINE("soberango", "xboard", "ar", 1127, False),
    ENGINE("usurpator", "xboard", "nl", 1122, False),
    ENGINE("ronja", "xboard", "se", 1085, False),
    ENGINE("blitzter", "xboard", "de", 1071, False),
    ENGINE("frank", "xboard", "it", 1067, False),
    ENGINE("strategicdeep", "xboard", "pl", 1062, False),
    ENGINE("talvmenni", "xboard", "fo", 1058, False),
    ENGINE("minnow", "uci", "unknown", 1043, False),
    ENGINE("xadreco", "xboard", "br", 1019, False),
    ENGINE("safrad", "uci", "cz", 1014, False),
    ENGINE("giuchess", "xboard", "it", 997, False),
    ENGINE("iota", "uci", "gb", 995, False),
    # zoe (name too short)
    ENGINE("kace", "xboard", "us", 965, False),
    ENGINE("youk", "xboard", "fr", 962, False),
    ENGINE("nsvchess", "uci", "fr", 939, False),
    ENGINE("chad", "uci", "xb", 930, False),
    ENGINE("dreamer", "xboard", "nl", 889, False),
    ENGINE("luzhin", "xboard", "unknown", 885, False),
    ENGINE("dika", "xboard", "fr", 876, False),
    ENGINE("hippocampe", "xboard", "fr", 839, False),
    ENGINE("pyotr", "xboard", "gr", 792, False),
    ENGINE("chessputer", "uci", "unknown", 780, False),
    ENGINE("belofte", "uci", "be", 729, False),  # Allows XB
    # easypeasy (no information)
    ENGINE("acqua", "uci", "it", 555, False),
    # neg @nl (name too short)
    # ram @nl (name too short)
    ENGINE("lamosca", "xboard", "it", 495, False),
    # ace @us (name too short)
    # pos @nl (name too short)

    # -- Other (parent engine, derivative work, unlisted, variant engine...)
    ENGINE("s_pro", "uci", "it", 0, False),
    ENGINE("asmfish", "uci", "bg", 0, False),
    ENGINE("glaurung", "uci", "no", 0, False),
    ENGINE("amundsen", "xboard", "se", 0, False),
    ENGINE("anticrux", "uci", "fr", 0, True),
    ENGINE("fairymax", "xboard", "nl", 0, False),
    ENGINE("fruit", "uci", "fr", 0, False)
]


# Bubble sort by descending length of the name
for i in range(len(ENGINES_LIST) - 1, 1, - 1):
    for j in range(0, i - 1):
        if len(ENGINES_LIST[i].name) > len(ENGINES_LIST[j].name):
            tmp = ENGINES_LIST[i]
            ENGINES_LIST[i] = ENGINES_LIST[j]
            ENGINES_LIST[j] = tmp
