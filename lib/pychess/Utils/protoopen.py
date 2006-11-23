import urllib

def protoopen (uri):
    """ Function for opening many things """
    
    uri = urllib.url2pathname(uri) # escape special chars
    uri = uri.strip('\r\n\x00') # remove \r\n and NULL
    
    s = uri.find("://")
    protocol = uri[:s]
    path = uri[s+3:]
    
    if protocol == "file":
        return file(path)
    if protocol == "http":
        return urllib.urlopen(uri)
    if protocol == "ftp":
        pass # We can use the gnome keymanager for finding ftp keys
