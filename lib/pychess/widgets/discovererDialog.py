import os

import gtk.glade
 
from pychess.System import conf
from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix
from pychess.System.glock import glock_connect
from pychess.Players.engineNest import discoverer

from Throbber import Throbber

uistuff.cacheGladefile("discovererDialog.glade")

class DiscovererDialog:
    
    @classmethod
    def show (cls, discoverer, binnames, mainwindow):
        assert not hasattr(cls, "widgets"), "Show can only be called once"
        cls.widgets = uistuff.GladeWidgets("discovererDialog.glade")
        
        #=======================================================================
        # Add throbber
        #=======================================================================
        
        throbber = Throbber(100, 100)
        throbber.set_size_request(100, 100)
        cls.widgets["throbberDock"].add(throbber)
        
        #=======================================================================
        # Clear glade defaults, and insert the names to be discovered
        #=======================================================================
        for child in cls.widgets["enginesTable"].get_children():
            cls.widgets["enginesTable"].remove(child)
        
        cls.nameToBar = {}
        for i, name in enumerate(binnames):
            label = gtk.Label(name+":")
            label.props.xalign = 1
            cls.widgets["enginesTable"].attach(label, 0, 1, i, i+1)
            bar = gtk.ProgressBar()
            cls.widgets["enginesTable"].attach(bar, 1, 2, i, i+1)
            cls.nameToBar[name] = bar
        
        #=======================================================================
        # Connect us to the discoverer
        #=======================================================================
        glock_connect(discoverer, "engine_discovered", cls._onEngineDiscovered)
        glock_connect(discoverer, "all_engines_discovered", cls._onAllEnginesDiscovered)
        
        #=======================================================================
        # Show the window
        #=======================================================================
        cls.widgets["discovererDialog"].set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        cls.widgets["discovererDialog"].set_modal(True)
        cls.widgets["discovererDialog"].set_transient_for(mainwindow)
        cls.widgets["discovererDialog"].show_all()
    
    
    @classmethod
    def _onEngineDiscovered (cls, discoverer, binname, xmlenginevalue):
        bar = cls.nameToBar[binname]
        bar.props.fraction = 1
    
    @classmethod
    def _onAllEnginesDiscovered (cls, discoverer):
        cls.widgets["discovererDialog"].hide()
