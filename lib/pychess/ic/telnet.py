from telnetlib import Telnet
import socket

IC_CONNECTED, IC_DISCONNECTED = range(2)

f = open("/home/thomas/ficslog", "w")
#import sys
def log (data, header=None):
    #sys.stdout.write(data)
    #sys.stdout.flush()
    f.write(data)
    f.flush()

client = None
connected = False

class LogOnError (Exception): pass

def connect (host, port, username="guest", password=""):
    
    global client, connected
    
    try:
        client = Telnet(host, port)
    except socket.gaierror, e:
        raise IOError, e.args[1]
    
    log(client.read_until("login: "), host)
    print >> client, username
    
    if username != "guest":
        r = client.expect(
            ["password: ", "login: ", "Press return to enter the server as"])
        if r[0] < 0:
            raise IOError, _("The connection was broken - got end of file message")
        elif r[0] == 1:
            raise LogOnError, _("Names can only consist of lower and upper case letters")
        elif r[0] == 2:
            raise LogOnError, _("'%s' is not a registered name") % username
        else:
            print >> client, password
    else:
        log(client.read_until("Press return"), host)
        print >> client
    
    r = client.expect(["Invalid password", "Starting FICS session"])
    log(r[2])
    if r[0] == 0:
        raise LogOnError, _("The entered password was invalid.\n\nIf you have forgot your password, try logging in as a guest and to chat channel 4 to tell the supporters that you have forgot it.\n\nIf that is by som reason not possible, please email: suppord@freechess.org")
    
    log(client.read_until("fics%"), host)
    
    connected = True
    for handler in connectHandlers:
        handler (client, IC_CONNECTED)
    
    #regexps.append("\n")
    while True:
        r = client.expect(regexps)
        log(r[2].replace("\r\n", "\n"), host)
        
        if r[0] < 0: break #EOF
        
        #log(r[2])
        
        #if r[0]+1 < len(regexps):
        handler = handlers[r[0]]
        handler (client, r[1].groups())
    
    for handler in connectHandlers:
        # Give handlers a chance no discover that the connection is closed
        handler (client, IC_DISCONNECTED)

import re
handlers = []
regexps = []
def expect (regexp, func):
    #if client:
    #    raise Exception, "Won't add more handlers to a connected client"
    handlers.append(func)
    regexps.append(re.compile(regexp))

connectHandlers = []
def connectStatus (func):
    connectHandlers.append(func)
