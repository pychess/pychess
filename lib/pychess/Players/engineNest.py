import asyncio
import os
from os.path import join, dirname, abspath
import sys
import shutil
import json
from functools import partial
from hashlib import md5
from copy import copy
from collections import OrderedDict

from gi.repository import GLib, GObject

from pychess.compat import create_task
from pychess.System import conf
from pychess.System.Log import log
from pychess.System.command import Command
from pychess.System.SubProcess import SubProcess
from pychess.System.prefix import addUserConfigPrefix, getDataPrefix, getEngineDataPrefix
from pychess.Players.Player import PlayerIsDead
from pychess.Utils import createStoryTextAppEvent
from pychess.Utils.const import BLACK, UNKNOWN_REASON, WHITE, HINT, ANALYZING, INVERSE_ANALYZING, NORMALCHESS
from pychess.Players.CECPEngine import CECPEngine
from pychess.Players.UCIEngine import UCIEngine
from pychess.Players.engineList import PYTHONBIN, VM_LIST, ENGINES_LIST
from pychess.Variants import variants

attrToProtocol = {"uci": UCIEngine, "xboard": CECPEngine}

ENGINE_DEFAULT_LEVEL = 20


class SubProcessError(Exception):
    pass


def md5_sum(filename):
    with open(filename, mode='rb') as file_handle:
        md5sum = md5()
        for buf in iter(partial(file_handle.read, 4096), b''):
            md5sum.update(buf)
    return md5sum.hexdigest()


class EngineDiscoverer(GObject.GObject):

    __gsignals__ = {
        "discovering_started": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        "engine_discovered": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        "engine_failed": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        "all_engines_discovered": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.jsonpath = addUserConfigPrefix("engines.json")
        self.engines = []
        try:
            self.engines = json.load(open(self.jsonpath))
        except ValueError as err:
            log.warning(
                "engineNest: Couldn\'t read engines.json, renamed it to .bak\n%s\n%s"
                % (self.jsonpath, err))
            os.rename(self.jsonpath, self.jsonpath + ".bak")
        except IOError as err:
            log.info("engineNest: Couldn\'t open engines.json, creating a new.\n%s" % err)

        # Try to detect engines shipping .eng files on Linux (suggested by HGM on talkchess.com forum)
        for protocol in ("xboard", "uci"):
            for path in ("/usr/local/share/games/plugins",
                         "/usr/share/games/plugins"):
                path = os.path.join(path, protocol)
                if os.path.isdir(path):
                    for entry in os.listdir(path):
                        ext = os.path.splitext(entry)[1]
                        if ext == ".eng":
                            with open(os.path.join(path, entry)) as file_handle:
                                plugin_spec = file_handle.readline().strip()
                                if not plugin_spec.startswith("plugin spec"):
                                    continue

                                engine_command = file_handle.readline().strip()
                                if self.getEngineByName(engine_command) is not None:
                                    continue

                                supported_variants = file_handle.readline().strip()
                                if not supported_variants.startswith("chess"):
                                    continue

                                new_engine = {}
                                if engine_command.startswith("cd ") and engine_command.find(";") > 0:
                                    parts = engine_command.split(";")
                                    working_directory = parts[0][3:]
                                    engine_command = parts[1]
                                    new_engine["workingDirectory"] = working_directory

                                new_engine["protocol"] = protocol
                                new_engine["name"] = engine_command
                                self.engines.append(new_engine)

        # Initial backup of the loaded engines
        self.backup()

    def __findRunData(self, engine):
        """ Searches for a readable, executable named 'name' in the PATH.
            For the PyChess engine, special handling is taken, and we search
            PYTHONPATH as well as the directory from where the 'os' module is
            imported """
        if engine.get("vm_name") is not None:
            vm_command = engine.get("vm_command")
            altpath = dirname(vm_command) if vm_command else None
            if getattr(sys, 'frozen', False) and engine["vm_name"] == "wine":
                vmpath = None
            else:
                vmpath = shutil.which(engine["vm_name"], mode=os.R_OK | os.X_OK, path=altpath)

            if engine["name"] == "PyChess.py" and not getattr(sys, 'frozen', False):
                path = join(abspath(dirname(__file__)), "PyChess.py")
                if not vmpath.endswith(PYTHONBIN):
                    # from python to python3
                    engine["vm_name"] = PYTHONBIN
                    vmpath = shutil.which(PYTHONBIN, mode=os.R_OK | os.X_OK, path=None)
                if not os.access(path, os.R_OK):
                    path = None
            else:
                command = engine.get("command")
                altpath = dirname(command) if command else None
                path = shutil.which(engine["name"], mode=os.R_OK, path=altpath)

            if vmpath and path:
                return vmpath, path
            elif path and sys.platform == "win32" and engine.get("vm_name") == "wine":
                return None, path

        else:
            command = engine.get("command")
            altpath = dirname(command) if command else None
            if sys.platform == "win32" and not altpath:
                altpath = os.path.join(getDataPrefix(), "engines") + ";" + os.path.dirname(sys.executable)
            path = shutil.which(command if command else engine["name"], mode=os.R_OK | os.X_OK, path=altpath)
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

    @asyncio.coroutine
    def __discoverE(self, engine):
        subproc = yield from self.initEngine(engine, BLACK, False)
        subproc.connect('readyForOptions', self.__discoverE2, engine)
        subproc.prestart()  # Sends the 'start line'

        event = asyncio.Event()
        is_dead = set()
        subproc.start(event, is_dead)

        yield from event.wait()

        if is_dead:
            # Check if the player died after engine_discovered by our own hands
            if not self.toBeRechecked[engine["name"]][1]:
                log.warning("Engine %s failed discovery" % engine["name"])
                self.emit("engine_failed", engine["name"], engine)
            subproc.kill(UNKNOWN_REASON)

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
        """ Grab the engine from the referenced engines and attach the attributes
            from rundata. The update engine is ready for discovering.
        """
        vmpath, path = rundata
        md5sum = md5_sum(path)

        # Find the referenced engine
        refeng = self.getReferencedEngine(engine["name"])
        if refeng is None:
            log.warning("Engine '%s' is not in PyChess predefined known engines list" % engine.get('name'))
            engine['recheck'] = True
        else:
            engine["country"] = refeng["country"]

        # Clean it
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

    def backup(self):
        self.enginesBackup = json.dumps(self.engines)

    def restore(self):
        self.engines = json.loads(self.enginesBackup)

    def hasChanged(self):
        return self.enginesBackup != json.dumps(self.engines)

    def save(self, *args):
        try:
            with open(self.jsonpath, "w") as file_handle:
                json.dump(self.engines, file_handle, indent=1, sort_keys=True)
        except IOError as err:
            log.error("Saving engines.json raised exception: %s" % ", ".join(str(a) for a in err.args))

    def pre_discover(self):
        # Remove the expired engines
        self.engines = [engine for engine in self.engines if os.path.isfile(engine.get('command', ''))]

        # Scan the referenced engines to see if they are installed
        for engine in ENGINES_LIST:
            if engine.autoDetect:
                if self.getEngineByName(engine.name, exactName=False) is not None:  # No rediscovery if already exists
                    continue
                engine = self.getReferencedEngine(engine.name)
                if engine is not None and self.__findRunData(engine):
                    self.engines.append(engine)

        # Check if the existing engines need a refresh
        for engine in self.engines:
            rundata = self.__findRunData(engine)
            if rundata and self.__needClean(rundata, engine):
                self.__clean(rundata, engine)
                engine['recheck'] = True

        # Runs all the engines in toBeRechecked, in order to gather information
        self.toBeRechecked = sorted([(c["name"], [c, False]) for c in self.engines if c.get('recheck')])
        self.toBeRechecked = OrderedDict(self.toBeRechecked)

    def discover(self):
        self.pre_discover()

        def count(self_, name, engine, wentwell):
            if not wentwell:
                print("count() not went well on engine", name)
                self.engines.remove(engine)

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
                    create_task(self.__discoverE(engine))
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
        return [engine for engine in self.getEngines() if self.is_analyzer(engine)]

    def getEngines(self):
        """ Returns a sorted list of engine dicts """
        return sorted(self.engines, key=lambda engine: engine["name"].lower())

    def getEngineN(self, index):
        return self.getEngines()[index]

    def getEngineByName(self, name, exactName=True):
        approximate = None
        for engine in self.engines:
            if engine["name"] == name:  # Priority to exact name
                return engine
            if not exactName and name.lower() in engine["name"].lower():
                approximate = engine
        return approximate

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
        UCI_without_standard_variant = False
        engine_variants = []
        for variantClass in variants.values():
            if variantClass.standard_rules:
                engine_variants.append(variantClass.variant)
            else:
                if engine.get("variants"):
                    if variantClass.cecp_name in engine.get("variants"):
                        engine_variants.append(variantClass.variant)
                # UCI knows Chess960 only
                if engine.get("options"):
                    for option in engine["options"]:
                        if option["name"] == "UCI_Chess960" and \
                                variantClass.cecp_name == "fischerandom":
                            engine_variants.append(variantClass.variant)
                        elif option["name"] == "UCI_Variant":
                            UCI_without_standard_variant = "chess" not in option["choices"]
                            if variantClass.cecp_name in option["choices"] or \
                                    variantClass.cecp_name.lower().replace("-", "") in option["choices"]:
                                engine_variants.append(variantClass.variant)

        if UCI_without_standard_variant:
            engine_variants.remove(NORMALCHESS)

        return engine_variants

    def getEngineLearn(self):
        # Local helpers
        def has_classical(engine):
            status = engine['protocol'] == 'uci'
            if 'variants' in engine:
                status = status and 'normal' in engine['variants']
            if 'options' in engine:
                for option in engine['options']:
                    if option['name'] == 'UCI_Variant' and 'choices' in option:
                        status = status and 'chess' in option['choices']
            return status

        def is_stockfish(engine):
            return 'stockfish' in engine['name'].lower()

        # Initialization
        id = conf.get('ana_combobox')
        analyzer_enabled = conf.get('analyzer_check')

        # Stockfish from the preferences
        if analyzer_enabled:  # The analyzer should be active else we might believe that it is irrelevant
            for engine in self.engines:
                if engine['md5'] == id and is_stockfish(engine):
                    return engine['name']

        # Stockfish from the raw list of engines
        for engine in self.engines:
            if is_stockfish(engine):
                return engine['name']

        # Preferred engine
        if analyzer_enabled:
            for engine in self.engines:
                if engine['md5'] == id and has_classical(engine):
                    return engine['name']

        # First found
        for engine in self.engines:
            if has_classical(engine):
                return engine['name']

        # No engine found
        return None

    def getName(self, engine=None):
        return engine["name"]

    def getReferencedEngine(self, name):
        """ This methods builds an automatic entry based on the name of the engine
            and the preconfigured values found for it.
        """
        for engine in ENGINES_LIST:
            if engine.name.lower() in name.lower():
                # Properties of the engine
                result = {"name": os.path.basename(name),
                          "protocol": engine.protocol[:6],
                          "recheck": True,
                          "country": engine.country,
                          "comment": "",
                          "level": ENGINE_DEFAULT_LEVEL if engine.defaultLevel is None else engine.defaultLevel}
                if '/' in name or '\\' in name:
                    result["command"] = name
                if engine.protocol == "xboard1":
                    result["protover"] = 1
                if engine.protocol == "xboard2":
                    result["protover"] = 2
                if engine.protocol == "uci":
                    result["analyze"] = True
                # if engine.elo > 0:
                #     result["elo"] = engine.elo

                # Attached interpreter
                ext = os.path.splitext(name.lower())[1]
                if ext != "":
                    for vm in VM_LIST:
                        if ext == vm.ext:
                            result["vm_name"] = vm.name
                            if vm.args is not None:
                                result["vm_args"] = vm.args

                # Linux-specific parameters
                if sys.platform != "win32":
                    if "vm_name" not in result and ext == ".exe":
                        result["vm_name"] = "wine"

                # Verify the host application
                if result.get("vm_name") and shutil.which(result["vm_name"], mode=os.R_OK | os.X_OK) is None:
                    return None

                # Found result
                return result

        # No result found
        return None

    def getCountry(self, engine):
        return engine.get("country")

    @asyncio.coroutine
    def initEngine(self, engine, color, lowPriority):
        name = engine['name']
        protocol = engine["protocol"]
        protover = 2 if engine.get("protover") is None else engine.get("protover")
        path = engine['command']
        args = [] if engine.get('args') is None else [a for a in engine['args']]
        if engine.get('vm_command') is not None:
            vmpath = engine['vm_command']
            vmargs = [] if engine.get('vm_args') is None else [a for a in engine['vm_args']]
            args = vmargs + [path] + args
            path = vmpath
        md5_engine = engine['md5']

        working_directory = engine.get("workingDirectory")
        if working_directory:
            workdir = working_directory
        else:
            workdir = getEngineDataPrefix()
        warnwords = ("illegal", "error", "exception")
        try:
            subprocess = SubProcess(path, args=args, warnwords=warnwords, cwd=workdir, lowPriority=lowPriority)
            yield from subprocess.start()
        except OSError:
            raise PlayerIsDead
        except asyncio.TimeoutError:
            raise PlayerIsDead
        except GLib.GError:
            raise PlayerIsDead
        except Exception:
            raise PlayerIsDead

        engine_proc = attrToProtocol[protocol](subprocess, color, protover, md5_engine)
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

    @asyncio.coroutine
    def initPlayerEngine(self,
                         engine,
                         color,
                         diffi,
                         variant,
                         secs=0,
                         incr=0,
                         moves=0,
                         forcePonderOff=False):
        engine = yield from self.initEngine(engine, color, False)

        def optionsCallback(engine):
            engine.setOptionStrength(diffi, forcePonderOff)
            engine.setOptionVariant(variant)
            if secs > 0 or incr > 0:
                engine.setOptionTime(secs, incr, moves)

        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine

    @asyncio.coroutine
    def initAnalyzerEngine(self, engine, mode, variant):
        engine = yield from self.initEngine(engine, WHITE, True)

        def optionsCallback(engine):
            engine.setOptionAnalyzing(mode)
            engine.setOptionVariant(variant)

        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine

    def addEngine(self, name, new_engine, protocol, vm_name, vm_args):
        # Default values
        refeng = self.getReferencedEngine(name)
        if refeng is not None:
            engine = copy(refeng)
        else:
            engine = {"country": "unknown",
                      "comment": "",
                      "level": ENGINE_DEFAULT_LEVEL}

        # New values
        engine["name"] = name
        engine["protocol"] = protocol
        engine["command"] = new_engine
        engine["recheck"] = True
        if vm_name is not None:
            engine["vm_name"] = vm_name
        if vm_args is not None:
            engine["vm_args"] = vm_args
        self.engines.append(engine)

    def addEngineFromReference(self, engine):
        if engine is not None:
            self.engines.append(engine)

    def removeEngine(self, name):
        names = [engine["name"] for engine in self.engines]
        index = names.index(name)
        del self.engines[index]


discoverer = EngineDiscoverer()


@asyncio.coroutine
def init_engine(analyzer_type, gamemodel, force_engine=None):
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

    if conf.get(check_name) or force_engine is not None:
        anaengines = list(discoverer.getAnalyzers())
        if len(anaengines) == 0:
            return None

        if force_engine is not None:
            engine = discoverer.getEngineByName(force_engine)
        else:
            engine = discoverer.getEngineByMd5(conf.get(combo_name))

        if engine is None:
            engine = discoverer.getEngineByName(discoverer.getEngineLearn())

        if engine is None:
            engine = anaengines[-1]

        if gamemodel.variant.variant in discoverer.getEngineVariants(engine):
            analyzer = yield from discoverer.initAnalyzerEngine(engine, mode,
                                                                gamemodel.variant)
            log.debug("%s analyzer: %s" % (analyzer_type, repr(analyzer)))

    return analyzer


def is_uci(engine_command):
    command = Command(engine_command, "uci\nquit\n")
    status, output, err = command.run(timeout=5)
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
    command = Command(engine_command, "xboard\nprotover 2\nquit\n")
    status, output, err = command.run(timeout=5)
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
    from pychess.external import gbulb
    gbulb.install()
    loop = asyncio.get_event_loop()

    def discovering_started(discoverer, names):
        print("discovering_started", names)

    discoverer.connect("discovering_started", discovering_started)

    def engine_discovered(discoverer, name, engine):
        sys.stdout.write(".")

    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered(discoverer):
        print("all_engines_discovered")
        print([engine["name"] for engine in discoverer.getEngines()])
        loop.stop()

    discoverer.connect("all_engines_discovered", all_engines_discovered)

    discoverer.discover()

    loop.run_forever()
