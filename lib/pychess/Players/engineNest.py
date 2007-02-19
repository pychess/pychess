from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, md5, imp, thread
from threading import Lock, Condition
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from CECPProtocol import CECPProtocol
from ProtocolEngine import ProtocolEngine
from UCIProtocol import UCIProtocol
from pychess.Utils.const import prefix, WHITE

attrToProtocol = {
    "uci": UCIProtocol,
    "cecp": CECPProtocol
}

backup = """
<engines>
    <engine protocol="cecp" binname="PyChess.py" />
    <engine protocol="cecp" binname="gnuchess" />
    <engine protocol="cecp" binname="crafty" />
    <engine protocol="cecp" binname="faile" />
    <engine protocol="cecp" binname="phalanx" />
    <engine protocol="cecp" binname="sjeng" />
    <engine protocol="uci" binname="ShredderClassicLinux" />
    <engine protocol="uci" binname="fruit_21_static" />
</engines>
"""

class EngineDiscoverer (GObject):
    
    __gsignals__ = {
        "discovering_started": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "engine_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "all_engines_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        self.xmlpath = prefix("engines.xml")
        
        try:
            self.dom = minidom.parse( self.xmlpath )
        except ExpatError:
            self.dom = minidom.parseString( backup )
        except IOError:
            self.dom = minidom.parseString( backup )
            
        self._engines = {}
        self.lock = Lock()
        self.condition = Condition()
        self.lock.acquire()

    ############################################################################
    # XML methods                                                              #
    ############################################################################
    
    def _clearEngine (self, engine):
        for child in [n for n in engine.childNodes]:
            engine.removeChild(child)
    
    def _createElement (self, name, strvalue="", args=[]):
        element = self.dom.createElement(name)
        if strvalue:
            element.appendChild(self.dom.createTextNode(strvalue))
        for key, value in args:
            element.setAttribute(key, value)
        return element
    
    ############################################################################
    # Discover methods                                                         #
    ############################################################################
    
    def _findPath (self, binname):
        if binname == "PyChess.py":
            if "PYTHONPATH" in os.environ:
                path = os.path.abspath(os.environ["PYTHONPATH"])
                path = os.path.join(path, "pychess/Players/PyChess.py")
            else:
                path = os.path.dirname(imp.find_module("os")[1])
                path = os.path.join(path,
                        "site-packages/pychess/Players/PyChess.py")
            return path, "env python "+path
        else:
            for dir in os.environ["PATH"].split(":"):
                path = os.path.join(dir, binname)
                if os.path.isfile(path):
                    if not os.access (path, os.R_OK):
                        print "Warning: Could not read", path
                        continue
                    if not os.access (path, os.EX_OK):
                        print "Warning: Could not execute", path
                        continue
                    return path, path
        return False
    
    def _handleUCIOptions (self, engine, options):
        optnode = self.dom.createElement("uci-options")
        for name, dic in options.iteritems():
            type = dic["type"]
            del dic["type"]
            
            args = [ ("name",name) ]
            for key, value in dic.iteritems():
                if key != "vars":
                    args.append( (key,value) )
            
            if type == "check":
                node = self._createElement("check-option", args=args)
            elif type == "string":
                node = self._createElement("string-option", args=args)
            elif type == "combo":
                node = self._createElement("combo-option", args=args)
                for value in dic["vars"]:
                    varNode = self._createElement("var", args=[("value",value)])
                    node.appendChild( varNode )
            elif type == "spin":
                node = self._createElement("spin-option", args=args)
            elif type == "button":
                node = self._createElement("button-option", args=args)
            optnode.appendChild(node)
        
        engine.appendChild(optnode)
        
    def _findOutMore (self, engine, binname):
        
        protocol = engine.getAttribute("protocol")
        path = engine.getElementsByTagName("path")[0].childNodes[0].data
        
        e = ProtocolEngine ((attrToProtocol[protocol], path), WHITE)
        e._wait()
        
        if protocol == "uci":
            e.proto.startGame()
            
            ids = self.dom.createElement("uci-ids")
            for key, value in e.proto.ids.iteritems():
                args = (("name",key), ("value", value))
                ids.appendChild(self._createElement("id",args=args))
            engine.appendChild(ids)
            
            self._handleUCIOptions (engine, e.proto.options)
        
        elif protocol == "cecp":
            features = self.dom.createElement("cecp-features")
            
            for key, value in e.proto.features.iteritems():
                command="depth" 
                args = (("command",key),
                        ("supports", value and "true" or "false"))
                node = self._createElement("feature",args=args)
                features.appendChild(node)
            
            engine.appendChild(features)
            
            # TODO: We still don't know if the engine supports "protover 2".
            # This is important for faster loadtimes and to know if an engine
            # supports loading
        
        engine.appendChild( self._createElement("name", repr(e)) )
        e.kill()
        
        self._engines[binname] = engine
        thread.start_new(self.emit, ("engine_discovered", binname, engine))
        
        self.threads -= 1
        if not self.threads:
            self.condition.acquire()
            self.condition.notifyAll()
            self.condition.release()
        
    ############################################################################
    # Main loop                                                                #
    ############################################################################
    
    def start (self):
        thread.start_new(self._start, ())
        
    def _start (self):
        toBeDiscovered = []
        
        for engine in self.dom.getElementsByTagName("engine"):
        
            binname = engine.getAttribute("binname")
            path = self._findPath(binname)
            
            if not path:
                # We ignore engines not available
                continue
            
            path, execpath = path
            md5sum = md5.new(open(path).read()).hexdigest()
            
            checkIt = False
            
            pathNodes = engine.getElementsByTagName("path")
            if pathNodes:
                epath = pathNodes[0].childNodes[0].data.split()[-1]
                if epath != path:
                    self._clearEngine(engine)
                    checkIt = True
                else:
                    md5Nodes = engine.getElementsByTagName("md5")
                    if not md5Nodes or \
                            md5Nodes[0].childNodes[0].data.strip() != md5sum:
                        self._clearEngine(engine)
                        checkIt = True
            else:
                checkIt = True
            
            if checkIt:
                engine.appendChild( self._createElement("path", execpath) )
                engine.appendChild( self._createElement("md5", md5sum) )
                toBeDiscovered.append((engine, binname))
            
            else:
                self._engines[binname] = engine
            
        if toBeDiscovered:
            self.emit("discovering_started", 
                [binname for engine, binname in toBeDiscovered])
            
            self.threads = len(toBeDiscovered)
            for engine, binname in toBeDiscovered:
                thread.start_new(self._findOutMore, (engine,binname))
            
            self.condition.acquire()
            while self.threads:
                self.condition.wait()
            self.condition.release()
        
        self.lock.release()
        thread.start_new(self.emit,("all_engines_discovered",))
        
        f = open(self.xmlpath, "w")
        lines = self.dom.toprettyxml().split("\n")
        f.write("\n".join([l for l in lines if l.strip()]))
        f.close()
    
    ####
    # Interaction
    ####
    
    def getAnalyzers (self):
        engines = self.getEngines()
        analyzers = []
        for engine in engines.values():
            protocol = engine.getAttribute("protocol")
            if protocol == "uci":
                analyzers.append(engine)
            elif protocol == "cecp":
                for feature in engine.getElementsByTagName("feature"):
                    if feature.getAttribute("command") == "analyze":
                        if feature.getAttribute("supports") == "true":
                            analyzers.append(engine)
                        break
        return analyzers
    
    def getEngines (self):
        if self.lock.locked():
            self.lock.acquire()
            self.lock.release()
        return self._engines
    
    def getEngineN (self, index):
        return self.getEngines()[self.getEngines().keys()[index]]
    
    def getName (self, engine):
        return engine.getElementsByTagName("name")[0].childNodes[0].data.strip()
    
    def initEngine (self, engine, color):
        protocol = engine.getAttribute("protocol")
        path = engine.getElementsByTagName("path")[0].childNodes[0].data.strip()
        return ProtocolEngine ((attrToProtocol[protocol], path), color)
    
    #
    # Other
    #
    
    def __del__ (self):
        dom.unlink()

#discoverer = EngineDiscoverer()

#def discovering_started (discoverer, list):
#    print "discovering_started", list
#discoverer.connect("discovering_started", discovering_started)

#from threading import RLock
#rlock = RLock()

#def engine_discovered (discoverer, str, object):
#    rlock.acquire()
#    print "engine_discovered", str, object.toprettyxml()
#    rlock.release()
#discoverer.connect("engine_discovered", engine_discovered)

#def all_engines_discovered (discoverer):
#    print "all_engines_discovered"
#discoverer.connect("all_engines_discovered", all_engines_discovered)

#discoverer.start()
#discoverer.getEngines()
