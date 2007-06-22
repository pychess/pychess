from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, md5, imp, thread
from threading import Thread, Condition
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.ThreadPool import pool
from pychess.System.Log import log
from pychess.Utils.const import prefix, WHITE, KILLED, UNKNOWN_REASON
from CECPProtocol import CECPProtocol
from ProtocolEngine import ProtocolEngine
from UCIProtocol import UCIProtocol

attrToProtocol = {
    "uci": UCIProtocol,
    "cecp": CECPProtocol
}

# TODO: Diablo, Amy and Amundsen
backup = """
<engines>
    <engine protocol="cecp" binname="PyChess.py" />
    <engine protocol="cecp" binname="gnuchess" />
    <engine protocol="cecp" binname="gnome-gnuchess" />
    <engine protocol="cecp" binname="crafty" />
    <engine protocol="cecp" binname="faile" />
    <engine protocol="cecp" binname="phalanx" />
    <engine protocol="cecp" binname="sjeng" />
    <engine protocol="cecp" binname="hoichess" />
    <engine protocol="cecp" binname="boochess" />
    <engine protocol="uci" binname="glaurung" />
    <engine protocol="uci" binname="ShredderClassicLinux" />
    <engine protocol="uci" binname="fruit_21_static" />
    <engine protocol="uci" binname="fruit" />
</engines>
"""

class EngineDiscoverer (GObject, Thread):
    
    __gsignals__ = {
        "discovering_started": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "engine_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "all_engines_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        Thread.__init__(self)
        self.xmlpath = prefix("engines.xml")
        
        try:
            self.dom = minidom.parse( self.xmlpath )
        except ExpatError, e:
            log.warn("engineNest: %s" % e)
            self.dom = minidom.parseString( backup )
        except IOError:
            self.dom = minidom.parseString( backup )
            
        self._engines = {}
        self.condition = Condition()

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
    
    def _createOrReturn (self, parrent, tagname):
        tags = parrent.getElementsByTagName(tagname)
        if not tags:
            tag = self.dom.createElement(tagname)
            parrent.appendChild(tag)
            return tag
        return tags[0]
    
    def _hasChildByTagName (self, parrent, tagname):
        for c in parrent.childNodes:
            if c.nodeType == c.ELEMENT_NODE and \
               c.tagName == tagname:
                return True
        return False
    
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
                        log.warn("Could not read the file %s" % path)
                        continue
                    if not os.access (path, os.EX_OK):
                        log.warn("Could not execute the file %s" % path)
                        continue
                    return path, path
        return False
    
    def _handleUCIOptions (self, engine, options):
        optnode = self._createOrReturn(engine, "options")
        used = dict([(child.getAttribute("name"),True) for child in \
                optnode.childNodes if child.nodeType == child.ELEMENT_NODE])
        
        for name, dic in options.iteritems():
            if name in used: continue
            
            type = dic["type"]
            del dic["type"]
            
            args = [ ("name",name) ]
            for key, value in dic.iteritems():
                if key != "vars":
                    args.append( (key,value) )
            
            if type == "check":
                node = self._createElement("check-option", args=args)
            elif type == "string":
                if name == "UCI_EngineAbout":
                    # I don't know why UCI puts about in the options, but we
                    # still put it in the meta where it belongs
                    meta = self._createOrReturn(engine, "meta")
                    if not self._hasChildByTagName (meta, "about"):
                        about = self._createElement("about", dic["default"])
                        meta.appendChild(about)
                    continue
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
        
        meta = self._createOrReturn(engine, "meta")
        
        if protocol == "uci":
            e.proto.startGame()

            for key, value in e.proto.ids.iteritems():
                if key == "name" and not self._hasChildByTagName(meta,"name"):
                    meta.appendChild(self._createElement("name", value))
                elif key == "author" and not self._hasChildByTagName(meta,"author"):
                    meta.appendChild(self._createElement("author", value))
            
            self._handleUCIOptions (engine, e.proto.options)
        
        elif protocol == "cecp":
            features = self._createOrReturn(engine, "cecp-features")
            
            used = dict ([(f.getAttribute("command"), True) for f in \
                                    features.getElementsByTagName("feature")])
            
            for key, value in e.proto.features.iteritems():
                if key in used: continue
                command="depth" 
                args = (("command",key),
                        ("supports", value and "true" or "false"))
                node = self._createElement("feature",args=args)
                features.appendChild(node)
            
            # TODO: We still don't know if the engine supports "protover 2" and
            # some other "Try and fail" based features.
            # This is important for faster loadtimes and to know if an engine
            # supports loading
            
            if not self._hasChildByTagName(meta, "name"):
                meta.appendChild( self._createElement("name", repr(e)) )
            
            if not self._hasChildByTagName(engine, "options"):
                options = self.dom.createElement("options")
                options.appendChild(self._createElement("check-option", \
                                 args=(("name","Ponder"), ("default","false"))))
                options.appendChild(self._createElement("check-option", \
                                 args=(("name","Random"), ("default","false"))))
                options.appendChild(self._createElement("spin-option", \
                                 args=(("name","Depth"), ("min","1"),
                                       ("max","-1"), ("default","false"))))
                engine.appendChild(options)
        
        e.kill(UNKNOWN_REASON)
        
        self._engines[binname] = engine
        self.emit ("engine_discovered", binname, engine)
        
        self.threads -= 1
        if not self.threads:
            self.condition.acquire()
            self.condition.notifyAll()
            self.condition.release()
        
    ############################################################################
    # Main loop                                                                #
    ############################################################################
    
    def run (self):
        toBeDiscovered = []
        
        for engine in self.dom.getElementsByTagName("engine"):
            
            if not engine.hasAttribute("protocol") and \
                   engine.hasAttribute("binname"):
                continue
            
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
                pool.start(self._findOutMore, engine, binname)
            
            self.condition.acquire()
            while self.threads:
                self.condition.wait()
            self.condition.release()
        
        self.emit("all_engines_discovered")
        f = open(self.xmlpath, "w")
        self.dom.writexml(f)
        f.close()
    
    ############################################################################
    # Interaction                                                              #
    ############################################################################
    
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
        """ Returns {binname: enginexml} """
        self.join()
        return self._engines
    
    def getEngineN (self, index):
        return self.getEngines()[self.getEngines().keys()[index]]
    
    def getEngineByMd5 (self, md5sum, list=[]):
        if not list:
            list = self.getEngines().values()
        for engine in list:
            md5s = engine.getElementsByTagName("md5")
            if not md5s: continue
            md5 = md5s[0]
            if md5.childNodes[0].data.strip() == md5sum:
                return engine
    
    def getName (self, engine):
        return engine.getElementsByTagName("name")[0].childNodes[0].data.strip()
    
    def getCountry (self, engine):
        c = engine.getElementsByTagName("country")
        if c:
            return c[0].childNodes[0].data.strip()
        return None
    
    def initEngine (self, engine, color):
        protocol = engine.getAttribute("protocol")
        path = engine.getElementsByTagName("path")[0].childNodes[0].data.strip()
        return ProtocolEngine ((attrToProtocol[protocol], path), color)
    
    #
    # Other
    #
    
    def __del__ (self):
        dom.unlink()

discoverer = EngineDiscoverer()
discoverer.start()

if __name__ == "__main__":

    discoverer = EngineDiscoverer()

    def discovering_started (discoverer, list):
        print "discovering_started", list
    discoverer.connect("discovering_started", discovering_started)

    from threading import RLock
    rlock = RLock()

    def engine_discovered (discoverer, str, object):
        rlock.acquire()
        print "engine_discovered", str, object.toprettyxml()
        rlock.release()
    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered (discoverer):
        print "all_engines_discovered"
    discoverer.connect("all_engines_discovered", all_engines_discovered)

    discoverer.start()
    discoverer.getEngines()
