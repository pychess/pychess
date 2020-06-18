import os
import sys
from collections import namedtuple
from pychess.System.cpu import get_cpu


# Constants
AUTO_DETECT = True
NO_AUTO_DETECT = False

# CPUID
cpu = get_cpu()

# List of known interpreters
PYTHONBIN = sys.executable.split("/")[-1]
VM = namedtuple('VM', 'name, ext, args')
VM_LIST = [
    VM("node", ".js", None),
    VM("java", ".jar", ["-jar"]),
    VM(PYTHONBIN, ".py", ["-u"])
]

# Needed by shutil.which() on Windows to find .py engines
if cpu['windows']:
    for vm in VM_LIST:
        if vm.ext.upper() not in os.getenv("PATHEXT"):
            os.environ["PATHEXT"] += ";%s" % vm.ext.upper()

# List of engines later sorted by descending length of name
# The comments provides known conflicts with Linux packages
# Weak engines (<2700) should be added manually unless a package exists already
if cpu['windows']:
    stockfish_name = "stockfish_11_x%s.exe" % cpu['bitness']
    sjaakii_name = "sjaakii_win%s_ms.exe" % cpu['bitness']
else:
    stockfish_name = "stockfish"
    sjaakii_name = "sjaakii"

ENGINE = namedtuple('ENGINE', 'name, protocol, country, elo, autoDetect, defaultLevel')
ENGINES_LIST = [
    # -- Full names for internal processing
    ENGINE("PyChess.py", "xboard", "dk", 0, AUTO_DETECT, 5),
    ENGINE("pychess-engine", "xboard", "dk", 0, AUTO_DETECT, 5),
    ENGINE(stockfish_name, "uci", "no", 3554, AUTO_DETECT, None),
    ENGINE(sjaakii_name, "xboard", "nl", 2194, AUTO_DETECT, None),
    ENGINE("Houdini.exe", "uci", "be", 3526, AUTO_DETECT, None),
    ENGINE("Rybka.exe", "uci", "cz", 3207, AUTO_DETECT, None),

    # -- Engines from CCRL 40/4
    ENGINE("leelenstein", "uci", "unknown", 3618, NO_AUTO_DETECT, None),
    ENGINE("leela", "uci", "us", 3641, NO_AUTO_DETECT, None),
    ENGINE("lczero", "uci", "us", 3641, NO_AUTO_DETECT, None),
    ENGINE("lc0", "uci", "us", 3641, NO_AUTO_DETECT, None),
    ENGINE("fatfritz", "uci", "nl", 3624, NO_AUTO_DETECT, None),
    ENGINE("stockfish", "uci", "no", 3601, AUTO_DETECT, None),
    ENGINE("allie", "uci", "unknown", 3554, NO_AUTO_DETECT, None),
    ENGINE("stoofvlees", "", "be", 3554, NO_AUTO_DETECT, None),
    ENGINE("komodo", "uci", "us", 3527, AUTO_DETECT, None),
    ENGINE("houdini", "uci", "be", 3516, AUTO_DETECT, None),
    ENGINE("xiphos", "uci", "us", 3429, NO_AUTO_DETECT, None),  # xiphos - environment for Bible reading, study, and research
    ENGINE("fire", "uci", "us", 3426, NO_AUTO_DETECT, None),  # fire in mesa-demos https://www.archlinux.org/packages/extra/x86_64/mesa-demos/files/
    ENGINE("ethereal", "uci", "us", 3442, AUTO_DETECT, None),
    ENGINE("fritz", "uci", "nl", 3381, AUTO_DETECT, None),
    ENGINE("laser", "uci", "us", 3364, AUTO_DETECT, None),
    ENGINE("defenchess", "uci", "tr", 3355, AUTO_DETECT, None),
    ENGINE("rofchade", "uci", "nl", 3396, AUTO_DETECT, None),
    ENGINE("fizbo", "uci", "us", 3346, AUTO_DETECT, None),
    ENGINE("andscacs", "uci", "ad", 3337, AUTO_DETECT, None),
    ENGINE("booot", "uci", "ua", 3357, AUTO_DETECT, None),  # Formerly XB
    ENGINE("shredder", "uci", "de", 3323, AUTO_DETECT, None),
    ENGINE("schooner", "xboard", "ca", 3288, AUTO_DETECT, None),
    ENGINE("arasan", "uci", "us", 3274, AUTO_DETECT, None),
    ENGINE("rubichess", "uci", "de", 3292, AUTO_DETECT, None),
    ENGINE("gull", "uci", "ru", 3260, AUTO_DETECT, None),
    ENGINE("equinox", "uci", "it", 3252, AUTO_DETECT, None),
    ENGINE("pedone", "uci", "it", 3255, AUTO_DETECT, None),
    ENGINE("chiron", "uci", "it", 3244, AUTO_DETECT, None),  # Allows XB
    ENGINE("critter", "uci", "sk", 3233, AUTO_DETECT, None),
    ENGINE("vajolet", "uci", "it", 3229, AUTO_DETECT, None),
    ENGINE("hannibal", "uci", "us", 3225, AUTO_DETECT, None),
    ENGINE("nirvana", "uci", "us", 3224, AUTO_DETECT, None),
    ENGINE("rybka", "uci", "cz", 3206, AUTO_DETECT, None),
    ENGINE("texel", "xboard", "se", 3196, AUTO_DETECT, None),  # UCI is an option in the command line
    ENGINE("blackmamba", "uci", "it", 3197, AUTO_DETECT, None),
    ENGINE("wasp", "uci", "us", 3191, AUTO_DETECT, None),
    ENGINE("nemorino", "uci", "de", 3179, AUTO_DETECT, None),  # Allows XB
    ENGINE("senpai", "uci", "fr", 3177, AUTO_DETECT, None),
    # ivanhoe, robbolito, panchess, bouquet, elektro
    # ice (name too short)
    ENGINE("naum", "uci", "rs", 3151, AUTO_DETECT, None),
    ENGINE("strelka", "uci", "ru", 3142, AUTO_DETECT, None),
    ENGINE("protector", "uci", "de", 3129, AUTO_DETECT, None),
    ENGINE("chessbrain", "uci", "de", 3170, AUTO_DETECT, None),  # Allows XB
    ENGINE("hiarcs", "uci", "gb", 3108, AUTO_DETECT, None),
    ENGINE("demolito", "uci", "fr", 3216, AUTO_DETECT, None),
    ENGINE("rodent", "uci", "pl", 3090, AUTO_DETECT, None),
    ENGINE("pesto", "uci", "nl", 3100, NO_AUTO_DETECT, None),
    ENGINE("chess22k", "uci", "nl", 3181, AUTO_DETECT, None),
    ENGINE("pirarucu", "uci", "br", 3132, AUTO_DETECT, None),
    ENGINE("winter", "uci", "ch", 3129, NO_AUTO_DETECT, None),
    ENGINE("cheng", "uci", "cz", 3063, AUTO_DETECT, None),
    ENGINE("crafty", "xboard", "us", 3053, AUTO_DETECT, None),
    ENGINE("marvin", "uci", "se", 3077, AUTO_DETECT, None),  # Allows XB
    ENGINE("bobcat", "uci", "nl", 3057, AUTO_DETECT, None),
    ENGINE("amoeba", "uci", "fr", 3102, AUTO_DETECT, None),
    ENGINE("smarthink", "uci", "ru", 3043, AUTO_DETECT, None),  # Allows XB
    ENGINE("spike", "uci", "de", 3040, AUTO_DETECT, None),  # Allows XB
    ENGINE("alfil", "uci", "es", 3031, AUTO_DETECT, None),
    ENGINE("igel", "uci", "ch", 3187, NO_AUTO_DETECT, None),
    ENGINE("minic", "xboard", "fr", 3138, NO_AUTO_DETECT, None),
    ENGINE("spark", "uci", "nl", 3027, NO_AUTO_DETECT, None),  # spark - Apache tool
    ENGINE("junior", "uci", "il", 3026, AUTO_DETECT, None),
    ENGINE("schess", "uci", "us", 3263, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("sblitz", "uci", "us", 3263, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("deuterium", "uci", "ph", 3022, AUTO_DETECT, None),
    ENGINE("hakkapeliitta", "uci", "fi", 3020, AUTO_DETECT, None),
    ENGINE("exchess", "xboard", "us", 3018, AUTO_DETECT, None),
    ENGINE("gogobello", "uci", "it", 3069, AUTO_DETECT, None),
    ENGINE("invictus", "uci", "ph", 3003, NO_AUTO_DETECT, None),
    ENGINE("topple", "uci", "unknown", 3055, NO_AUTO_DETECT, None),
    ENGINE("tucano", "xboard", "br", 2991, AUTO_DETECT, None),
    ENGINE("scorpio", "xboard", "et", 2994, AUTO_DETECT, None),
    ENGINE("baron", "xboard", "nl", 2989, AUTO_DETECT, None),
    ENGINE("asymptote", "uci", "de", 3007, NO_AUTO_DETECT, None),
    ENGINE("gaviota", "xboard", "ar", 2978, AUTO_DETECT, None),
    ENGINE("zappa", "uci", "us", 2973, AUTO_DETECT, None),
    ENGINE("fabchess", "uci", "de", 3019, NO_AUTO_DETECT, None),
    ENGINE("togaii", "uci", "de", 2963, AUTO_DETECT, None),
    ENGINE("toga2", "uci", "de", 2963, AUTO_DETECT, None),
    ENGINE("counter", "uci", "ru", 2959, NO_AUTO_DETECT, None),
    ENGINE("onno", "uci", "de", 2956, AUTO_DETECT, None),
    ENGINE("thinker", "uci", "ca", 2954, AUTO_DETECT, None),
    ENGINE("bagatur", "uci", "bg", 3036, NO_AUTO_DETECT, None),
    ENGINE("godel", "uci", "es", 2982, AUTO_DETECT, None),  # May allow XB
    ENGINE("sjeng", "xboard", "be", 2941, AUTO_DETECT, None),
    ENGINE("disasterarea", "uci", "de", 2938, AUTO_DETECT, None),
    ENGINE("atlas", "uci", "es", 2924, NO_AUTO_DETECT, None),
    ENGINE("dirty", "xboard", "es", 2926, AUTO_DETECT, None),
    ENGINE("discocheck", "uci", "fr", 2915, AUTO_DETECT, None),
    ENGINE("monolith", "uci", "it", 3102, NO_AUTO_DETECT, None),
    ENGINE("bright", "uci", "nl", 2911, AUTO_DETECT, None),
    ENGINE("minko", "uci", "sv", 2911, AUTO_DETECT, None),
    ENGINE("quazar", "uci", "ru", 2901, AUTO_DETECT, None),
    ENGINE("zurichess", "uci", "ro", 2901, AUTO_DETECT, None),
    ENGINE("daydreamer", "uci", "us", 2893, AUTO_DETECT, None),
    ENGINE("cheese", "uci", "fr", 2904, NO_AUTO_DETECT, None),  # Allows XB; cheese - tool to take pictures and videos from your webcam
    ENGINE("murka", "uci", "by", 2883, AUTO_DETECT, None),
    ENGINE("loop", "uci", "de", 2882, NO_AUTO_DETECT, None),
    ENGINE("tornado", "uci", "de", 2867, AUTO_DETECT, None),
    ENGINE("francesca", "xboard", "gb", 2901, NO_AUTO_DETECT, None),
    ENGINE("nemo", "uci", "de", 2857, NO_AUTO_DETECT, None),  # nemo - File manager and graphical shell for Cinnamon
    ENGINE("bugchess", "xboard", "fr", 2843, AUTO_DETECT, None),
    ENGINE("octochess", "uci", "de", 2823, AUTO_DETECT, None),  # Allows XB
    ENGINE("gnuchessu", "uci", "us", 2808, NO_AUTO_DETECT, None),
    ENGINE("gnuchess", "xboard", "us", 2808, AUTO_DETECT, None),
    ENGINE("ruydos", "uci", "es", 2807, AUTO_DETECT, None),
    ENGINE("rhetoric", "uci", "es", 2806, AUTO_DETECT, None),
    ENGINE("shield", "uci", "it", 2798, NO_AUTO_DETECT, None),
    ENGINE("fridolin", "uci", "de", 2791, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("ktulu", "uci", "ir", 2782, AUTO_DETECT, None),  # Allows XB
    ENGINE("prodeo", "uci", "nl", 2771, AUTO_DETECT, None),  # Allows XB
    ENGINE("twisted-logic", "uci", "ph", 2770, AUTO_DETECT, None),
    ENGINE("frenzee", "xboard", "dk", 2770, AUTO_DETECT, None),
    ENGINE("pawny", "uci", "bg", 2767, AUTO_DETECT, None),
    ENGINE("tomitank", "uci", "hu", 2832, NO_AUTO_DETECT, None),
    ENGINE("jonny", "uci", "de", 2762, AUTO_DETECT, None),  # Formerly XB
    ENGINE("bison", "uci", "ru", 2762, NO_AUTO_DETECT, None),  # bison - YACC-compatible parser generator
    ENGINE("chessmaster", "xboard", "nl", 2757, AUTO_DETECT, None),
    ENGINE("arminius", "xboard", "de", 2757, NO_AUTO_DETECT, None),
    ENGINE("chronos", "uci", "ar", 2739, AUTO_DETECT, None),
    ENGINE("karballo", "uci", "es", 2730, AUTO_DETECT, None),
    ENGINE("tiger", "uci", "gp", 2713, AUTO_DETECT, None),
    ENGINE("devel", "uci", "no", 2765, NO_AUTO_DETECT, None),
    ENGINE("greko", "uci", "ru", 2752, AUTO_DETECT, None),
    ENGINE("ece-x3", "uci", "it", 2701, NO_AUTO_DETECT, None),
    ENGINE("donna", "uci", "us", 2695, NO_AUTO_DETECT, None),
    ENGINE("danasah", "uci", "es", 2689, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("redqueen", "uci", "br", 2689, NO_AUTO_DETECT, None),
    ENGINE("delfi", "uci", "it", 2683, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("djinn", "xboard", "us", 2674, NO_AUTO_DETECT, None),
    ENGINE("pharaon", "uci", "fr", 2674, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("alaric", "uci", "se", 2662, NO_AUTO_DETECT, None),  # Allows XB
    # k2 (name to short)
    ENGINE("gandalf", "uci", "dk", 2663, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("dorky", "xboard", "us", 2653, NO_AUTO_DETECT, None),
    ENGINE("naraku", "uci", "it", 2653, NO_AUTO_DETECT, None),
    ENGINE("nebula", "uci", "rs", 2653, NO_AUTO_DETECT, None),
    ENGINE("phalanx", "xboard1", "cz", 2655, NO_AUTO_DETECT, None),
    ENGINE("colossus", "uci", "gb", 2641, NO_AUTO_DETECT, None),
    ENGINE("cyrano", "uci", "no", 2641, NO_AUTO_DETECT, None),
    ENGINE("sjakk", "uci", "no", 2637, NO_AUTO_DETECT, None),
    ENGINE("rodin", "xboard", "es", 2638, NO_AUTO_DETECT, None),
    ENGINE("et_chess", "xboard2", "fr", 2634, NO_AUTO_DETECT, None),
    ENGINE("wyldchess", "uci", "in", 2628, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("detroid", "uci", "at", 2626, NO_AUTO_DETECT, None),
    ENGINE("weiss", "uci", "no", 2844, NO_AUTO_DETECT, None),
    ENGINE("wildcat", "uci", "by", 2624, NO_AUTO_DETECT, None),  # Formerly XB
    ENGINE("movei", "uci", "il", 2622, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("orion", "uci", "fr", 2624, NO_AUTO_DETECT, None),
    ENGINE("philou", "uci", "fr", 2619, NO_AUTO_DETECT, None),
    ENGINE("rotor", "uci", "nl", 2618, NO_AUTO_DETECT, None),
    ENGINE("zarkov", "xboard", "us", 2619, NO_AUTO_DETECT, None),
    ENGINE("sloppy", "xboard", "fi", 2616, NO_AUTO_DETECT, None),
    ENGINE("coiled", "uci", "es", 2611, NO_AUTO_DETECT, None),
    ENGINE("delocto", "uci", "at", 2755, NO_AUTO_DETECT, None),
    ENGINE("glass", "uci", "pl", 2611, NO_AUTO_DETECT, None),
    ENGINE("jellyfish", "uci", "unknown", 2611, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("noragrace", "xboard", "us", 2610, NO_AUTO_DETECT, None),
    ENGINE("ruffian", "uci", "se", 2609, NO_AUTO_DETECT, None),
    ENGINE("caligula", "uci", "es", 2605, NO_AUTO_DETECT, None),
    ENGINE("garbochess", "uci", "us", 2606, NO_AUTO_DETECT, None),
    ENGINE("amyan", "uci", "cl", 2604, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("lemming", "xboard", "us", 2599, NO_AUTO_DETECT, None),
    # n2 (name to short)
    ENGINE("nawito", "uci", "cu", 2589, NO_AUTO_DETECT, None),
    ENGINE("floyd", "uci", "nl", 2583, NO_AUTO_DETECT, None),
    ENGINE("cuckoo", "xboard", "se", 2583, NO_AUTO_DETECT, None),  # UCI is an option in the command line
    ENGINE("muse", "xboard", "ch", 2577, NO_AUTO_DETECT, None),  # May support UCI as well
    ENGINE("hamsters", "uci", "it", 2579, NO_AUTO_DETECT, None),
    ENGINE("pseudo", "xboard", "cz", 2576, NO_AUTO_DETECT, None),
    ENGINE("galjoen", "uci", "be", 2565, NO_AUTO_DETECT, None),  # Allows XB
    # sos (name too short)
    ENGINE("maverick", "uci", "gb", 2569, NO_AUTO_DETECT, None),
    ENGINE("aristarch", "uci", "de", 2567, NO_AUTO_DETECT, None),
    ENGINE("petir", "xboard", "id", 2566, NO_AUTO_DETECT, None),
    ENGINE("capivara", "uci", "br", 2565, NO_AUTO_DETECT, None),
    ENGINE("nanoszachy", "xboard", "pl", 2562, NO_AUTO_DETECT, None),
    ENGINE("brutus", "xboard", "nl", 2559, NO_AUTO_DETECT, None),
    ENGINE("dimitri", "uci", "it", 2557, NO_AUTO_DETECT, None),  # May allow XB
    ENGINE("ghost", "xboard", "de", 2553, NO_AUTO_DETECT, None),
    ENGINE("jumbo", "xboard", "de", 2547, NO_AUTO_DETECT, None),
    ENGINE("anaconda", "uci", "de", 2546, NO_AUTO_DETECT, None),
    ENGINE("frank-walter", "xboard", "nl", 2545, NO_AUTO_DETECT, None),
    ENGINE("rebel", "uci", "nl", 2544, NO_AUTO_DETECT, None),
    ENGINE("betsabe", "xboard", "es", 2563, NO_AUTO_DETECT, None),
    ENGINE("hermann", "uci", "de", 2540, NO_AUTO_DETECT, None),
    ENGINE("ufim", "uci", "ru", 2540, NO_AUTO_DETECT, None),  # Formerly XB
    ENGINE("anmon", "uci", "fr", 2539, NO_AUTO_DETECT, None),
    ENGINE("pupsi", "uci", "se", 2538, NO_AUTO_DETECT, None),
    ENGINE("jikchess", "xboard2", "fi", 2523, NO_AUTO_DETECT, None),
    ENGINE("pepito", "xboard", "es", 2521, NO_AUTO_DETECT, None),
    ENGINE("axolotl", "uci", "de", 2507, NO_AUTO_DETECT, None),
    ENGINE("danchess", "xboard", "et", 2504, NO_AUTO_DETECT, None),
    ENGINE("greenlight", "xboard", "gb", 2505, NO_AUTO_DETECT, None),
    ENGINE("goliath", "uci", "de", 2505, NO_AUTO_DETECT, None),
    ENGINE("yace", "uci", "de", 2503, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("trace", "xboard", "au", 2502, NO_AUTO_DETECT, None),
    ENGINE("cyberpagno", "xboard", "it", 2493, NO_AUTO_DETECT, None),
    ENGINE("bruja", "xboard", "us", 2491, NO_AUTO_DETECT, None),
    ENGINE("magnum", "uci", "ca", 2491, NO_AUTO_DETECT, None),
    ENGINE("nemeton", "xboard", "nl", 2491, NO_AUTO_DETECT, None),
    # tao (name too short)
    ENGINE("gothmog", "uci", "no", 2482, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("bbchess", "uci", "si", 2479, NO_AUTO_DETECT, None),
    ENGINE("drosophila", "xboard", "se", 2673, NO_AUTO_DETECT, None),
    ENGINE("delphil", "uci", "fr", 2469, NO_AUTO_DETECT, None),
    ENGINE("mephisto", "uci", "gb", 2475, NO_AUTO_DETECT, None),
    ENGINE("cerebro", "xboard", "it", 2472, NO_AUTO_DETECT, None),
    ENGINE("kiwi", "xboard", "it", 2469, NO_AUTO_DETECT, None),
    ENGINE("xpdnt", "xboard", "us", 2469, NO_AUTO_DETECT, None),
    ENGINE("myrddin", "xboard", "us", 2459, NO_AUTO_DETECT, None),
    ENGINE("pikoszachy", "xboard", "pl", 2456, NO_AUTO_DETECT, None),
    ENGINE("anatoli", "xboard", "nl", 2456, NO_AUTO_DETECT, None),
    ENGINE("littlethought", "uci", "au", 2452, NO_AUTO_DETECT, None),
    ENGINE("matacz", "xboard", "pl", 2446, NO_AUTO_DETECT, None),
    ENGINE("tunguska", "uci", "br", 2443, NO_AUTO_DETECT, None),
    ENGINE("lozza", "uci", "gb", 2444, NO_AUTO_DETECT, None),
    ENGINE("ares", "uci", "us", 2441, NO_AUTO_DETECT, None),
    ENGINE("bumblebee", "uci", "us", 2435, NO_AUTO_DETECT, None),
    ENGINE("soldat", "xboard", "it", 2438, NO_AUTO_DETECT, None),
    ENGINE("spider", "xboard", "nl", 2439, NO_AUTO_DETECT, None),
    ENGINE("madchess", "uci", "us", 2433, NO_AUTO_DETECT, None),
    ENGINE("abrok", "uci", "de", 2432, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("lambchop", "uci", "nz", 2434, NO_AUTO_DETECT, None),  # Formerly XB
    ENGINE("kingofkings", "uci", "ca", 2435, NO_AUTO_DETECT, None),
    ENGINE("flux", "uci", "ch", 2430, NO_AUTO_DETECT, None),
    ENGINE("shallow", "uci", "unknown", 2429, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("eeyore", "uci", "ru", 2428, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("zevra", "uci", "ru", 2426, NO_AUTO_DETECT, None),
    ENGINE("gaia", "uci", "fr", 2426, NO_AUTO_DETECT, None),
    ENGINE("gromit", "uci", "de", 2429, NO_AUTO_DETECT, None),
    ENGINE("nejmet", "uci", "fr", 2424, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("quark", "xboard", "de", 2423, NO_AUTO_DETECT, None),
    ENGINE("hussar", "uci", "hu", 2421, NO_AUTO_DETECT, None),
    ENGINE("snitch", "xboard", "de", 2418, NO_AUTO_DETECT, None),
    ENGINE("dragon", "xboard", "fr", 2417, NO_AUTO_DETECT, None),  # Video player
    ENGINE("olithink", "xboard", "de", 2416, NO_AUTO_DETECT, None),
    ENGINE("romichess", "xboard", "us", 2413, NO_AUTO_DETECT, None),
    ENGINE("typhoon", "xboard", "us", 2414, NO_AUTO_DETECT, None),
    ENGINE("giraffe", "xboard", "gb", 2410, NO_AUTO_DETECT, None),
    ENGINE("simplex", "uci", "es", 2408, NO_AUTO_DETECT, None),
    ENGINE("teki", "uci", "in", 2406, NO_AUTO_DETECT, None),
    ENGINE("taltos", "uci", "hu", 2402, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("ifrit", "uci", "ru", 2405, NO_AUTO_DETECT, None),
    ENGINE("tjchess", "uci", "us", 2399, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("knightdreamer", "xboard", "se", 2393, NO_AUTO_DETECT, None),
    ENGINE("bearded", "xboard", "pl", 2393, NO_AUTO_DETECT, None),
    ENGINE("starthinker", "uci", "de", 2390, NO_AUTO_DETECT, None),
    ENGINE("postmodernist", "xboard", "gb", 2390, NO_AUTO_DETECT, None),
    ENGINE("comet", "xboard", "de", 2388, NO_AUTO_DETECT, None),
    ENGINE("leila", "xboard", "it", 2387, NO_AUTO_DETECT, None),
    # amy (name too short)
    ENGINE("diablo", "uci", "us", 2385, NO_AUTO_DETECT, None),
    ENGINE("capture", "xboard", "fr", 2382, NO_AUTO_DETECT, None),
    ENGINE("gosu", "xboard", "pl", 2382, NO_AUTO_DETECT, None),
    ENGINE("barbarossa", "uci", "at", 2373, NO_AUTO_DETECT, None),
    ENGINE("cmcchess", "uci", "zh", 2378, NO_AUTO_DETECT, None),
    ENGINE("knightx", "xboard2", "fr", 2488, NO_AUTO_DETECT, None),
    ENGINE("bringer", "xboard", "de", 2374, NO_AUTO_DETECT, None),
    ENGINE("jazz", "xboard", "nl", 2374, NO_AUTO_DETECT, None),
    ENGINE("patzer", "xboard", "de", 2373, NO_AUTO_DETECT, None),
    ENGINE("terra", "uci", "se", 2369, NO_AUTO_DETECT, None),
    ENGINE("wchess", "xboard", "us", 2366, NO_AUTO_DETECT, None),  # Unsure protocol
    ENGINE("crazybishop", "xboard", "fr", 2364, NO_AUTO_DETECT, None),  # Named as tcb
    ENGINE("dumb", "uci", "fr", 2359, NO_AUTO_DETECT, None),
    ENGINE("homer", "uci", "de", 2357, NO_AUTO_DETECT, None),
    ENGINE("betsy", "xboard", "us", 2356, NO_AUTO_DETECT, None),
    ENGINE("jonesy", "xboard", "es", 2351, NO_AUTO_DETECT, None),  # popochin
    ENGINE("amateur", "xboard", "us", 2351, NO_AUTO_DETECT, None),
    ENGINE("alex", "uci", "us", 2348, NO_AUTO_DETECT, None),
    ENGINE("tigran", "uci", "es", 2345, NO_AUTO_DETECT, None),
    ENGINE("popochin", "xboard", "es", 2345, NO_AUTO_DETECT, None),
    ENGINE("plisk", "uci", "us", 2343, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("horizon", "xboard", "us", 2341, NO_AUTO_DETECT, None),
    ENGINE("queen", "uci", "nl", 2336, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("arion", "uci", "fr", 2332, NO_AUTO_DETECT, None),
    ENGINE("gibbon", "uci", "fr", 2332, NO_AUTO_DETECT, None),
    ENGINE("waxman", "xboard", "us", 2331, NO_AUTO_DETECT, None),
    ENGINE("thor", "xboard", "hr", 2330, NO_AUTO_DETECT, None),
    ENGINE("amundsen", "xboard", "se", 2328, NO_AUTO_DETECT, None),
    ENGINE("sorgenkind", "xboard", "dk", 2330, NO_AUTO_DETECT, None),
    ENGINE("eveann", "xboard", "es", 2328, NO_AUTO_DETECT, None),
    ENGINE("sage", "xboard", "unknown", 2325, NO_AUTO_DETECT, None),
    ENGINE("chezzz", "xboard", "dk", 2321, NO_AUTO_DETECT, None),
    ENGINE("mediocre", "uci", "se", 2320, NO_AUTO_DETECT, None),
    # isa (name too short)
    ENGINE("absolute-zero", "uci", "zh", 2346, NO_AUTO_DETECT, None),
    ENGINE("aice", "xboard", "gr", 2315, NO_AUTO_DETECT, None),
    ENGINE("sungorus", "uci", "es", 2313, NO_AUTO_DETECT, None),
    ENGINE("nebiyu", "xboard", "et", 2310, NO_AUTO_DETECT, None),  # wine crash on Ubuntu 1804 with NebiyuAlien.exe
    ENGINE("asterisk", "uci", "hu", 2307, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("averno", "xboard", "es", 2307, NO_AUTO_DETECT, None),
    ENGINE("joker", "xboard", "nl", 2305, NO_AUTO_DETECT, None),
    ENGINE("kingfisher", "uci", "hk", 2304, NO_AUTO_DETECT, None),
    ENGINE("tytan", "xboard", "pl", 2303, NO_AUTO_DETECT, None),
    ENGINE("resp", "xboard", "de", 2295, NO_AUTO_DETECT, None),
    ENGINE("ayito", "uci", "es", 2285, NO_AUTO_DETECT, None),  # Formerly XB
    ENGINE("chaturanga", "xboard", "it", 2272, NO_AUTO_DETECT, None),
    ENGINE("matilde", "xboard", "it", 2281, NO_AUTO_DETECT, None),
    ENGINE("fischerle", "uci", "de", 2281, NO_AUTO_DETECT, None),
    ENGINE("rival", "uci", "gb", 2271, NO_AUTO_DETECT, None),
    ENGINE("ct800", "uci", "de", 2393, NO_AUTO_DETECT, None),
    ENGINE("paladin", "uci", "in", 2271, NO_AUTO_DETECT, None),
    # esc (name too short)
    ENGINE("scidlet", "xboard", "nz", 2266, NO_AUTO_DETECT, None),
    ENGINE("butcher", "xboard", "pl", 2263, NO_AUTO_DETECT, None),
    ENGINE("zeus", "xboard", "ru", 2262, NO_AUTO_DETECT, None),
    ENGINE("natwarlal", "xboard", "in", 2260, NO_AUTO_DETECT, None),
    # doctor (unknown protocol)
    ENGINE("kmtchess", "xboard", "es", 2259, NO_AUTO_DETECT, None),
    ENGINE("firefly", "uci", "hk", 2251, NO_AUTO_DETECT, None),
    ENGINE("robocide", "uci", "gb", 2250, NO_AUTO_DETECT, None),
    ENGINE("napoleon", "uci", "it", 2253, NO_AUTO_DETECT, None),
    ENGINE("spacedog", "uci", "uk", 2242, NO_AUTO_DETECT, None),  # Allows XB
    # ant (name too short)
    ENGINE("anechka", "uci", "ru", 2233, NO_AUTO_DETECT, None),
    ENGINE("gopher_check", "uci", "us", 2234, NO_AUTO_DETECT, None),
    ENGINE("dorpsgek", "xboard", "en", 2230, NO_AUTO_DETECT, None),
    ENGINE("alichess", "uci", "de", 2228, NO_AUTO_DETECT, None),
    ENGINE("obender", "xboard", "ru", 2222, NO_AUTO_DETECT, None),
    ENGINE("joker2", "uci", "it", 2222, NO_AUTO_DETECT, None),
    ENGINE("adam", "xboard", "fr", 2220, NO_AUTO_DETECT, None),
    ENGINE("ramjet", "uci", "it", 2216, NO_AUTO_DETECT, None),
    ENGINE("exacto", "xboard", "us", 2217, NO_AUTO_DETECT, None),
    ENGINE("buzz", "xboard", "us", 2214, NO_AUTO_DETECT, None),
    ENGINE("chessalex", "uci", "ru", 2207, NO_AUTO_DETECT, None),
    ENGINE("chispa", "uci", "ar", 2206, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("beowulf", "xboard", "gb", 2203, NO_AUTO_DETECT, None),
    ENGINE("weini", "xboard", "fr", 2206, NO_AUTO_DETECT, None),  # Allows UCI
    ENGINE("rattate", "xboard", "it", 2197, NO_AUTO_DETECT, None),
    ENGINE("latista", "xboard", "us", 2195, NO_AUTO_DETECT, None),
    ENGINE("sinobyl", "xboard", "us", 2195, NO_AUTO_DETECT, None),
    ENGINE("ng-play", "xboard", "gr", 2194, NO_AUTO_DETECT, None),
    ENGINE("feuerstein", "uci", "de", 2192, NO_AUTO_DETECT, None),
    ENGINE("neurosis", "xboard", "nl", 2188, NO_AUTO_DETECT, None),
    # uralochka (blacklisted)
    ENGINE("mango", "xboard", "ve", 2185, NO_AUTO_DETECT, None),
    ENGINE("atak", "xboard", "pl", 2184, NO_AUTO_DETECT, None),
    ENGINE("madeleine", "uci", "it", 2183, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("mora", "uci", "ar", 2183, NO_AUTO_DETECT, None),
    ENGINE("sjaakii", "xboard", "nl", 2176, NO_AUTO_DETECT, None),
    ENGINE("protej", "uci", "it", 2175, NO_AUTO_DETECT, None),
    ENGINE("baislicka", "uci", "unknown", 2177, NO_AUTO_DETECT, None),
    ENGINE("achillees", "uci", "es", 2173, NO_AUTO_DETECT, None),
    ENGINE("genesis", "xboard", "il", 2170, NO_AUTO_DETECT, None),
    ENGINE("blackbishop", "uci", "de", 2163, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("inmichess", "xboard", "at", 2161, NO_AUTO_DETECT, None),
    ENGINE("kurt", "xboard", "de", 2162, NO_AUTO_DETECT, None),
    ENGINE("blitzkrieg", "uci", "in", 2161, NO_AUTO_DETECT, None),
    ENGINE("nagaskaki", "xboard", "za", 2156, NO_AUTO_DETECT, None),
    ENGINE("raven", "uci", "gb", 2429, NO_AUTO_DETECT, None),
    ENGINE("chesley", "xboard", "us", 2148, NO_AUTO_DETECT, None),
    ENGINE("alarm", "xboard", "se", 2144, NO_AUTO_DETECT, None),
    ENGINE("lime", "uci", "gb", 2143, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("hedgehog", "uci", "ru", 2141, NO_AUTO_DETECT, None),
    ENGINE("sunsetter", "xboard", "de", 2143, NO_AUTO_DETECT, None),
    ENGINE("chesskiss", "xboard", "unknown", 2137, NO_AUTO_DETECT, None),
    ENGINE("fortress", "xboard", "it", 2136, NO_AUTO_DETECT, None),
    ENGINE("tinychess", "uci", "unknown", 2136, NO_AUTO_DETECT, None),
    ENGINE("nesik", "xboard", "pl", 2133, NO_AUTO_DETECT, None),
    ENGINE("wjchess", "uci", "fr", 2130, NO_AUTO_DETECT, None),
    ENGINE("prophet", "xboard", "us", 2125, NO_AUTO_DETECT, None),
    ENGINE("uragano", "xboard", "it", 2131, NO_AUTO_DETECT, None),
    ENGINE("clever-girl", "uci", "us", 2117, NO_AUTO_DETECT, None),
    # merlin (no information)
    ENGINE("embla", "uci", "nl", 2115, NO_AUTO_DETECT, None),
    ENGINE("little-wing", "uci", "fr", 2106, NO_AUTO_DETECT, None),  # Allows XB
    # gk (name too short)
    ENGINE("knockout", "xboard", "de", 2108, NO_AUTO_DETECT, None),
    # alf (name too short)
    ENGINE("bikjump", "uci", "nl", 2102, NO_AUTO_DETECT, None),
    ENGINE("micah", "", "nl", 2106, NO_AUTO_DETECT, None),
    ENGINE("wing", "xboard", "nl", 2101, NO_AUTO_DETECT, None),
    ENGINE("clarabit", "uci", "es", 2096, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("adroitchess", "uci", "gb", 2071, NO_AUTO_DETECT, None),
    ENGINE("parrot", "xboard", "us", 2077, NO_AUTO_DETECT, None),
    ENGINE("abbess", "xboard", "us", 2072, NO_AUTO_DETECT, None),
    ENGINE("crabby", "uci", "us", 2063, NO_AUTO_DETECT, None),
    ENGINE("gunborg", "uci", "unknown", 2069, NO_AUTO_DETECT, None),
    ENGINE("alcibiades", "uci", "bg", 2065, NO_AUTO_DETECT, None),
    ENGINE("cinnamon", "uci", "it", 2070, NO_AUTO_DETECT, None),
    ENGINE("smash", "uci", "it", 2062, NO_AUTO_DETECT, None),
    ENGINE("chessmind", "uci", "de", 2056, NO_AUTO_DETECT, None),
    ENGINE("matheus", "uci", "br", 2058, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("potato", "xboard", "at", 2058, NO_AUTO_DETECT, None),
    ENGINE("honzovy", "uci", "cz", 2056, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("monarch", "uci", "gb", 2058, NO_AUTO_DETECT, None),
    ENGINE("dolphin", "xboard", "vn", 2055, NO_AUTO_DETECT, None),  # File manager
    ENGINE("kingsout", "xboard", "de", 2055, NO_AUTO_DETECT, None),
    ENGINE("bodo", "uci", "au", 2055, NO_AUTO_DETECT, None),
    ENGINE("rdchess", "xboard", "at", 2048, NO_AUTO_DETECT, None),
    ENGINE("gerbil", "xboard", "us", 2043, NO_AUTO_DETECT, None),
    ENGINE("vice", "uci", "unknown", 2044, NO_AUTO_DETECT, None),  # Both UCI/XBoard
    # ax (name too short)
    ENGINE("jabba", "uci", "gb", 2034, NO_AUTO_DETECT, None),
    # plp (name too short)
    ENGINE("prochess", "uci", "it", 2029, NO_AUTO_DETECT, None),
    # zct (name too short)
    ENGINE("zetadva", "xboard", "de", 2023, NO_AUTO_DETECT, None),
    ENGINE("bestia", "xboard", "ua", 2019, NO_AUTO_DETECT, None),
    ENGINE("bismark", "uci", "il", 2011, NO_AUTO_DETECT, None),
    ENGINE("plywood", "xboard", "unknown", 2020, NO_AUTO_DETECT, None),
    ENGINE("ecce", "uci", "ru", 2016, NO_AUTO_DETECT, None),
    ENGINE("cupcake", "xboard", "us", 2016, NO_AUTO_DETECT, None),
    ENGINE("delphimax", "uci", "de", 2013, NO_AUTO_DETECT, None),
    ENGINE("oberon", "xboard", "pl", 2012, NO_AUTO_DETECT, None),
    # schola (no information)
    ENGINE("freyr", "xboard", "ro", 2014, NO_AUTO_DETECT, None),
    ENGINE("ceibo", "uci", "ar", 1996, NO_AUTO_DETECT, None),
    ENGINE("leonidas", "xboard", "nl", 2006, NO_AUTO_DETECT, None),
    ENGINE("requiem", "xboard", "fi", 2008, NO_AUTO_DETECT, None),
    ENGINE("chess4j", "xboard", "us", 1989, NO_AUTO_DETECT, None),
    ENGINE("squared-chess", "uci", "de", 1996, NO_AUTO_DETECT, None),
    ENGINE("wowl", "uci", "de", 1995, NO_AUTO_DETECT, None),
    ENGINE("gullydeckel", "xboard", "de", 1992, NO_AUTO_DETECT, None),
    ENGINE("goldfish", "uci", "no", 1995, NO_AUTO_DETECT, None),
    ENGINE("elephant", "xboard", "de", 1985, NO_AUTO_DETECT, None),
    ENGINE("arabian-knight", "xboard", "pl", 1987, NO_AUTO_DETECT, None),
    ENGINE("biglion", "uci", "cm", 1986, NO_AUTO_DETECT, None),
    ENGINE("armageddon", "xboard", "pl", 1985, NO_AUTO_DETECT, None),
    ENGINE("bubble", "uci", "br", 1987, NO_AUTO_DETECT, None),
    ENGINE("snowy", "uci", "us", 1982, NO_AUTO_DETECT, None),
    ENGINE("faile", "xboard1", "ca", 1978, NO_AUTO_DETECT, None),
    ENGINE("slibo", "xboard", "de", 1973, NO_AUTO_DETECT, None),
    ENGINE("matant", "xboard", "pl", 1981, NO_AUTO_DETECT, None),
    ENGINE("ladameblanche", "xboard", "fr", 1966, NO_AUTO_DETECT, None),
    ENGINE("monik", "xboard", "unknown", 1967, NO_AUTO_DETECT, None),
    ENGINE("sissa", "uci", "fr", 1967, NO_AUTO_DETECT, None),
    ENGINE("ssechess", "xboard", "us", 1967, NO_AUTO_DETECT, None),
    ENGINE("jacksprat", "xboard", "unknown", 1954, NO_AUTO_DETECT, None),
    ENGINE("alchess", "uci", "ru", 1959, NO_AUTO_DETECT, None),
    # eia (name too short)
    # bsc (name too short)
    ENGINE("cilian", "xboard", "ch", 1959, NO_AUTO_DETECT, None),
    # franky (no information)
    ENGINE("mustang", "xboard", "by", 1961, NO_AUTO_DETECT, None),
    ENGINE("adachess", "xboard", "it", 1954, NO_AUTO_DETECT, None),
    ENGINE("micromax", "xboard", "nl", 1954, NO_AUTO_DETECT, None),
    ENGINE("umax", "xboard", "nl", 1954, NO_AUTO_DETECT, None),
    ENGINE("etude", "uci", "us", 1951, NO_AUTO_DETECT, None),
    ENGINE("wuttang", "uci", "in", 1958, NO_AUTO_DETECT, None),
    ENGINE("janwillem", "xboard", "nl", 1951, NO_AUTO_DETECT, None),
    ENGINE("pleco", "uci", "us", 1948, NO_AUTO_DETECT, None),
    ENGINE("sharper", "xboard", "se", 1940, NO_AUTO_DETECT, None),
    ENGINE("sapeli", "uci", "fi", 1975, NO_AUTO_DETECT, None),
    ENGINE("bell", "xboard", "fr", 1935, NO_AUTO_DETECT, None),
    ENGINE("bibichess", "uci", "fr", 1927, NO_AUTO_DETECT, None),
    ENGINE("smirf", "xboard", "de", 1924, NO_AUTO_DETECT, None),
    ENGINE("heracles", "uci", "fr", 1924, NO_AUTO_DETECT, None),
    ENGINE("samchess", "xboard", "us", 1919, NO_AUTO_DETECT, None),
    ENGINE("iach", "xboard", "unknown", 1917, NO_AUTO_DETECT, None),
    ENGINE("bambam", "xboard", "at", 1913, NO_AUTO_DETECT, None),
    ENGINE("tony", "xboard", "ca", 1910, NO_AUTO_DETECT, None),
    ENGINE("eagle", "uci", "uci", 1912, NO_AUTO_DETECT, None),
    ENGINE("reger", "xboard", "nl", 1911, NO_AUTO_DETECT, None),
    ENGINE("claudia", "uci", "es", 1904, NO_AUTO_DETECT, None),
    ENGINE("dabbaba", "xboard", "dk", 1906, NO_AUTO_DETECT, None),
    ENGINE("warrior", "xboard", "lv", 1907, NO_AUTO_DETECT, None),
    ENGINE("clueless", "uci", "de", 1903, NO_AUTO_DETECT, None),
    ENGINE("morphy", "xboard", "us", 1902, NO_AUTO_DETECT, None),
    ENGINE("zeta", "xboard", "me", 1894, NO_AUTO_DETECT, None),
    ENGINE("snailchess", "xboard", "sg", 1894, NO_AUTO_DETECT, None),
    ENGINE("surprise", "xboard", "de", 1888, NO_AUTO_DETECT, None),
    ENGINE("tyrell", "uci", "us", 1886, NO_AUTO_DETECT, None),
    ENGINE("matmoi", "xboard", "ca", 1888, NO_AUTO_DETECT, None),
    ENGINE("purplehaze", "xboard", "fr", 1884, NO_AUTO_DETECT, None),
    ENGINE("mrchess", "xboard", "sg", 1882, NO_AUTO_DETECT, None),
    # freechess (blacklisted)
    ENGINE("presbyter", "uci", "unknown", 1870, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("simontacchi", "uci", "us", 1862, NO_AUTO_DETECT, None),
    ENGINE("butter", "uci", "unknown", 1856, NO_AUTO_DETECT, None),
    ENGINE("roce", "uci", "ch", 1853, NO_AUTO_DETECT, None),
    ENGINE("deepov", "uci", "fr", 1850, NO_AUTO_DETECT, None),
    ENGINE("ranita", "uci", "fr", 1841, NO_AUTO_DETECT, None),
    ENGINE("sayuri", "uci", "jp", 1837, NO_AUTO_DETECT, None),
    ENGINE("milady", "xboard", "fr", 1834, NO_AUTO_DETECT, None),
    ENGINE("skiull", "uci", "ve", 1832, NO_AUTO_DETECT, None),
    ENGINE("halogen", "uci", "au", 2062, NO_AUTO_DETECT, None),
    ENGINE("heavychess", "uci", "ar", 1831, NO_AUTO_DETECT, None),
    ENGINE("ajedreztactico", "xboard", "mx", 1830, NO_AUTO_DETECT, None),
    ENGINE("celes", "uci", "nl", 1960, NO_AUTO_DETECT, None),
    ENGINE("jars", "xboard", "fr", 1823, NO_AUTO_DETECT, None),
    ENGINE("ziggurat", "uci", "us", 1810, NO_AUTO_DETECT, None),
    ENGINE("rataaeroespacial", "xboard", "ar", 1816, NO_AUTO_DETECT, None),
    ENGINE("noonian", "uci", "us", 1807, NO_AUTO_DETECT, None),
    ENGINE("predateur", "uci", "fr", 1811, NO_AUTO_DETECT, None),
    ENGINE("chenard", "xboard", "us", 1808, NO_AUTO_DETECT, None),
    ENGINE("morphychess", "xboard", "us", 1855, NO_AUTO_DETECT, None),
    ENGINE("beaches", "xboard", "us", 1797, NO_AUTO_DETECT, None),
    ENGINE("macromix", "uci", "ua", 1801, NO_AUTO_DETECT, None),
    ENGINE("pigeon", "uci", "ca", 1799, NO_AUTO_DETECT, None),
    ENGINE("chessterfield", "xboard", "ch", 1808, NO_AUTO_DETECT, None),
    ENGINE("cdrill", "uci", "unknown", 1798, NO_AUTO_DETECT, None),
    ENGINE("hoichess", "xboard", "de", 1791, NO_AUTO_DETECT, None),
    ENGINE("bremboce", "xboard", "it", 1780, NO_AUTO_DETECT, None),
    ENGINE("enigma", "xboard", "pl", 1789, NO_AUTO_DETECT, None),
    ENGINE("mobmat", "uci", "us", 1783, NO_AUTO_DETECT, None),
    ENGINE("grizzly", "xboard", "de", 1787, NO_AUTO_DETECT, None),
    ENGINE("embracer", "xboard", "se", 1785, NO_AUTO_DETECT, None),
    ENGINE("cecir", "xboard", "uy", 1780, NO_AUTO_DETECT, None),
    ENGINE("fauce", "xboard", "it", 1781, NO_AUTO_DETECT, None),
    ENGINE("berochess", "uci", "de", 1772, NO_AUTO_DETECT, None),
    ENGINE("apollo", "uci", "us", 1764, NO_AUTO_DETECT, None),
    ENGINE("pulsar", "xboard", "us", 1768, NO_AUTO_DETECT, None),
    ENGINE("mint", "xboard", "se", 1763, NO_AUTO_DETECT, None),
    ENGINE("robin", "xboard", "pl", 1761, NO_AUTO_DETECT, None),
    ENGINE("lodocase", "xboard", "be", 1758, NO_AUTO_DETECT, None),
    ENGINE("laurifer", "xboard", "pl", 1764, NO_AUTO_DETECT, None),
    ENGINE("rocinante", "uci", "es", 1745, NO_AUTO_DETECT, None),
    ENGINE("ziggy", "uci", "is", 1743, NO_AUTO_DETECT, None),
    ENGINE("vicki", "xboard", "za", 1741, NO_AUTO_DETECT, None),
    # elf (name too short)
    ENGINE("shallowblue", "uci", "ca", 1728, NO_AUTO_DETECT, None),
    ENGINE("kanguruh", "xboard", "at", 1734, NO_AUTO_DETECT, None),
    ENGINE("adamant", "xboard", "ru", 1733, NO_AUTO_DETECT, None),
    ENGINE("foxsee", "uci", "cn", 2147, NO_AUTO_DETECT, None),
    ENGINE("gchess", "xboard", "it", 1732, NO_AUTO_DETECT, None),
    ENGINE("zzzzzz", "xboard", "nl", 1729, NO_AUTO_DETECT, None),
    ENGINE("jaksah", "uci", "rs", 1725, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("kitteneitor", "xboard", "es", 1722, NO_AUTO_DETECT, None),
    ENGINE("tscp", "xboard", "us", 1724, NO_AUTO_DETECT, None),
    ENGINE("zoidberg", "xboard", "es", 1722, NO_AUTO_DETECT, None),
    # see (name too short)
    ENGINE("tristram", "xboard", "us", 1720, NO_AUTO_DETECT, None),
    ENGINE("enkochess", "uci", "unknown", 1716, NO_AUTO_DETECT, None),
    ENGINE("aldebaran", "xboard", "it", 1711, NO_AUTO_DETECT, None),
    ENGINE("testina", "uci", "it", 1697, NO_AUTO_DETECT, None),
    ENGINE("celestial", "uci", "au", 1695, NO_AUTO_DETECT, None),
    ENGINE("jester", "xboard", "us", 1693, NO_AUTO_DETECT, None),
    # chess (name too generic)
    ENGINE("sharpchess", "xboard", "unknown", 1690, NO_AUTO_DETECT, None),
    ENGINE("gargamella", "xboard", "it", 1684, NO_AUTO_DETECT, None),
    ENGINE("chengine", "xboard", "jp", 1683, NO_AUTO_DETECT, None),
    ENGINE("mizar", "xboard", "it", 1682, NO_AUTO_DETECT, None),
    ENGINE("polarchess", "xboard", "no", 1675, NO_AUTO_DETECT, None),
    ENGINE("bace", "xboard", "us", 1675, NO_AUTO_DETECT, None),
    ENGINE("golem", "xboard", "it", 1671, NO_AUTO_DETECT, None),
    ENGINE("tom-thumb", "uci", "nl", 1664, NO_AUTO_DETECT, None),
    ENGINE("belzebub", "xboard", "pl", 1662, NO_AUTO_DETECT, None),
    ENGINE("pooky", "uci", "us", 1655, NO_AUTO_DETECT, None),
    ENGINE("koedem", "uci", "de", 1831, NO_AUTO_DETECT, None),
    ENGINE("dchess", "xboard", "us", 1652, NO_AUTO_DETECT, None),
    ENGINE("simon", "xboard", "us", 1646, NO_AUTO_DETECT, None),
    ENGINE("spartan", "uci", "unknown", 1635, NO_AUTO_DETECT, None),
    ENGINE("vapor", "uci", "us", 1642, NO_AUTO_DETECT, None),
    ENGINE("iq23", "uci", "de", 1640, NO_AUTO_DETECT, None),
    ENGINE("pulse", "uci", "ch", 1637, NO_AUTO_DETECT, None),
    ENGINE("chessrikus", "xboard", "us", 1631, NO_AUTO_DETECT, None),
    ENGINE("mscp", "xboard", "nl", 1632, NO_AUTO_DETECT, None),
    ENGINE("storm", "xboard", "us", 1628, NO_AUTO_DETECT, None),
    ENGINE("monochrome", "uci", "unknown", 1619, NO_AUTO_DETECT, None),
    ENGINE("jsbam", "xboard", "nl", 1621, NO_AUTO_DETECT, None),
    ENGINE("saruman", "uci", "unknown", 1620, NO_AUTO_DETECT, None),
    ENGINE("revati", "uci", "de", 1618, NO_AUTO_DETECT, None),
    ENGINE("kasparov", "uci", "ca", 1615, NO_AUTO_DETECT, None),
    ENGINE("philemon", "uci", "ch", 1612, NO_AUTO_DETECT, None),
    ENGINE("bullitchess", "uci", "unknown", 1609, NO_AUTO_DETECT, None),
    ENGINE("rainman", "xboard", "se", 1606, NO_AUTO_DETECT, None),
    ENGINE("marginal", "uci", "ru", 1565, NO_AUTO_DETECT, None),
    ENGINE("zotron", "xboard", "us", 1592, NO_AUTO_DETECT, None),
    ENGINE("violet", "uci", "unknown", 1592, NO_AUTO_DETECT, None),
    ENGINE("casper", "uci", "gb", 1585, NO_AUTO_DETECT, None),
    ENGINE("darky", "uci", "mx", 1588, NO_AUTO_DETECT, None),
    ENGINE("dreamer", "xboard", "nl", 1583, NO_AUTO_DETECT, None),
    ENGINE("needle", "xboard", "fi", 1580, NO_AUTO_DETECT, None),
    ENGINE("damas", "xboard", "br", 1583, NO_AUTO_DETECT, None),
    ENGINE("sdbc", "xboard", "de", 1577, NO_AUTO_DETECT, None),
    ENGINE("vanilla", "xboard", "au", 1569, NO_AUTO_DETECT, None),
    ENGINE("cicada", "uci", "us", 1575, NO_AUTO_DETECT, None),
    ENGINE("hokus", "xboard", "pl", 1550, NO_AUTO_DETECT, None),
    ENGINE("mace", "uci", "de", 1546, NO_AUTO_DETECT, None),
    ENGINE("larsen", "xboard", "it", 1542, NO_AUTO_DETECT, None),
    ENGINE("trappist", "uci", "unknown", 1536, NO_AUTO_DETECT, None),
    ENGINE("yawce", "xboard", "dk", 1517, NO_AUTO_DETECT, None),
    ENGINE("supra", "uci", "pt", 1507, NO_AUTO_DETECT, None),
    ENGINE("piranha", "uci", "de", 1500, NO_AUTO_DETECT, None),
    ENGINE("alibaba", "uci", "nl", 1498, NO_AUTO_DETECT, None),
    ENGINE("apep", "xboard", "us", 1477, NO_AUTO_DETECT, None),
    ENGINE("tarrasch", "uci", "us", 1492, NO_AUTO_DETECT, None),
    ENGINE("andersen", "xboard", "se", 1486, NO_AUTO_DETECT, None),
    ENGINE("pwned", "uci", "us", 1484, NO_AUTO_DETECT, None),
    ENGINE("apil", "xboard", "de", 1482, NO_AUTO_DETECT, None),
    ENGINE("pentagon", "xboard", "it", 1479, NO_AUTO_DETECT, None),
    ENGINE("gedeone", "xboard", "unknown", 1476, NO_AUTO_DETECT, None),
    ENGINE("roque", "xboard", "es", 1467, NO_AUTO_DETECT, None),
    ENGINE("numpty", "xboard", "gb", 1465, NO_AUTO_DETECT, None),
    ENGINE("blikskottel", "xboard", "za", 1460, NO_AUTO_DETECT, None),
    ENGINE("hactar", "uci", "de", 1434, NO_AUTO_DETECT, None),
    ENGINE("nero", "xboard", "de", 1448, NO_AUTO_DETECT, None),
    ENGINE("suff", "uci", "at", 1422, NO_AUTO_DETECT, None),
    ENGINE("sabrina", "xboard", "it", 1415, NO_AUTO_DETECT, None),
    ENGINE("quokka", "uci", "us", 1413, NO_AUTO_DETECT, None),
    ENGINE("minimardi", "xboard", "unknown", 1412, NO_AUTO_DETECT, None),
    ENGINE("satana", "xboard", "it", 1407, NO_AUTO_DETECT, None),
    ENGINE("eden", "uci", "de", 1404, NO_AUTO_DETECT, None),
    ENGINE("goyaz", "xboard", "br", 1416, NO_AUTO_DETECT, None),
    ENGINE("jchess", "xboard", "pl", 1408, NO_AUTO_DETECT, None),
    ENGINE("nanook", "uci", "fr", 1389, NO_AUTO_DETECT, None),
    ENGINE("skaki", "xboard", "us", 1386, NO_AUTO_DETECT, None),
    ENGINE("virutor", "uci", "cz", 1363, NO_AUTO_DETECT, None),
    ENGINE("minichessai", "xboard", "pl", 1366, NO_AUTO_DETECT, None),
    ENGINE("joanna", "xboard", "pl", 1345, NO_AUTO_DETECT, None),
    ENGINE("gladiator", "xboard", "es", 1340, NO_AUTO_DETECT, None),
    ENGINE("ozwald", "xboard", "fi", 1342, NO_AUTO_DETECT, None),
    ENGINE("fimbulwinter", "xboard", "us", 1318, NO_AUTO_DETECT, None),
    ENGINE("cerulean", "xboard", "ca", 1287, NO_AUTO_DETECT, None),
    ENGINE("killerqueen", "uci", "it", 1289, NO_AUTO_DETECT, None),
    ENGINE("trex", "uci", "fr", 1289, NO_AUTO_DETECT, None),
    # chess (name too generic)
    ENGINE("qutechess", "uci", "si", 1274, NO_AUTO_DETECT, None),
    ENGINE("ronja", "xboard", "se", 1270, NO_AUTO_DETECT, None),
    ENGINE("tikov", "uci", "gb", 1245, NO_AUTO_DETECT, None),
    ENGINE("raffaela", "xboard", "it", 1231, NO_AUTO_DETECT, None),
    ENGINE("dragontooth", "uci", "us", 1236, NO_AUTO_DETECT, None),
    ENGINE("gringo", "xboard", "at", 1231, NO_AUTO_DETECT, None),  # gringo - grounding tools for (disjunctive) logic programs
    ENGINE("pierre", "xboard", "ca", 1236, NO_AUTO_DETECT, None),
    ENGINE("toledo-uci", "uci", "mx", 1225, NO_AUTO_DETECT, 5),
    ENGINE("toledo", "xboard", "mx", 1225, NO_AUTO_DETECT, None),
    ENGINE("neurone", "xboard", "it", 1219, NO_AUTO_DETECT, None),
    ENGINE("gray-matter", "xboard", "unknown", 1162, NO_AUTO_DETECT, None),
    ENGINE("enxadrista", "xboard", "br", 1195, NO_AUTO_DETECT, None),
    ENGINE("darkfusch", "uci", "de", 1185, NO_AUTO_DETECT, None),
    ENGINE("project-invincible", "xboard", "fi", 1288, NO_AUTO_DETECT, None),
    ENGINE("cassandre", "uci", "fr", 1151, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("jchecs", "xboard", "fr", 1142, NO_AUTO_DETECT, None),
    ENGINE("brama", "xboard", "it", 1137, NO_AUTO_DETECT, None),
    ENGINE("soberango", "xboard", "ar", 1135, NO_AUTO_DETECT, None),
    ENGINE("usurpator", "xboard", "nl", 1129, NO_AUTO_DETECT, None),
    ENGINE("blitzter", "xboard", "de", 1080, NO_AUTO_DETECT, None),
    ENGINE("strategicdeep", "xboard", "pl", 1075, NO_AUTO_DETECT, None),
    ENGINE("frank", "xboard", "it", 1074, NO_AUTO_DETECT, None),
    ENGINE("talvmenni", "xboard", "fo", 1067, NO_AUTO_DETECT, None),
    ENGINE("minnow", "uci", "unknown", 1062, NO_AUTO_DETECT, None),
    ENGINE("xadreco", "xboard", "br", 1026, NO_AUTO_DETECT, None),
    ENGINE("safrad", "uci", "cz", 1025, NO_AUTO_DETECT, None),
    ENGINE("iota", "uci", "gb", 1037, NO_AUTO_DETECT, None),
    ENGINE("giuchess", "xboard", "it", 994, NO_AUTO_DETECT, None),
    ENGINE("belofte", "uci", "be", 1203, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("kace", "xboard", "us", 992, NO_AUTO_DETECT, None),
    ENGINE("feeks", "uci", "nl", 967, NO_AUTO_DETECT, None),
    ENGINE("youk", "xboard", "fr", 966, NO_AUTO_DETECT, None),
    ENGINE("nsvchess", "uci", "fr", 946, NO_AUTO_DETECT, None),
    # zoe (name too short)
    ENGINE("chad", "uci", "xb", 941, NO_AUTO_DETECT, None),
    ENGINE("luzhin", "xboard", "unknown", 927, NO_AUTO_DETECT, None),
    ENGINE("hippocampe", "xboard", "fr", 873, NO_AUTO_DETECT, None),
    ENGINE("pyotr", "xboard", "gr", 882, NO_AUTO_DETECT, None),
    ENGINE("dika", "xboard", "fr", 857, NO_AUTO_DETECT, None),
    ENGINE("chessputer", "uci", "unknown", 843, NO_AUTO_DETECT, None),
    ENGINE("alouette", "uci", "fr", 753, NO_AUTO_DETECT, None),
    # easypeasy (no information)
    ENGINE("acquad", "uci", "it", 777, NO_AUTO_DETECT, None),
    ENGINE("acqua", "uci", "it", 617, NO_AUTO_DETECT, None),
    # neg (name too short)
    # ram (name too short)
    ENGINE("cpp1", "xboard", "nl", 458, NO_AUTO_DETECT, None),
    # pos (name too short)
    ENGINE("lamosca", "xboard", "it", 371, NO_AUTO_DETECT, None),
    # ace (name too short)
    ENGINE("sxrandom", "uci", "cz", 218, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("combusken", "uci", "pl", 3175, NO_AUTO_DETECT, None),
    ENGINE("noc", "", "es", 2491, NO_AUTO_DETECT, None),  # noc (name too short)
    ENGINE("wasabi", "uci", "de", 2348, NO_AUTO_DETECT, None),
    ENGINE("kingfisher", "uci", "de", 2305, NO_AUTO_DETECT, None),
    ENGINE("ceechess", "uci", "us", 2245, NO_AUTO_DETECT, None),  # Allows XB
    ENGINE("stash", "uci", "fr", 2230, NO_AUTO_DETECT, None),
    ENGINE("brainless", "xboard", "unknown", 2138, NO_AUTO_DETECT, None),
    ENGINE("magic", "xboard", "cn", 2025, NO_AUTO_DETECT, None),
    ENGINE("chessv", "xboard", "us", 1996, NO_AUTO_DETECT, None),  # A lot of chess variants
    ENGINE("tinman", "xboard", "us", 1880, NO_AUTO_DETECT, None),
    ENGINE("gearheart", "uci", "us", 1789, NO_AUTO_DETECT, None),
    # chancellor (no information)
    ENGINE("clownfish", "xboard", "it", 1566, NO_AUTO_DETECT, None),
    ENGINE("eubos", "uci", "gb", 1454, NO_AUTO_DETECT, None),
    # thelightning (no information)
    ENGINE("irina", "uci", "unknown", 1437, NO_AUTO_DETECT, None),
    ENGINE("cefap", "xboard", "se", 1372, NO_AUTO_DETECT, None),
    ENGINE("sargon", "uci", "us", 1256, NO_AUTO_DETECT, None),
    ENGINE("robokewlper", "xboard", "us", 1062, NO_AUTO_DETECT, None),

    # -- Other (parent engine, derivative work, unlisted, variant engine...)
    ENGINE("s_pro", "uci", "it", 3540, NO_AUTO_DETECT, None),
    ENGINE("asmfish", "uci", "bg", 3531, NO_AUTO_DETECT, None),
    ENGINE("glaurung", "uci", "no", 2915, AUTO_DETECT, None),
    ENGINE("amundsen", "xboard", "se", 0, NO_AUTO_DETECT, None),
    ENGINE("anticrux", "uci", "fr", 0, NO_AUTO_DETECT, 10),
    ENGINE("fairymax", "xboard", "nl", 0, AUTO_DETECT, None),
    ENGINE("fruit", "uci", "fr", 2783, AUTO_DETECT, None),
    ENGINE("sunfish", "xboard", "dk", 0, NO_AUTO_DETECT, None),
    ENGINE("democracy", "uci", "fr", 0, NO_AUTO_DETECT, None),
    ENGINE("worse-chess", "uci", "fr", 0, NO_AUTO_DETECT, None)
]


# Bubble sort by descending length of the name
for i in range(len(ENGINES_LIST) - 1, 1, - 1):
    for j in range(0, i - 1):
        if len(ENGINES_LIST[i].name) > len(ENGINES_LIST[j].name):
            tmp = ENGINES_LIST[i]
            ENGINES_LIST[i] = ENGINES_LIST[j]
            ENGINES_LIST[j] = tmp


# Mass detection of the engines (no recursion if maxDepth=0)
def listEnginesFromPath(defaultPath, maxDepth=3, withSymLink=False):
    # Base folders
    if defaultPath is None or defaultPath == "":
        base = os.getenv("PATH")
        maxDepth = 1
    else:
        base = defaultPath
    base = [os.path.join(p, "") for p in base.split(";")]

    # List the executable files
    found_engines = []
    depth_current = 1
    depth_next = len(base)
    for depth_loop, dir in enumerate(base):
        files = os.listdir(dir)
        for file in files:
            file_ci = file.lower()
            fullname = os.path.join(dir, file)

            # Recurse the folders by appending to the scanned list
            if os.path.isdir(fullname):
                if not withSymLink and os.path.islink(fullname):
                    continue
                if maxDepth > 0:
                    if depth_loop == depth_next:
                        depth_current += 1
                        depth_next = len(base)
                    if depth_current <= maxDepth:
                        base.append(os.path.join(dir, file, ""))
                continue

            # Blacklisted keywords
            blacklisted = False
            for kw in ["install", "setup", "reset", "remove", "delete", "clean", "purge", "config", "register", "editor", "book"]:
                if kw in file_ci:
                    blacklisted = True
                    break
            if blacklisted:
                continue

            # Check if the file is a supported scripting language, or an executable file
            executable = False
            for vm in VM_LIST:
                if file_ci.endswith(vm.ext):
                    executable = True
                    break
            if not executable:
                if cpu['windows']:
                    executable = file_ci.endswith(cpu['binext'])
                else:
                    executable = os.access(fullname, os.X_OK)
            if not executable:
                continue

            # Check the filename against the known list of engines
            found = False
            for engine in ENGINES_LIST:
                if engine.name in file_ci:
                    found = True
                    break
            if not found:
                continue

            # Check the bitness because x64 does not run on x32
            if cpu['bitness'] == "32" and "64" in file_ci:
                continue

            # Check the support for POPCNT
            if not cpu['popcnt'] and "popcnt" in file_ci:
                continue

            # Check the support for BMI2
            if not cpu['bmi2'] and "bmi2" in file_ci:
                continue

            # Great, this is an engine !
            found_engines.append(fullname)

    # Return the found engines as an array of full file names
    return found_engines
