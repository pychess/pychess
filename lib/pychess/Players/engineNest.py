from __future__ import absolute_import
from __future__ import print_function
import os
from os.path import join, dirname, abspath
import sys
import json
import platform
from functools import partial
from hashlib import md5
from threading import Thread, Lock
from copy import deepcopy

from gi.repository import GObject

from pychess.System import conf, fident
from pychess.System.Log import log
from pychess.System.command import Command
from pychess.System.SubProcess import SubProcess, searchPath, SubProcessError
from pychess.System.prefix import addUserConfigPrefix, getDataPrefix, getEngineDataPrefix
from pychess.Players.Player import PlayerIsDead
from pychess.Utils import createStoryTextAppEvent
from pychess.Utils.const import BLACK, UNKNOWN_REASON, SUBPROCESS_SUBPROCESS, WHITE, \
    HINT, ANALYZING, INVERSE_ANALYZING
from .CECPEngine import CECPEngine
from .UCIEngine import UCIEngine
from pychess.Variants import variants

attrToProtocol = {"uci": UCIEngine, "xboard": CECPEngine}

PYTHONBIN = sys.executable.split("/")[-1]
BITNESS = "64" if platform.machine().endswith('64') else "32"

if sys.platform == "win32":
    backup = [
        {"protocol": "uci",
         "name": "stockfish-7-%s.exe" % BITNESS,
         "country": "no"},
        {"protocol": "xboard",
         "name": "sjaakii_win%s_ms.exe" % BITNESS,
         "country": "nl"},
    ]
    if getattr(sys, 'frozen', False):
        backup.append({"protocol": "xboard",
                       "name": "pychess-engine",
                       "country": "dk"})
    else:
        backup.append({"protocol": "xboard",
                       "name": "PyChess.py",
                       "country": "dk",
                       "vm_name": PYTHONBIN,
                       "vm_args": ["-u"]})
else:
    backup = [
        {"protocol": "xboard",
         "name": "pychess-engine",
         "country": "dk"},
        {"protocol": "xboard",
         "name": "PyChess.py",
         "country": "dk",
         "vm_name": PYTHONBIN,
         "vm_args": ["-u"]},
        #    {"protocol": "xboard", "name": "shatranj.py", "country": "us",
        #        "vm_name": PYTHONBIN, "vm_args": ["-u"], "args": ["-xboard"]},
        {"protocol": "xboard",
         "name": "gnuchess",
         "country": "us"},
        {"protocol": "xboard",
         "name": "gnome-gnuchess",
         "country": "us"},
        {"protocol": "xboard",
         "name": "crafty",
         "country": "us"},
        {"protocol": "xboard",
         "name": "faile",
         "country": "ca",
         "protover": 1},
        {"protocol": "xboard",
         "name": "phalanx",
         "country": "cz",
         "protover": 1},
        {"protocol": "xboard",
         "name": "sjeng",
         "country": "be"},
        {"protocol": "xboard",
         "name": "hoichess",
         "country": "de"},
        {"protocol": "xboard",
         "name": "boochess",
         "country": "de",
         "protover": 1},
        {"protocol": "xboard",
         "name": "amy",
         "country": "de"},
        {"protocol": "xboard",
         "name": "amundsen",
         "country": "sw"},
        {"protocol": "uci",
         "name": "gnuchessu",
         "country": "us"},
        {"protocol": "uci",
         "name": "robbolito",
         "country": "ru"},
        {"protocol": "uci",
         "name": "glaurung",
         "country": "no"},
        {"protocol": "uci",
         "name": "stockfish",
         "country": "no"},
        {"protocol": "uci",
         "name": "ShredderClassicLinux",
         "country": "de"},
        {"protocol": "uci",
         "name": "fruit_21_static",
         "country": "fr"},
        {"protocol": "uci",
         "name": "fruit",
         "country": "fr"},
        {"protocol": "uci",
         "name": "toga2",
         "country": "de"},
        {"protocol": "uci",
         "name": "hiarcs",
         "country": "gb"},
        {"protocol": "uci",
         "name": "diablo",
         "country": "us"},
        {"protocol": "uci",
         "name": "Houdini.exe",
         "country": "be",
         "vm_name": "wine"},
        {"protocol": "uci",
         "name": "Rybka.exe",
         "country": "ru",
         "vm_name": "wine"},
    ]


def md5_sum(filename):
    with open(filename, mode='rb') as file_handle:
        md5sum = md5()
        for buf in iter(partial(file_handle.read, 4096), b''):
            md5sum.update(buf)
    return md5sum.hexdigest()


class EngineDiscoverer(GObject.GObject):

    __gsignals__ = {
        "discovering_started": (GObject.SignalFlags.RUN_FIRST, None,
                                (object, )),
        "engine_discovered": (GObject.SignalFlags.RUN_FIRST, None,
                              (str, object)),
        "engine_failed": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        "all_engines_discovered": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.engines = []
        self.jsonpath = addUserConfigPrefix("engines.json")
        try:
            self._engines = json.load(open(self.jsonpath))
        except ValueError as err:
            log.warning(
                "engineNest: Couldn\'t read engines.json, renamed it to .bak\n%s\n%s"
                % (self.jsonpath, err))
            os.rename(self.jsonpath, self.jsonpath + ".bak")
            self._engines = deepcopy(backup)
        except IOError as err:
            log.info(
                "engineNest: Couldn\'t open engines.json, creating a new.\n%s"
                % err)
            self._engines = deepcopy(backup)

        # Try to detect engines shipping .eng files on Linux (suggested by HGM on talkcess.com forum)
        for protocol in ("xboard", "uci"):
            for path in ("/usr/local/share/games/plugins",
                         "/usr/share/games/plugins"):
                path = os.path.join(path, protocol)
                if os.path.isdir(path):
                    for entry in os.listdir(path):
                        ext = os.path.splitext(entry)[1]
                        if ext == ".eng":
                            with open(os.path.join(path, entry)) as file_handle:
                                engine_command = file_handle.readline().strip()
                                new_engine = {}
                                if engine_command.startswith(
                                        "cd ") and engine_command.find(
                                            ";") > 0:
                                    parts = engine_command.split(";")
                                    working_directory = parts[0][3:]
                                    engine_command = parts[1]
                                    new_engine[
                                        "workingDirectory"] = working_directory

                                find = False
                                for engine in self._engines:
                                    if engine["name"] == engine_command:
                                        find = True
                                        break
                                if not find:
                                    new_engine["protocol"] = protocol
                                    new_engine["name"] = engine_command
                                    self._engines.append(new_engine)

                                    ############################################################################
                                    # Discover methods                                                         #
                                    ############################################################################

    def __findRundata(self, engine):
        """ Searches for a readable, executable named 'name' in the PATH.
            For the PyChess engine, special handling is taken, and we search
            PYTHONPATH as well as the directory from where the 'os' module is
            imported """
        if engine.get("vm_name") is not None:
            altpath = engine.get("vm_command")
            if getattr(sys, 'frozen', False) and engine["vm_name"] == "wine":
                vmpath = None
            else:
                vmpath = searchPath(engine["vm_name"],
                                    access=os.R_OK | os.X_OK,
                                    altpath=altpath)

            if engine["name"] == "PyChess.py" and not getattr(sys, 'frozen',
                                                              False):
                path = join(abspath(dirname(__file__)), "PyChess.py")
                if not os.access(path, os.R_OK):
                    path = None
            else:
                altpath = engine.get("command")
                path = searchPath(engine["name"],
                                  access=os.R_OK,
                                  altpath=altpath)

            if vmpath and path:
                return vmpath, path
            elif path and sys.platform == "win32" and engine.get(
                    "vm_name") == "wine":
                return None, path

        else:
            altpath = engine.get("command")
            if sys.platform == "win32" and not altpath:
                altpath = os.path.join(getDataPrefix(), "engines",
                                       engine["name"])
            path = searchPath(engine["name"],
                              access=os.R_OK | os.X_OK,
                              altpath=altpath)
            if path:
                return None, path
        return False

    def __fromUCIProcess(self, subprocess):
        ids = subprocess.ids
        options = subprocess.options
        engine = {}
        if 'author' in ids:
            engine['author'] = ids['author']
        if options:
            engine["options"] = list(options.values())
        return engine

    def __fromCECPProcess(self, subprocess):
        features = subprocess.features
        options = subprocess.options
        engine = {}
        if features['variants'] is not None:
            engine['variants'] = features['variants'].split(",")
        if features['analyze'] == 1:
            engine["analyze"] = True
        if options:
            engine["options"] = list(options.values())

        return engine

    def __discoverE(self, engine):
        subproc = self.initEngine(engine, BLACK)
        try:
            subproc.connect('readyForOptions', self.__discoverE2, engine)
            subproc.prestart()  # Sends the 'start line'
            subproc.start()
        except SubProcessError as err:
            log.warning("Engine %s failed discovery: %s" % (engine["name"], err))
            self.emit("engine_failed", engine["name"], engine)
        except PlayerIsDead as err:
            # Check if the player died after engine_discovered by our own hands
            if not self.toBeRechecked[engine["name"]][1]:
                log.warning("Engine %s failed discovery: %s" %
                            (engine["name"], err))
                self.emit("engine_failed", engine["name"], engine)

    def __discoverE2(self, subproc, engine):
        if engine.get("protocol") == "uci":
            fresh = self.__fromUCIProcess(subproc)
        elif engine.get("protocol") == "xboard":
            fresh = self.__fromCECPProcess(subproc)
        engine.update(fresh)

        exitcode = subproc.kill(UNKNOWN_REASON)
        if exitcode:
            log.debug("Engine failed %s" % engine["name"])
            self.emit("engine_failed", engine['name'], engine)
            return

        engine['recheck'] = False
        log.debug("Engine finished %s" % engine["name"])
        self.emit("engine_discovered", engine['name'], engine)

    ############################################################################
    # Main loop                                                                #
    ############################################################################

    def __needClean(self, rundata, engine):
        """ Check if the filename or md5sum of the engine has changed.
            In that case we need to clean the engine """

        path = rundata[1]

        # Check if filename is not set, or if it has changed
        if engine.get("command") is None or engine.get("command") != path:
            return True
        # If the engine failed last time, we'll recheck it as well
        if engine.get('recheck'):
            return True

        # Check if md5sum is not set, or if it has changed
        if engine.get("md5") is None:
            return True

        md5sum = md5_sum(path)
        if engine.get("md5") != md5sum:
            return True

        return False

    def __clean(self, rundata, engine):
        """ Grab the engine from the backup and attach the attributes
            from rundata. The update engine is ready for discovering.
        """

        vmpath, path = rundata

        md5sum = md5_sum(path)

        ######
        # Find the backup engine
        ######
        try:
            backup_engine = next((
                c for c in backup if c["name"] == engine["name"]))
            engine["country"] = backup_engine["country"]
        except StopIteration:
            log.warning(
                "Engine '%s' has not been tested and verified to work with PyChess" % engine.get('name'))
            engine['recheck'] = True

        ######
        # Clean it
        ######
        engine['command'] = path
        engine['md5'] = md5sum
        if vmpath is not None:
            engine['vm_command'] = vmpath
        if "variants" in engine:
            del engine["variants"]
        if "options" in engine:
            del engine["options"]

        ######
        # Save the xml
        ######
    def save(self, *args):
        try:
            with open(self.jsonpath, "w") as file_handle:
                json.dump(self._engines, file_handle, indent=1, sort_keys=True)
        except IOError as err:
            log.error("Saving engines.json raised exception: %s" %
                      ", ".join(str(a) for a in err.args))

    def discover(self):
        class Discoverer(Thread):
            def __init__(self, parent):
                Thread.__init__(self, name=fident(self.run))
                self.daemon = True
                self.parent = parent

            def run(self):
                self.parent.do_discover()

        dis_coverer = Discoverer(self)
        dis_coverer.start()

    def do_discover(self):
        self.engines = []
        # List available engines
        for engine in self._engines:
            # Find the known and installed engines on the system

            # Look up
            rundata = self.__findRundata(engine)
            if not rundata:
                # Engine is not available on the system
                continue

            if self.__needClean(rundata, engine):
                self.__clean(rundata, engine)
                engine['recheck'] = True

            self.engines.append(engine)
        ######
        # Runs all the engines in toBeRechecked, in order to gather information
        ######
        self.toBeRechecked = dict((c["name"], [c, False])
                                  for c in self._engines if c.get('recheck'))
        self.all_done_lock = Lock()

        def count(self_, name, engine, wentwell):
            with self.all_done_lock:
                if wentwell:
                    self.toBeRechecked[name][1] = True
                if all([elem[1] for elem in self.toBeRechecked.values()]):
                    self.engines.sort(key=lambda x: x["name"])
                    self.emit("all_engines_discovered")
                    createStoryTextAppEvent("all_engines_discovered")

        self.connect("engine_discovered", count, True)
        self.connect("engine_failed", count, False)
        if self.toBeRechecked:
            self.emit("discovering_started", self.toBeRechecked.keys())
            self.connect("all_engines_discovered", self.save)
            for engine, done in self.toBeRechecked.values():
                if not done:
                    self.__discoverE(engine)
        else:
            self.emit("all_engines_discovered")
            createStoryTextAppEvent("all_engines_discovered")

    ############################################################################
    # Interaction                                                              #
    ############################################################################

    def is_analyzer(self, engine):
        protocol = engine.get("protocol")
        if protocol == "uci":
            return True
        elif protocol == "xboard":
            return engine.get("analyze") is not None

    def getAnalyzers(self):
        return [engine
                for engine in self.getEngines() if self.is_analyzer(engine)]

    def getEngines(self):
        """ Returns list of engine dicts """
        return sorted(self.engines, key=lambda engine: engine["name"].lower())

    def getEngineN(self, index):
        return self.getEngines()[index]

    def getEngineByName(self, name):
        names = [engine["name"] for engine in self.getEngines()]
        return self.getEngines()[names.index(name)]

    def getEngineByMd5(self, md5sum, list=[]):
        if not list:
            list = self.getEngines()
        for engine in list:
            md5_check = engine.get('md5')
            if md5_check is None:
                continue
            if md5_check == md5sum:
                return engine

    def getEngineVariants(self, engine):
        for variantClass in variants.values():
            if variantClass.standard_rules:
                yield variantClass.variant
            else:
                if engine.get("variants"):
                    if variantClass.cecp_name in engine.get("variants"):
                        yield variantClass.variant
                # UCI knows Chess960 only
                if engine.get("options"):
                    for option in engine["options"]:
                        if option["name"] == "UCI_Chess960" and \
                                variantClass.cecp_name == "fischerandom":
                            yield variantClass.variant
                        elif option["name"] == "UCI_Variant":
                            if variantClass.cecp_name in option["choices"] or \
                                    variantClass.cecp_name.lower().replace("-", "") in option["choices"]:
                                yield variantClass.variant

    def getName(self, engine=None):
        # Test if the call was to get the name of the thread
        if engine is None:
            return Thread.getName(self)
        return engine["name"]

    def getCountry(self, engine):
        return engine.get("country")

    def initEngine(self, engine, color):
        name = engine['name']
        protocol = engine["protocol"]
        protover = 2 if engine.get("protover") is None else engine.get(
            "protover")
        path = engine['command']
        args = [] if engine.get('args') is None else [a
                                                      for a in engine['args']]
        if engine.get('vm_command') is not None:
            vmpath = engine['vm_command']
            vmargs = [] if engine.get('vm_args') is None else [
                a for a in engine['vm_args']
            ]
            args = vmargs + [path] + args
            path = vmpath
        md5_engine = engine['md5']

        working_directory = engine.get("workingDirectory")
        if working_directory:
            workdir = working_directory
        else:
            workdir = getEngineDataPrefix()
        warnwords = ("illegal", "error", "exception")
        subprocess = SubProcess(path, args, warnwords, SUBPROCESS_SUBPROCESS,
                                workdir)
        engine_proc = attrToProtocol[protocol](subprocess, color, protover,
                                               md5_engine)

        engine_proc.setName(name)

        # If the user has configured special options for this engine, here is
        # where they should be set.
        def optionsCallback(set_option):
            if engine.get("options"):
                for option in engine["options"]:
                    key = option["name"]
                    value = option.get("value")
                    if (value is not None) and option["default"] != value:
                        if protocol == "xboard" and option["type"] == "check":
                            value = int(bool(value))
                        set_option.setOption(key, value)

        engine_proc.connect("readyForOptions", optionsCallback)

        return engine_proc

    def initPlayerEngine(self,
                         engine,
                         color,
                         diffi,
                         variant,
                         secs=0,
                         incr=0,
                         forcePonderOff=False):
        engine = self.initEngine(engine, color)

        def optionsCallback(engine):
            engine.setOptionStrength(diffi, forcePonderOff)
            engine.setOptionVariant(variant)
            if secs > 0:
                engine.setOptionTime(secs, incr)

        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine

    def initAnalyzerEngine(self, engine, mode, variant):
        engine = self.initEngine(engine, WHITE)

        def optionsCallback(engine):
            engine.setOptionAnalyzing(mode)
            engine.setOptionVariant(variant)

        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine

    def addEngine(self, name, new_engine, protocol, vm_name):
        engine = {"name": name,
                  "protocol": protocol,
                  "command": new_engine,
                  "recheck": True}
        if vm_name is not None:
            engine["vm_name"] = vm_name
        self._engines.append(engine)

    def removeEngine(self, name):
        names = [engine["name"] for engine in self.engines]
        index = names.index(name)
        del self.engines[index]

        names = [engine["name"] for engine in self._engines]
        index = names.index(name)
        del self._engines[index]


discoverer = EngineDiscoverer()


def init_engine(analyzer_type, gamemodel, force=False):
    """
    Initializes and starts the engine analyzer of analyzer_type the user has
    configured in the Engines tab of the preferencesDialog, for gamemodel. If no
    such engine is set in the preferences, or if the configured engine doesn't
    support the chess variant being played in gamemodel, then no analyzer is
    started and None is returned.
    """
    if analyzer_type == HINT:
        combo_name = "ana_combobox"
        check_name = "analyzer_check"
        mode = ANALYZING
    else:
        combo_name = "inv_ana_combobox"
        check_name = "inv_analyzer_check"
        mode = INVERSE_ANALYZING

    analyzer = None

    if conf.get(check_name, True):
        anaengines = list(discoverer.getAnalyzers())
        engine = discoverer.getEngineByMd5(conf.get(combo_name, 0))
        if engine is None:
            # Let Stockfish to be default analyzer in Windows installer
            engine = anaengines[-1]

        if gamemodel.variant.variant in discoverer.getEngineVariants(engine):
            analyzer = discoverer.initAnalyzerEngine(engine, mode,
                                                     gamemodel.variant)
            log.debug("%s analyzer: %s" % (analyzer_type, repr(analyzer)))

    return analyzer


def is_uci(engine_command):
    command = Command(engine_command, "uci\n")
    status, output, err = command.run(timeout=3)
    uci = False
    for line in output.splitlines():
        line = line.rstrip()
        if line == "uciok" or line.startswith("info string"):
            uci = True
            break
        elif "Error" in line or "Illegal" in line or "Invalid" in line:
            break
    return uci


def is_cecp(engine_command):
    command = Command(engine_command, "xboard\nprotover 2\n")
    status, output, err = command.run(timeout=3)
    cecp = False
    for line in output.splitlines():
        line = line.rstrip()
        if "feature" in line and "done" in line:
            cecp = True
            break
        elif "Error" in line or "Illegal" in line or "Invalid" in line:
            break
    return cecp


if __name__ == "__main__":
    from gi.repository import GLib
    from gi.repository import GObject
    GObject.threads_init()
    mainloop = GLib.MainLoop()

    # discoverer = EngineDiscoverer()

    def discovering_started(discoverer, names):
        print("discovering_started", names)

    discoverer.connect("discovering_started", discovering_started)

    def engine_discovered(discoverer, name, engine):
        sys.stdout.write(".")

    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered(discoverer):
        print("all_engines_discovered")
        print([engine["name"] for engine in discoverer.getEngines()])
        mainloop.quit()

    discoverer.connect("all_engines_discovered", all_engines_discovered)

    discoverer.start()

    mainloop.run()
