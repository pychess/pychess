from __future__ import with_statement 

from xml.dom import minidom
from xml.parsers.expat import ExpatError
import os, imp
from hashlib import md5
from threading import Thread
from os.path import join, dirname, abspath
from copy import deepcopy

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring

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

# TODO: Diablo, Amy and Amundsen
backup = """
<engines version="%s">
    <engine protocol="cecp" protover="2" binname="PyChess.py">
        <meta><country>dk</country></meta>
        <vm binname="python"><args><arg name='0' value="-u"/></args></vm></engine>
    <engine protocol="cecp" protover="2" binname="shatranj.py">
        <vm binname="python"><args><arg name='0' value="-u"/></args></vm>
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
    <engine protocol="uci" protover="1" binname="rybka">
        <meta><country>ru</country></meta></engine>
    <engine protocol="uci" protover="1" binname="hiarcs">
        <meta><country>gb</country></meta></engine>
</engines>
""" % ENGINES_XML_API_VERSION

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
        self.xmlpath = addHomePrefix("engines.xml")
        try:
            self.dom = ET.ElementTree(file=self.xmlpath)
            c = compareVersions(self.dom.getroot().get('version'), ENGINES_XML_API_VERSION)
            if c == -1:
                log.warn("engineNest: engines.xml is outdated. It will be replaced\n")
                self.dom = deepcopy(self.backup)
            elif c == 1:
                raise NotImplementedError, "engines.xml is of a newer date. In order" + \
                                "to run this version of PyChess it must first be removed"
        except ExpatError, e:
            log.warn("engineNest: %s\n" % e)
            self.dom = deepcopy(self.backup)
        except IOError, e:
            log.log("engineNest: Couldn\'t open engines.xml. Creating a new.\n%s\n" % e)
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
        
        if engine.find('vm') != None:
            vmpath = searchPath(engine.find('vm').get('binname'), access=os.R_OK|os.X_OK)
            if engine.get('binname') != "PyChess.py":
                path = searchPath(engine.get('binname'), access=os.R_OK)
            else:
                path = join(abspath(dirname(__file__)), "PyChess.py")
                if not os.access(path, os.R_OK):
                    path = None
            if vmpath and path:
                return vmpath, path
        else:
            path = searchPath(engine.get('binname'), access=os.R_OK|os.X_OK)
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
            option = fromstring('<%s-option/>' % dic['type'])
            optnode.append(option)
            for key, value in dic.iteritems():
                if key == 'type': continue
                if key != 'vars':
                    option.attrib[key] = str(value)
                else:
                    for subvalue in value:
                        option.append(fromstring('<var name="%s" />' % subvalue))
        
        return engine
    
    def __fromCECPProcess (self, subprocess):
        features = subprocess.features
        engine = fromstring('<engine><meta/><cecp-features/><options/></engine>')
        
        meta = engine.find('meta')
        if "name" in features:
            meta.append(fromstring('<name>%s</name>' % features['myname']))
        
        feanode = engine.find('cecp-features')
        for key, value in features.iteritems():
            feanode.append(fromstring('<feature name="%s" value="%s"/>' % (key, value)))
        
        optnode = engine.find('options')
        optnode.append(fromstring('<check-option name="Ponder" default="false"/>'))
        optnode.append(fromstring('<check-option name="Random" default="false"/>'))
        optnode.append(fromstring('<spin-option name="Depth" min="1" max="-1" default="false"/>'))
        
        return engine
    
    def __discoverE (self, engine):
        subproc = self.initEngine (engine, BLACK)
        try:
            # We could also use readyForOptions, but then we would have to wait
            # for the readyForMoves signal, before we could shut the engine...
            subproc.connect('readyForOptions', self.__discoverE2, engine)
            subproc.prestart() # Sends the 'start line'
        except SubProcessError, e:
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
        if engine.find("path") == None or engine.find("path").text != path:
            return True
        # If the engine failed last time, we'll recheck it as well
        if engine.get('recheck') == "true":
            return True
        
        # Check if md5sum is not set, or if it has changed
        if engine.find("md5") == None:
            return True
        with open(path) as f:
            md5sum = md5(f.read()).hexdigest()
        if engine.find("md5").text != md5sum:
            return True
        
        return False
    
    def __clean(self, rundata, engine):
        """ Grab the engine from the backup and attach the attributes from
            rundata. The 'new' engine is returned and ready for discovering """
        
        vmpath, path = rundata
        
        with open(path) as f:
            md5sum = md5(f.read()).hexdigest()
        
        ######
        # Vind the backup engine
        ######
        try:
            engine2 = (c for c in self.backup.findall('engine')
                       if c.get('binname') == engine.get('binname')).next()
        except StopIteration:
            log.warn("Engine '%s' is no longer suported" % engine.get('binname'))
            return None
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
    
    def run (self):
        # List available engines
        for engine in self.dom.findall('engine'):
            ######
            # Find the known and installed engines on the system
            ######
            
            # Validate slihtly
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
                if not engine2:
                    # No longer suported
                    continue
                self.dom.getroot().remove(engine)
                self.dom.getroot().append(engine2)
                engine = engine2
                engine.set('recheck', 'true')
            
            self._engines[engine.get("binname")] = engine
        
        ######
        # Save the xml
        ######
        def cb(self_, *args):
            try:
                with open(self.xmlpath, "w") as f:
                    self.dom.write(f)
            except IOError, e:
                log.error("Saving enginexml raised exception: %s\n" % \
                          ", ".join(str(a) for a in e.args))
        
        ######
        # Runs all the engines in toBeRechecked, in order to gather information
        ######
        
        toBeRechecked = [c for c in self.dom.findall('engine')
                         if c.get('recheck') == 'true']
        # Waiting for etree 1.3 to get into python, before we can use xpath
        # toBeRechecked = self.dom.findall('engine[recheck=true]')
        
        self.counter_ = 0
        def count(self_, binname, engine):
            self.counter_ += 1
            if self.counter_ == len(toBeRechecked):
                self.emit("all_engines_discovered")
        self.connect("engine_discovered", count)
        self.connect("engine_failed", count)
        
        if toBeRechecked:
            binnames = [engine.get('binname') for engine in toBeRechecked] 
            self.emit("discovering_started", binnames)
            for engine in toBeRechecked:
                self.__discoverE(engine)
            self.connect("all_engines_discovered", cb)
            #self.emit("all_engines_discovered")
        else:
            self.emit('all_engines_discovered')
        
        
    
    ############################################################################
    # Interaction                                                              #
    ############################################################################
    
    def getAnalyzers (self):
        for engine in self.getEngines().values():
            protocol = engine.get("protocol")
            if protocol == "uci":
                yield engine
            elif protocol == "cecp":
                if any(True for f in engine.findall('cecp-features/feature') if
                       f.get('name') == 'analyze' and f.get('value') == '1'):
                    yield engine
    
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
            if md5 == None: continue
            if md5.text.strip() == md5sum:
                return engine
    
    def getEngineVariants (self, engine):
        for variantClass in variants.values():
            if variantClass.standard_rules:
                yield variantClass.board.variant
            else:
                for feature in engine.findall("cecp-features/feature"):
                    if feature.get("name") == "variants":
                        if variantClass.cecp_name == feature.get('value'):
                            yield variantClass.board.variant
                # UCI knows Chess960 only
                if variantClass.cecp_name == "fischerandom":
                    for option in engine.findall('options/check-option'):
                        if option.get("name") == "UCI_Chess960":
                            yield variantClass.board.variant
    
    def getName (self, engine=None):
        # Test if the call was to get the name of the thread
        if engine == None:
            return Thread.getName(self)
        
        name = engine.find("meta/name")
        if name != None:
            return name.text.strip()
        return engine.get('binname')
    
    def getCountry (self, engine):
        country = engine.find('meta/country')
        if country != None:
            return country.text.strip()
        return None
   
    def initEngine (self, xmlengine, color):
        protover = int(xmlengine.get("protover"))
        protocol = xmlengine.get("protocol")
        
        path = xmlengine.find('path').text.strip()
        args = [a.get('value') for a in xmlengine.findall('args/arg')]
        if xmlengine.find('vm') != None:
            vmpath = xmlengine.find('vm/path').text.strip()
            vmargs = [a.get('value') for a in xmlengine.findall('vm/args/arg')]
            args = vmargs+[path]+args
            path = vmpath
        
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
