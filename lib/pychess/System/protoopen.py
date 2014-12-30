import urllib, os

def splitUri (uri):
    uri = urllib.url2pathname(uri) # escape special chars
    uri = uri.strip('\r\n\x00') # remove \r\n and NULL
    return uri.split("://")

def protoopen (uri):
    """ Function for opening many things """
   
    try:
        return open(uri, "rU")
    except (IOError, OSError):
        pass

    try:
        return urllib.urlopen(uri)
    except (IOError, OSError):
        pass

    raise IOError("Protocol isn't supported by pychess")

def protosave (uri, append=False):
    """ Function for saving many things """
    
    splitted = splitUri(uri)
    
    if splitted[0] == "file":
        if append:
            return file(splitted[1], "a")
        return file(splitted[1], "w")
    elif len(splitted) == 1:
        if append:
            return file(splitted[0], "a")
        return file(splitted[0], "w")

    raise IOError("PyChess doesn't support writing to protocol")

def isWriteable (uri):
    """ Returns true if protoopen can open a write pipe to the uri """
    
    splitted = splitUri(uri)
    
    if splitted[0] == "file":
        return os.access (splitted[1], os.W_OK)
    elif len(splitted) == 1:
        return os.access (splitted[0], os.W_OK)
    
    return False
