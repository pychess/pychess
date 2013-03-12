from __future__ import with_statement 

import os
import sys
from hashlib import md5
from threading import Thread
from os.path import join, dirname, abspath
from copy import deepcopy

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring
try:
    from xml.etree.ElementTree import ParseError
except ImportError:
    from xml.parsers.expat import ExpatError as ParseError

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System import conf
from pychess.System.Log import log
from pychess.System.command import Command
from pychess.System.SubProcess import SubProcess, searchPath, SubProcessError
from pychess.System.prefix import addUserConfigPrefix, getEngineDataPrefix
from pychess.System.ThreadPool import pool, PooledThread
from pychess.Players.Player import PlayerIsDead
from pychess.Utils.const import *
from CECPEngine import CECPEngine
from UCIEngine import UCIEngine
from pychess.Variants import variants

attrToProtocol = {
    "uci": UCIEngine,
    "cecp": CECPEngine
}

def compareVersions(ver1, ver2):
    ''' Returns -1 if ver1 < ver2; 0 if ver1 == ver2; 1 if ver1 > ver2 '''
    parts1 = map(int, ver1.split('.'))
    parts2 = map(int, ver2.split('.'))
    for part1, part2 in zip(parts1, parts2):
        if part1 != part2:
            return cmp(part1, part2)
    return cmp(len(parts1),len(parts2))

def mergeElements(elemA, elemB):
    """ Recursively merge two xml-elements into the first.
        If both elements contain the same child, the text will be taken form elemA.
          <A><B name='t'>text1</B><C>text2</C></A>
        + <A><B name='u'>text3</B><C>text4</C></A>
        = <A><B name='u'>text3</B><B name='t'>text1</B><C>text2</C></A>
        Merges some attributes*."""
    
    elemA.attrib.update(elemB.attrib)
    childrenA = dict(((c.tag,c.get('name')),c) for c in elemA.getchildren())
    for child in elemB.getchildren():
        tag = (child.tag,child.get('name'))
        if not tag in childrenA:
            elemA.append(deepcopy(child))
        else:
            mergeElements(childrenA[tag], child)

#<engine protocol='cecp' protover='2' binname='PyChess.py'>
#    <path>/usr/bin/gnuchess</path>
#    <md5>bee39e0ac125b46a8ce0840507dde50e</md5>
#    <vm>
#        <path>/use/bin/python</path>
#        <md5>lksjdflkajdflk</md5>
#    </vm>
#</engine>

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

PYTHONBIN = sys.executable.split("/")[-1]

backup = """
<engines version="%s">
    <engine protocol="cecp" protover="2" binname="PyChess.py">
        <meta><country>dk</country></meta>
        <vm binname="%s"><args><arg name='0' value="-u"/></args></vm></engine>
    <engine protocol="cecp" protover="2" binname="shatranj.py">
        <vm binname="%s"><args><arg name='0' value="-u"/></args></vm>
        <args><arg name='0' value='-xboard'/></args></engine>
    <engine protocol="cecp" protover="2" binname="gnuchess">
        <meta><country>us</country></meta>
        <cecp-features><feature name="sigint" value="1"/></cecp-features>
        </engine>
    <engine protocol="cecp" protover="2" binname="gnome-gnuchess">
        <meta><country>us</country></meta>
        <cecp-features><feature name="sigint" value="1"/></cecp-features>
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
    <engine protocol="cecp" protover="2" binname="amy">
        <meta><country>de</country><author>Thorsten Greiner</author></meta></engine>
    <engine protocol="cecp" protover="1" binname="amundsen">
        <meta><country>sw</country><author>John Bergbom</author></meta></engine>
    
    <engine protocol="uci" protover="1" binname="gnuchessu">
        <meta><country>us</country></meta></engine>
    <engine protocol="uci" protover="1" binname="robbolito">
        <meta><country>ru</country></meta></engine>
    <engine protocol="uci" protover="1" binname="glaurung">
        <meta><country>no</country></meta></engine>
    <engine protocol="uci" protover="1" binname="stockfish">
        <meta><country>no</country></meta></engine>
    <engine protocol="uci" protover="1" binname="ShredderClassicLinux">
        <meta><country>de</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit_21_static"> 
        <meta><country>fr</country></meta></engine>
    <engine protocol="uci" protover="1" binname="fruit">
        <meta><country>fr</country></meta></engine>
    <engine protocol="uci" protover="1" binname="toga2">
        <meta><country>de</country></meta></engine>
    <engine protocol="uci" protover="1" binname="hiarcs">
        <meta><country>gb</country></meta></engine>
    <engine protocol="uci" protover="1" binname="diablo">
        <meta><country>us</country><author>Marcus Predaski</author></meta></engine>

    <engine protocol="uci" protover="1" binname="Houdini.exe">
        <meta><country>be</country></meta>
        <vm binname="wine"/></engine>
    <engine protocol="uci" protover="1" binname="Rybka.exe">
        <meta><country>ru</country></meta>
        <vm binname="wine"/></engine>
</engines>
""" % (ENGINES_XML_API_VERSION, PYTHONBIN, PYTHONBIN)

class EngineDiscoverer (GObject, PooledThread):
    
    __gsignals__ = {
        "discovering_started": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "engine_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "engine_failed": (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object)),
        "all_engines_discovered": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        
        self.backup = ET.ElementTree(fromstring(backup))
        self.xmlpath = addUserConfigPrefix("engines.xml")
        try:
            self.dom = ET.ElementTree(file=self.xmlpath)
            c = compareVersions(self.dom.getroot().get('version', default='0'), ENGINES_XML_API_VERSION)
            if c == -1:
                log.warn("engineNest: engines.xml is outdated. It will be replaced\n")
                # TODO: this is not so nice, koz will lose modifications made on engines.xml
                self.dom = deepcopy(self.backup)
            elif c == 1:
                raise NotImplementedError, "engines.xml is of a newer date. In order" + \
                                "to run this version of PyChess it must first be removed"
        except ParseError, e:
            log.warn("engineNest: %s\n" % e)
            self.dom = deepcopy(self.backup)
        except IOError, e:
            log.info("engineNest: Couldn\'t open engines.xml. Creating a new.\n%s\n" % e)
            self.dom = deepcopy(self.backup)
        
        self._engines = {}
    
    ############################################################################
    # Discover methods                                                         #
    ############################################################################
    
    def __findRundata (self, engine):
        """ Searches for a readable, executable named 'binname' in the PATH.
            For the PyChess engine, special handling is taken, and we search
            PYTHONPATH as well as the directory from where the 'os' module is
            imported """
        
        if engine.find('vm') is not None:
            altpath = engine.find('vm').find('path') is not None and \
                    engine.find('vm').find('path').text.strip()
            vmpath = searchPath(engine.find('vm').get('binname'),
                    access=os.R_OK|os.X_OK, altpath = altpath)
            
            if engine.get('binname') == "PyChess.py":
                path = join(abspath(dirname(__file__)), "PyChess.py")
                if not os.access(path, os.R_OK):
                    path = None
            else:
                altpath = engine.find('path') is not None and engine.find('path').text.strip()
                path = searchPath(engine.get('binname'), access=os.R_OK, altpath=altpath)
            if vmpath and path:
                return vmpath, path
        else:
            altpath = engine.find('path') is not None and engine.find('path').text.strip()
            path = searchPath(engine.get('binname'), access=os.R_OK|os.X_OK, altpath=altpath)
            if path:
                return None, path
        
        return False
    
    def __fromUCIProcess (self, subprocess):
        ids = subprocess.ids
        options = subprocess.options
        engine = fromstring('<engine><meta/><options/></engine>')
        
        meta = engine.find('meta')
        if "name" in ids:
            meta.append(fromstring('<name>%s</name>' % ids['name']))
        if 'author' in ids:
            meta.append(fromstring('<author>%s</author>' % ids['author']))
        
        optnode = engine.find('options')
        for name, dic in options.iteritems():
            option = fromstring('<%s-option name="%s"/>' % (dic.pop('type'), name))
            optnode.append(option)
            for key, value in dic.iteritems():
                if key == 'vars':
                    for valueoption in value:
                        option.append(fromstring('<var name="%s"/>' % valueoption))
                else:
                    option.attrib[key] = str(value)
                
        return engine
    
    def __fromCECPProcess (self, subprocess):
        features = subprocess.features
        options = subprocess.options
        engine = fromstring('<engine><meta/><cecp-features/><options/></engine>')
        
        meta = engine.find('meta')
        if "name" in features:
            meta.append(fromstring('<name>%s</name>' % features['myname']))
        
        feanode = engine.find('cecp-features')
        optnode = engine.find('options')

        for opt in options:
            if " -check " in opt:
                name, value = opt.split(" -check ")
                optnode.append(fromstring('<check-option name="%s" default="%s"/>' % (name, bool(int(value)))))
            elif " -spin " in opt:
                name, value = opt.split(" -spin ")
                defv, minv, maxv = value.split()
                optnode.append(fromstring('<spin-option name="%s" default="%s" min="%s" max="%s"/>' % (name, defv, minv, maxv)))
            elif " -slider " in opt:
                name, value = opt.split(" -slider ")
                defv, minv, maxv = value.split()
                optnode.append(fromstring('<spin-option name="%s" default="%s" min="%s" max="%s"/>' % (name, defv, minv, maxv)))
            elif " -string " in opt:
                name, value = opt.split(" -string ")
                optnode.append(fromstring('<string-option name="%s" default="%s"/>' % (name, value)))
            elif " -file " in opt:
                name, value = opt.split(" -file ")
                optnode.append(fromstring('<string-option name="%s" default="%s"/>' % (name, value)))
            elif " -path " in opt:
                name, value = opt.split(" -path ")
                optnode.append(fromstring('<string-option name="%s" default="%s"/>' % (name, value)))
            elif " -combo " in opt:
                name, value = opt.split(" -combo ")
                optnode.append(fromstring('<combo-option name="%s" default="%s"/>' % (name, value)))
            elif " -button" in opt:
                pos = opt.find(" -button")
                optnode.append(fromstring('<button-option name="%s"/>' % opt[:pos]))
            elif " -save" in opt:
                pos = opt.find(" -save")
                optnode.append(fromstring('<button-option name="%s"/>' % opt[:pos]))
            elif " -reset" in opt:
                pos = opt.find(" -reset")
                optnode.append(fromstring('<button-option name="%s"/>' % opt[:pos]))

        for key, value in features.iteritems():
            if key == "smp" and value == 1:
                optnode.append(fromstring('<spin-option name="cores" default="1" min="1" max="64"/>'))
            elif key == "memory" and value == 1:
                optnode.append(fromstring('<spin-option name="memory" default="32" min="1" max="4096"/>'))
            else:
                feanode.append(fromstring('<feature name="%s" value="%s"/>' % (key, value)))
        
        optnode.append(fromstring('<check-option name="Ponder" default="false"/>'))
        #optnode.append(fromstring('<check-option name="Random" default="false"/>'))
        #optnode.append(fromstring('<spin-option name="Depth" min="1" max="-1" default="false"/>'))
        
        return engine
    
    def __discoverE (self, engine):
        subproc = self.initEngine (engine, BLACK)
        try:
            subproc.connect('readyForOptions', self.__discoverE2, engine)
            subproc.prestart() # Sends the 'start line'
            subproc.start()
        except SubProcessError, e:
            log.warn("Engine %s failed discovery: %s" % (engine.get('binname'),e))
            self.emit("engine_failed", engine.get('binname'), engine)
        except PlayerIsDead, e:
            # Check if the player died after engine_discovered by our own hands
            if not self.toBeRechecked[engine]:
                log.warn("Engine %s failed discovery: %s" % (engine.get('binname'),e))
                self.emit("engine_failed", engine.get('binname'), engine)
    
    def __discoverE2 (self, subproc, engine):
        if engine.get("protocol") == "uci":
            fresh = self.__fromUCIProcess(subproc)
        elif engine.get("protocol") == "cecp":
            fresh = self.__fromCECPProcess(subproc)
        mergeElements(engine, fresh)

        exitcode = subproc.kill(UNKNOWN_REASON)
        if exitcode:
            log.debug("Engine failed %s\n" % self.getName(engine))
            self.emit("engine_failed", engine.get('binname'), engine)
            return
        
        engine.set('recheck', 'false')
        log.debug("Engine finished %s\n" % self.getName(engine))
        self.emit ("engine_discovered", engine.get('binname'), engine)
    
    
    ############################################################################
    # Main loop                                                                #
    ############################################################################
    
    def __needClean(self, rundata, engine):
        """ Check if the filename or md5sum of the engine has changed.
            In that case we need to clean the engine """
        
        vmpath, path = rundata
        
        # Check if filename is not set, or if it has changed
        if engine.find("path") is None or engine.find("path").text != path:
            return True
        # If the engine failed last time, we'll recheck it as well
        if engine.get('recheck') == "true":
            return True
        
        # Check if md5sum is not set, or if it has changed
        if engine.find("md5") is None:
            return True
        with open(path) as f:
            md5sum = md5(f.read()).hexdigest()
        if engine.find("md5").text != md5sum:
            return True
        
        return False
    
    def __clean(self, rundata, engine):
        """ Grab the engine from the backup and attach the attributes from
            rundata. The 'new' engine is returned and ready for discovering.
        
            If engine doesn't exist in backup, an 'unsupported engine' warning
            is logged, and a new engine element is created for it
        """
        
        vmpath, path = rundata
        
        with open(path) as f:
            md5sum = md5(f.read()).hexdigest()
        
        ######
        # Find the backup engine
        ######
        try:
            engine2 = (c for c in self.backup.findall('engine')
                       if c.get('binname') == engine.get('binname')).next()
        except StopIteration:
            log.warn("Engine '%s' has not been tested and verified to work with PyChess\n" % \
                engine.get('binname'))
            engine2 = fromstring('<engine></engine>')
            engine2.set('binname', engine.get('binname'))
            engine2.set('protocol', engine.get('protocol'))
            if engine.get('protover'):
                engine2.set('protover', engine.get('protover'))
            engine2.set('recheck', 'true')

        # This doesn't work either. Dammit python
        # engine = any(c for c in self.backup.getchildren()
        #             if c.get('binname') == engine.get('binname'))
        # Waiting for etree 1.3 to get into python, before we can use xpath 
        # engine = self.backup.find('engine[@binname="%s"]' % engine.get('binname'))
        
        ######
        # Clean it
        ######
        engine2.append(fromstring('<path>%s</path>' % path))
        engine2.append(fromstring('<md5>%s</md5>' % md5sum))
        engine2.append(fromstring('<args/>'))
        
        if vmpath:
            vmbn = engine.find('vm').get('binname')
            engine2.append(fromstring('<vm binname="%s"/>' % vmbn))
            engine2.find('vm').append(fromstring('<path>%s</path>' % vmpath))
            engine2.find('vm').append(fromstring('<args/>'))
        
        return engine2

    ######
    # Save the xml
    ######
    def save(self, *args):
        try:
            with open(self.xmlpath, "w") as f:
                indent(self.dom.getroot())
                self.dom.write(f)
        except IOError, e:
            log.error("Saving enginexml raised exception: %s\n" % \
                      ", ".join(str(a) for a in e.args))
    
    def run (self):
        # List available engines
        for engine in self.dom.findall('engine'):
            ######
            # Find the known and installed engines on the system
            ######
            
            # Validate slightly
            if not engine.get("protocol") or not engine.get("binname"):
                log.warn("Engine '%s' lacks protocol/binname attributes. Skipping\n" % \
                         engine.get('binname'))
                continue
            
            # Look up
            rundata = self.__findRundata(engine)
            if not rundata:
                # Engine is not available on the system
                continue
            
            if self.__needClean(rundata, engine):
                engine2 = self.__clean(rundata, engine)
                if engine2 is None:
                    # No longer suported
                    continue
                self.dom.getroot().remove(engine)
                self.dom.getroot().append(engine2)
                engine = engine2
                engine.set('recheck', 'true')
            
            self._engines[engine.get("binname")] = engine
        
        ######
        # Runs all the engines in toBeRechecked, in order to gather information
        ######
        
        self.toBeRechecked = dict((c,False) for c in self.dom.findall('engine')
                                  if c.get('recheck') == 'true')
        # Waiting for etree 1.3 to get into python, before we can use xpath
        # toBeRechecked = self.dom.findall('engine[recheck=true]')
        
        def count(self_, binname, engine, wentwell):
            if wentwell:
                self.toBeRechecked[engine] = True
            if all(self.toBeRechecked.values()):
                self.emit("all_engines_discovered")
        self.connect("engine_discovered", count, True)
        self.connect("engine_failed", count, False)
        
        if self.toBeRechecked:
            binnames = [engine.get('binname') for engine in self.toBeRechecked.keys()] 
            self.emit("discovering_started", binnames)
            self.connect("all_engines_discovered", self.save)
            for engine in self.toBeRechecked.keys():
                self.__discoverE(engine)
        else:
            self.emit('all_engines_discovered')
        
        
    
    ############################################################################
    # Interaction                                                              #
    ############################################################################
    
    def is_analyzer(self, engine):
        protocol = engine.get("protocol")
        if protocol == "uci":
            return True
        elif protocol == "cecp":
            if any(True for f in engine.findall('cecp-features/feature') if
                   f.get('name') == 'analyze' and f.get('value') == '1'):
                return True
        return False
        
    def getAnalyzers (self):
        return [engine for engine in self.getEngines().values() if self.is_analyzer(engine)]
    
    def getEngines (self):
        """ Returns {binname: enginexml} """
        return self._engines
    
    def getEngineN (self, index):
        return self.getEngines()[self.getEngines().keys()[index]]
    
    def getEngineByMd5 (self, md5sum, list=[]):
        if not list:
            list = self.getEngines().values()
        for engine in list:
            md5 = engine.find('md5')
            if md5 is None: continue
            if md5.text.strip() == md5sum:
                return engine
    
    def getEngineVariants (self, engine):
        for variantClass in variants.values():
            if variantClass.standard_rules:
                yield variantClass.board.variant
            else:
                for feature in engine.findall("cecp-features/feature"):
                    if feature.get("name") == "variants":
                        if variantClass.cecp_name in feature.get('value'):
                            yield variantClass.board.variant
                # UCI knows Chess960 only
                if variantClass.cecp_name == "fischerandom":
                    for option in engine.findall('options/check-option'):
                        if option.get("name") == "UCI_Chess960":
                            yield variantClass.board.variant
    
    def getName (self, engine=None):
        # Test if the call was to get the name of the thread
        if engine is None:
            return Thread.getName(self)
        
        nametag = engine.find("meta/name")
        if nametag is not None:
            return nametag.text.strip()
        return engine.get('binname')
    
    def getCountry (self, engine):
        country = engine.find('meta/country')
        if country is not None:
            return country.text.strip()
        return None

    def initEngine (self, xmlengine, color):
        protover = int(xmlengine.get("protover"))
        protocol = xmlengine.get("protocol")
        
        path = xmlengine.find('path').text.strip()
        args = [a.get('value') for a in xmlengine.findall('args/arg')]
        if xmlengine.find('vm') is not None:
            vmpath = xmlengine.find('vm/path').text.strip()
            vmargs = [a.get('value') for a in xmlengine.findall('vm/args/arg')]
            args = vmargs+[path]+args
            path = vmpath
        md5 = xmlengine.find('md5').text.strip()
        
        working_directory = xmlengine.get("directory")
        if working_directory:
            workdir = working_directory
        else:
            workdir = getEngineDataPrefix()
        warnwords = ("illegal", "error", "exception")
        subprocess = SubProcess(path, args, warnwords, SUBPROCESS_SUBPROCESS, workdir)
        engine = attrToProtocol[protocol](subprocess, color, protover, md5)
        
        if xmlengine.find('meta/name') is not None:
            engine.setName(xmlengine.find('meta/name').text.strip())
            #print 'set engine name to "%s"' % engine.name
        
        # If the user has configured special options for this engine, here is
        # where they should be set.
        def optionsCallback (engine):
            options_tags = xmlengine.findall(".//options")
            if options_tags:
                for option in options_tags[0].getchildren():
                    key = option.get("name")
                    value = option.get("value")
                    if (value is not None) and option.get("default") != value:
                        if protocol == "cecp" and option.tag.split("-")[0] == "check":
                            value = int(bool(value))
                        engine.setOption(key, value)
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
        def optionsCallback (engine):
            engine.setOptionAnalyzing(mode)
            engine.setOptionVariant(variant)
        engine.connect("readyForOptions", optionsCallback)
        engine.prestart()
        return engine

    def addEngine(self, name, new_engine, protocol):
        path, binname = os.path.split(new_engine)
        engine = fromstring('<engine></engine>')
        engine.set('binname', name)
        if protocol.lower() == "uci":
            engine.set('protocol', 'uci')
            engine.set('protover', '1')
        else:
            engine.set('protocol', 'cecp')
            engine.set('protover', '2')
            # TODO: handle protover 1 engines
        with open(new_engine) as f:
            md5sum = md5(f.read()).hexdigest()
        engine.append(fromstring('<path>%s</path>' % new_engine))
        engine.append(fromstring('<md5>%s</md5>' % md5sum))
        engine.append(fromstring('<args/>'))
        engine.set('recheck', 'true')

        self.dom.getroot().append(engine)

    def removeEngine(self, name):
        engine = self._engines[name]
        del self._engines[name]
        self.dom.getroot().remove(engine)

discoverer = EngineDiscoverer()

def init_engine (analyzer_type, gamemodel, force=False):
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
            engine = anaengines[0]
        
        if gamemodel.variant.board.variant in discoverer.getEngineVariants(engine):
            analyzer = discoverer.initAnalyzerEngine(engine, mode, gamemodel.variant)
            log.debug("%s analyzer: %s\n" % (analyzer_type, repr(analyzer)))
        
    return analyzer

def is_uci(new_engine):
    command = Command(new_engine, "uci\n")
    output = command.run(timeout=3)[1]
    uci = False
    for line in output.split("\n"):
        line = line.rstrip()
        if line == "uciok":
            uci = True
            break
        elif "Error" in line or "Illegal" in line or "Invalid" in line:
            break
    return uci

def is_cecp(new_engine):
    command = Command(new_engine, "xboard\nprotover 2\n")
    output = command.run(timeout=3)[1]
    cecp = False
    for line in output.split("\n"):
        line = line.rstrip()
        if "feature" in line and "done" in line:
            cecp = True
            break
        elif "Error" in line or "Illegal" in line or "Invalid" in line:
            break
    return cecp

if __name__ == "__main__":
    import glib, gobject
    gobject.threads_init()
    mainloop = glib.MainLoop()

#    discoverer = EngineDiscoverer()

    def discovering_started (discoverer, binnames):
        print "discovering_started", binnames
    discoverer.connect("discovering_started", discovering_started)

    def engine_discovered (discoverer, binname, engine):
        sys.stdout.write(".")
    discoverer.connect("engine_discovered", engine_discovered)

    def all_engines_discovered (discoverer):
        print "all_engines_discovered"
        print discoverer.getEngines().keys()
        mainloop.quit()
    discoverer.connect("all_engines_discovered", all_engines_discovered)
    
    discoverer.start()

    mainloop.run()
