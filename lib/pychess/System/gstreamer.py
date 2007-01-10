# GstPlayer is borrowed from istanbul

import pygst
pygst.require('0.10')
import gst

class GstPlayer:
    def __init__(self, uri):
        self.playing = False
        self.player = gst.element_factory_make("playbin", "player")
        self.on_eos = False
        self.player.set_property('uri', uri)
        
        self.bus = self.player.get_bus()
        self.bus.enable_sync_message_emission()
        self.bus.add_signal_watch()
        self.bus.connect('sync-message::element', self.on_sync_message)
        self.bus.connect('message', self.on_message)
    
    def on_sync_message(self, bus, message):
        if message.structure is None: return
        if message.structure.get_name() == 'prepare-xwindow-id':
            message.src.set_property('force-aspect-ratio', True)
    
    def on_message(self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            gerror, debug = message.parse_error()
            m = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE, _("Error playing sound"))
            m.format_secondary_text(
                _('There was an error playing: %s\n\nDebug Information:\n%s') % (
                    gerror, debug))
            self.playing = False
        
        elif message.type == gst.MESSAGE_EOS:
            self.playing = False
            
    def play(self):
        gst.info("playing player")
        self.player.set_state(gst.STATE_PLAYING)
        self.playing = True

from threading import Lock
lock = Lock()
def playSound (uri):
    # If you run this to many time, it'll crash the program with some strange
    # GThread-ERROR **: file gthread-posix.c: line 356 (): error
    lock.acquire()
    instance = GstPlayer(uri)
    instance.play()
    lock.release()
