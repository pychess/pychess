import urllib, os

def splitUri (uri):
    uri = urllib.url2pathname(uri) # escape special chars
    uri = uri.strip('\r\n\x00') # remove \r\n and NULL
    return uri.split("://")

def protoopen (uri):
    """ Function for opening many things """
    
    protocol, path = splitUri(uri)
    
    if protocol == "file":
        return file(path)
    if protocol == "http":
        return urllib.urlopen(uri)
    
    raise IOError, "Protocol isn't supported by pychess"

def protosave (uri):
    """ Function for saving many things """
    
    protocol, path = splitUri(uri)
    
    if protocol == "file":
        return file(path, "w")
    
    raise IOError, "PyChess doesn't support writing to protocol"

def isWriteable (uri):
    """ Returns true if protoopen can open a write pipe to the uri """
    
    protocol, path = splitUri(uri)
    
    if protocol == "file":
        return os.access (path, os.W_OK)
    
    return False
