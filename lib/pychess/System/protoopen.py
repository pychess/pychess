import os
import sys
from urllib.request import urlopen
from urllib.parse import unquote


PGN_ENCODING = "latin_1"


def splitUri(uri):
    uri = unquote(uri)  # escape special chars
    uri = uri.strip('\r\n\x00')  # remove \r\n and NULL
    if sys.platform == "win32":
        return uri.split(":///")
    else:
        return uri.split("://")


def protoopen(uri, encoding=PGN_ENCODING):
    """ Function for opening many things """
    splitted = splitUri(uri)

    if splitted[0] == "file":
        uri = splitted[1]

    try:
        handle = open(unquote(uri), "r", encoding=encoding, newline="")
        handle.pgn_encoding = "utf-8" if os.path.basename(uri).startswith("lichess_") else encoding
        return handle
    except (IOError, OSError):
        pass

    try:
        return urlopen(uri)
    except (IOError, OSError):
        pass

    raise IOError("Protocol isn't supported by pychess")


def protosave(uri, append=False):
    """ Function for saving many things """

    splitted = splitUri(uri)

    if splitted[0] == "file":
        if append:
            return open(splitted[1], "a", encoding=PGN_ENCODING, newline="")
        return open(splitted[1], "w", newline="")
    elif len(splitted) == 1:
        if append:
            return open(splitted[0], "a", encoding=PGN_ENCODING, newline="")
        return open(splitted[0], "w", encoding=PGN_ENCODING, newline="")

    raise IOError("PyChess doesn't support writing to protocol")


def isWriteable(uri):
    """ Returns true if protoopen can open a write pipe to the uri """

    splitted = splitUri(uri)

    if splitted[0] == "file":
        return os.access(splitted[1], os.W_OK)
    elif len(splitted) == 1:
        return os.access(splitted[0], os.W_OK)

    return False
