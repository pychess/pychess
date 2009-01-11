from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, imp
from hashlib import md5
from threading import Thread

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.ThreadPool import pool
#from pychess.System.TaskQueue import TaskQueue
from pychess.System.Log import log
from pychess.System.SubProcess import SubProcess, searchPath, SubProcessError
from pychess.System.prefix import addHomePrefix
from pychess.System.ThreadPool import PooledThread
from pychess.Utils.const import *
from CECPEngine import CECPEngine
from UCIEngine import UCIEngine
from pychess.Variants import variants

attrToProtocol = {
    "uci": UCIEngine,
    "cecp": CECPEngine
}

# TODO: Diablo, Amy and Amundsen
backup = """
<engines version="%s">
    <engine protocol="cecp" protover="2" binname="PyChess.py" />
    <engine protocol="cecp" protover="2" binname="shatranj.py" />
    <engine protocol="cecp" protover="2" binname="gnuchess">
        <meta><country>us</country></meta>
        <cecp-features><feature command="sigint" supports="true"/></cecp-features>
        </engine>
    <engine protocol="cecp" protover="2" binname="gnome-gnuchess">
        <meta><country>us</country></meta>
        <cecp-features><feature command="sigint" supports="true"/></cecp-features>
        </engine>
    <engine protocol="cecp" protover="2" binname="crafty">
        <meta><country>us</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="faile">
        <meta><country>ca</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="phalanx">
        <meta><country>cz</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="sjeng">
        <meta><country>be</country></meta></engine>
    <engine protocol="cecp" protover="2" binname="hoichess">
        <meta><country>de</country></meta></engine>
    <engine protocol="cecp" protover="1" binname="boochess">
        <meta><country>de</country></meta></engine>
    
    <engine protocol="uci" protover="1" binname="glaurung">
        <meta><country>no</country></meta></engine>
    <engine protocol="uci" protover="1" binname="ShredderClassicLinux">
        <meta><country>de</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit_21_static"> 
        <meta><country>fr</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit">
        <meta><country>fr</country></meta></engine>
    <engine protocol="uci" protover="1" binname="toga2">
        <meta><country>de</country></meta></engine>
</engines>
""" % ENGINES_XML_API_VERSION

class EngineDiscoverer (GObject, PooledThread):
    
    __gsignals__ = {
        "discovering_started": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "engine_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "all_engines_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        self.xmlpath = addHomePrefix("engines.xml")
        
        try:
            self.dom = minidom.parse( self.xmlpath )
            engines = self.dom.documentElement
            if engines.hasAttribute("version"):
                version = engines.getAttribute("version")
                if float(version) < float(ENGINES_XML_API_VERSION):
                    log.warn("engineNest: updated engines.xml from version %s to %s \n" %\
                        (version, ENGINES_XML_API_VERSION))
                    self.dom = minidom.parseString( backup )
            else:
                log.warn("engineNest: no version attribute found\n")
                self.dom = minidom.parseString( backup )
        except ExpatError, e:
            log.warn("engineNest: %s\n" % e)
            self.dom = minidom.parseString( backup )
        except IOError:
            self.dom = minidom.parseString( backup )
        
        self._engines = {}
    
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
        """ Searches for a readable, executable named 'binname' in the PATH.
            For the PyChess engine, special handling is taken, and we search
            PYTHONPATH as well as the directory from where the 'os' module is
            imported """
        
        if binname == "PyChess.py":
            path = None
            interpreterPath = searchPath("python", access=os.R_OK|os.EX_OK)
            
            if "PYTHONPATH" in os.environ:
                path = searchPath("pychess/Players/PyChess.py", "PYTHONPATH")
            
            if not path:
                path = os.path.dirname(imp.find_module("os")[1])
                path = os.path.join(path,
                        "site-packages/pychess/Players/PyChess.py")
                if not os.path.isfile(path) or not os.access(path, os.R_OK):
                    return False
            
            return path, interpreterPath, ["-u", path]
        
        elif binname == "shatranj.py":
            interpreterPath = searchPath("python", access=os.R_OK|os.EX_OK)
            path = os.path.expanduser("~/Desktop/shatranj.py")
            if os.path.isfile(path):
                return path, interpreterPath, ["-u", path, "-xboard"]
        
        else:
            path = searchPath(binname, access=os.R_OK|os.X_OK)
            if path:
                return path, path, []
        
        return False
    
    def _handleUCIOptions (self, engine, ids, options):
        meta = self._createOrReturn(engine, "meta")
        
        for key, value in ids.iteritems():
            if key == "name" and not self._hasChildByTagName(meta,"name"):
                meta.appendChild(self._createElement("name", value))
            elif key == "author" and not self._hasChildByTagName(meta,"author"):
                meta.appendChild(self._createElement("author", value))
        
        optnode = self._createOrReturn(engine, "options")
        
        # We don't want to change preset values, but currently there are none,
        # so 'preset' should be an empty dict
        preset = dict([(child.getAttribute("name"),True) for child in \
                optnode.childNodes if child.nodeType == child.ELEMENT_NODE])
        
        for name, dic in options.iteritems():
            if name in preset: continue
            
            type = dic["type"]
            del dic["type"]
            
            args = [ ("name",name) ]
            for key, value in dic.iteritems():
                if key != "vars":
                    args.append( (key,value) )
            
            if type == "check":
                args2 = []
                for key, value in args:
                    if value == True: value = "true"
                    elif value == False: value = "false"
                    args2.append( (key,value) )
                node = self._createElement("check-option", args=args2)
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
                args = [(k,str(v)) for k,v in args]
                node = self._createElement("spin-option", args=args)
            elif type == "button":
                node = self._createElement("button-option", args=args)
            
            optnode.appendChild(node)
        
        engine.appendChild(optnode)
    
    def _handleCECPOptions (self, engine, features):
        feature_node = self._createOrReturn(engine, "cecp-features")
        meta = self._createOrReturn(engine, "meta")
        
        # We don't want to change preset values, but currently there are
        # none, so 'preset' should be an empty dict
        preset = dict ([(f.getAttribute("command"), True) for f in \
                                feature_node.getElementsByTagName("feature")])
        
        for key, value in features.iteritems():
            if key in preset: continue
            
            if key == "myname":
                meta.appendChild( self._createElement("name", value) )
            
            if key == "variants":
                args = (("command",key),
                        ("value", value))
            else:
                args = (("command",key),
                        ("supports", value and "true" or "false"))
            node = self._createElement("feature",args=args)
            feature_node.appendChild(node)
        
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
    
    def _findOutMore (self, toBeDiscovered):
        # List of engines which fails and must be rechecked another time
        rechecks = [] 
        
        # Test engines
        for xmlengine, binname in toBeDiscovered:
            engine = self.initEngine (xmlengine, BLACK)
            try:
                engine.prestart()
                engine.start()
                protname = xmlengine.getAttribute("protocol")
                if protname == "uci":
                    self._handleUCIOptions (xmlengine, engine.ids, engine.options)
                elif protname == "cecp":
                    self._handleCECPOptions (xmlengine, engine.features)
            except SubProcessError:
                rechecks.append(xmlengine)
            
            exitcode = engine.kill(UNKNOWN_REASON)
            if exitcode:
                rechecks.append(xmlengine)
                log.debug("Engine failed %s\n" % self.getName(xmlengine))
            else:
                log.debug("Engine finished %s\n" % self.getName(xmlengine))
            self.emit ("engine_discovered", binname, xmlengine)
        
        return rechecks
        
    ############################################################################
    # Main loop                                                                #
    ############################################################################
    
    def run (self):
        toBeDiscovered = []
        
        for engine in self.dom.getElementsByTagName("engine"):
            if not engine.hasAttribute("protocol") and \
                   engine.hasAttribute("binname"):
                log.warn("Engine '%s' misses protocol/binname attribute\n")
                continue
            
            binname = engine.getAttribute("binname")
            location = self._findPath(binname)
            
            if not location:
                # We ignore engines not available
                continue
            
            file, path, args = location
            md5sum = md5(open(file).read()).hexdigest()
            
            checkIt = False
            
            fileNodes = engine.getElementsByTagName("file")
            if fileNodes:
                efile = fileNodes[0].childNodes[0].data.strip()
                if efile != file:
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
                engine.appendChild( self._createElement("file", file) )
                engine.appendChild( self._createElement("path", path) )
                argselem = engine.appendChild( self._createElement("args") )
                for arg in args:
                    typestr = repr(type(arg))[7:-2]
                    elem = self._createElement("arg", str(arg), (("type", typestr),))
                    argselem.appendChild(elem)
                engine.appendChild( self._createElement("md5", md5sum) )
                toBeDiscovered.append((engine, binname))
            
            self._engines[binname] = engine
        
        if toBeDiscovered:
            self.emit("discovering_started", 
                [binname for engine, binname in toBeDiscovered])
            rechecks = self._findOutMore(toBeDiscovered)
            for xmlengine in rechecks:
                md5Nodes = xmlengine.getElementsByTagName("md5")
                xmlengine.removeChild(md5Nodes[0])
        
        self.emit("all_engines_discovered")
        
        try:
            f = open(self.xmlpath, "w")
            self.dom.writexml(f)
            f.close()
        except IOError, e:
            log.warn("Saving enginexml raised exception: %s\n" % \
                    ", ".join(str(a) for a in e.args))
    
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
    
    def getEngineVariants (self, engine):
        for variantClass in variants.values():
            if variantClass.standard_rules:
                yield variantClass.board.variant
            else:
                for feature in engine.getElementsByTagName("feature"):
                    if feature.getAttribute("command") == "variants":
                        if variantClass.cecp_name in feature.getAttribute("value"):
                            yield variantClass.board.variant
                # UCI knows Chess960 only
                if variantClass.cecp_name == "fischerandom":
                    for option in engine.getElementsByTagName("check-option"):
                        if option.getAttribute("name") == "UCI_Chess960":
                            yield variantClass.board.variant
    
    def getName (self, engine=None):
        # Test if the call was to get the name of the thread
        if engine == None:
            return Thread.getName(self)
        
        names = engine.getElementsByTagName("name")
        if names:
            return names[0].childNodes[0].data.strip()
        else:
            return engine.getAttribute("binname")
    
    def getCountry (self, engine):
        c = engine.getElementsByTagName("country")
        if c:
            return c[0].childNodes[0].data.strip()
        return None
    
    def getArgs (self, engine):
        args = []
        for arg in engine.getElementsByTagName("arg"):
            type = arg.getAttribute("type")
            value = arg.childNodes[0].data.strip()
            if type == "bool":
                args.append(value.lower() == "true" and True or False)
            else:
                args.append(__builtins__[type](value))
        return args
   
    def initEngine (self, xmlengine, color):
        protover = int(xmlengine.getAttribute("protover"))
        protocol = xmlengine.getAttribute("protocol")
        
        path = xmlengine.getElementsByTagName("path")[0].childNodes[0].data.strip()
        args = self.getArgs(xmlengine)
        warnwords = ("illegal", "error", "exception")
        subprocess = SubProcess(path, args, warnwords, SUBPROCESS_SUBPROCESS)
        
        engine = attrToProtocol[protocol](subprocess, color, protover)
        
        if protocol == "uci":
            # If the user has configured special options for this engine, here is
            # where they should be set.
            def optionsCallback (engine):
                if engine.hasOption("OwnBook"):
                    engine.setOption("OwnBook", True)
            engine.connect("readyForOptions", optionsCallback)
        
        return engine
    
    def initPlayerEngine (self, xmlengine, color, diffi, variant, secs=0, incr=0):
        engine = self.initEngine (xmlengine, color)
        def optionsCallback (engine):
            engine.setOptionStrength(diffi)
            engine.setOptionVariant(variant)
            if secs > 0:
                engine.setOptionTime(secs, incr)
        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine
    
    def initAnalyzerEngine (self, xmlengine, mode, variant):
        engine = self.initEngine (xmlengine, WHITE)
        engine.setOptionAnalyzing(mode)
        def optionsCallback (engine):
            engine.setOptionVariant(variant)
        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine
    
    #
    # Other
    #
    
    def __del__ (self):
        self.dom.unlink()

discoverer = EngineDiscoverer()

if __name__ == "__main__":

    discoverer = EngineDiscoverer()

    def discovering_started (discoverer, list):
        print "discovering_started", list
    discoverer.connect("discovering_started", discovering_started)

    from threading import RLock
    rlock = RLock()

    def engine_discovered (discoverer, str, object):
        rlock.acquire()
        try:
            print "engine_discovered", str, object.toprettyxml()
        finally:
            rlock.release()
    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered (discoverer):
        print "all_engines_discovered"
    discoverer.connect("all_engines_discovered", all_engines_discovered)

    discoverer.start()
    discoverer.getEngines()
