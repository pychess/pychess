#!/usr/bin/env python

import sys
import os.path

from pychess.compat import basestring


###
# Generators are not thread safe, so reduced which_files() to return the first match only !!!
###
""" Which - locate a command

    * adapted from proposal__ by Erik Demaine and patch__ by Brian Curtin, which adds this feature__ to shutil

    __ http://bugs.python.org/file8185/find_in_path.py
    __ http://bugs.python.org/file15381/shutil_which.patch
    __ http://bugs.python.org/issue444582

    * which_files() returns generator, which() returns first match,
      or raises IOError(errno.ENOENT)
    * searches current directory before ``PATH`` on Windows,
      but not before an explicitly passed path
    * accepts both string or iterable for an explicitly passed path, or pathext
    * accepts an explicitly passed empty path, or pathext (either '' or [])
    * does not search ``PATH`` for files that have a path specified in their name already
    * uses ``PATHEXT`` on Windows, providing a default value for different Windows versions

    .. function:: which_files(file [, mode=os.F_OK | os.X_OK[, path=None[, pathext=None]]])

       Generate full paths, where the *file* is accesible under *mode*
       and is located in the directory passed as a part of the *file* name,
       or in any directory on *path* if a base *file* name is passed.

       The *mode* matches an existing executable file by default.

       The *path* defaults to the ``PATH`` environment variable,
       or to :const:`os.defpath` if the ``PATH`` variable is not set.
       On Windows, a current directory is searched before directories in the ``PATH`` variable,
       but not before directories in an explicitly passed *path* string or iterable.

       The *pathext* is used to match files with any of the extensions appended to *file*.
       On Windows, it defaults to the ``PATHEXT`` environment variable.
       If the ``PATHEXT`` variable is not set, then the default *pathext* value is hardcoded
       for different Windows versions, to match the actual search performed on command execution.
       On Windows <= 4.x, ie. NT and older, it defaults to '.COM;.EXE;.BAT;.CMD'.
       On Windows 5.x, ie. 2k/XP/2003, the extensions '.VBS;.VBE;.JS;.JSE;.WSF;.WSH' are appended,
       On Windows >= 6.x, ie. Vista/2008/7, the extension '.MSC' is further appended.
       The actual search on command execution may differ under Wine_,
       which may use a `different default value`__, that is `not treated specially here`__.
       In each directory, the *file* is first searched without any additional extension,
       even when a *pathext* string or iterable is explicitly passed.

       .. _Wine: http://www.winehq.org/
       __ http://source.winehq.org/source/programs/cmd/wcmdmain.c#L1019
       __ http://wiki.winehq.org/DeveloperFaq#detect-wine

    .. function:: which(file [, mode=os.F_OK | os.X_OK[, path=None[, pathext=None]]])

       Return the first full path matched by :func:`which_files`,
       or raise :exc:`IOError` (:const:`errno.ENOENT`).
"""
__docformat__ = 'restructuredtext en'
__all__ = 'which which_files'.split()
_windows = sys.platform.startswith('win')

if _windows:

    def _getwinpathext(*winver):
        """ Return the default PATHEXT value for a particular Windows version.

            On Windows <= 4.x, ie. NT and older, it defaults to '.COM;.EXE;.BAT;.CMD'.
            On Windows 5.x, ie. 2k/XP/2003, the extensions '.VBS;.VBE;.JS;.JSE;.WSF;.WSH' are appended,
            On Windows >= 6.x, ie. Vista/2008/7, the extension '.MSC' is further appended.

            Availability: Windows

            >>> def test(extensions, *winver):
            ...     result = _getwinpathext(*winver)
            ...     expected = os.pathsep.join(['.%s' % ext.upper() for ext in extensions.split()])
            ...     assert result == expected, 'getwinpathext: %s != %s' % (result, expected)

            >>> test('com exe bat cmd', 3)
            >>> test('com exe bat cmd', 4)
            >>> test('com exe bat cmd vbs vbe js jse wsf wsh', 5)
            >>> test('com exe bat cmd vbs vbe js jse wsf wsh msc', 6)
            >>> test('com exe bat cmd vbs vbe js jse wsf wsh msc', 7)
        """
        if not winver:
            winver = sys.getwindowsversion()

        return os.pathsep.join(
            '.COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC'.split(
                ';')[:(winver[0] < 5 and 4 or winver[0] < 6 and -1 or None)])


def which_files(file, mode=os.F_OK | os.X_OK, path=None, pathext=None):
    """ Generate full paths, where the file*is accesible under mode
        and is located in the directory passed as a part of the file name,
        or in any directory on path if a base file name is passed.

        The mode matches an existing executable file by default.

        The path defaults to the PATH environment variable,
        or to os.defpath if the PATH variable is not set.
        On Windows, a current directory is searched before directories in the PATH variable,
        but not before directories in an explicitly passed path string or iterable.

        The pathext is used to match files with any of the extensions appended to file.
        On Windows, it defaults to the ``PATHEXT`` environment variable.
        If the PATHEXT variable is not set, then the default pathext value is hardcoded
        for different Windows versions, to match the actual search performed on command execution.

        On Windows <= 4.x, ie. NT and older, it defaults to '.COM;.EXE;.BAT;.CMD'.
        On Windows 5.x, ie. 2k/XP/2003, the extensions '.VBS;.VBE;.JS;.JSE;.WSF;.WSH' are appended,
        On Windows >= 6.x, ie. Vista/2008/7, the extension '.MSC' is further appended.
        The actual search on command execution may differ under Wine,
        which may use a different default value, that is not treated specially here.

        In each directory, the file is first searched without any additional extension,
        even when a pathext string or iterable is explicitly passed.

        >>> def test(expected, *args, **argd):
        ...     result = list(which_files(*args, **argd))
        ...     assert result == expected, 'which_files: %s != %s' % (result, expected)
        ...
        ...     try:
        ...         result = [ which(*args, **argd) ]
        ...     except IOError:
        ...         result = []
        ...     assert result[:1] == expected[:1], 'which: %s != %s' % (result[:1], expected[:1])

        >>> ### Set up
        >>> import stat, tempfile
        >>> dir = tempfile.mkdtemp(prefix='test-')
        >>> ext = '.ext'
        >>> tmp = tempfile.NamedTemporaryFile(prefix='command-', suffix=ext, dir=dir)
        >>> name = tmp.name
        >>> file = os.path.basename(name)
        >>> here = os.path.join(os.curdir, file)
        >>> nonexistent = '%s-nonexistent' % name
        >>> path = os.pathsep.join([ nonexistent, name,  dir, dir ])
        ... # Test also that duplicates are removed, and non-existent objects
        ... # or non-directories in path do not trigger any exceptions.

        >>> ### Test permissions
        >>> test(_windows and [name] or [], file, path=path)
        >>> test(_windows and [name] or [], file, mode=os.X_OK, path=path)
        ... # executable flag is not needed on Windows

        >>> test([name], file, mode=os.F_OK, path=path)
        >>> test([name], file, mode=os.R_OK, path=path)
        >>> test([name], file, mode=os.W_OK, path=path)
        >>> test([name], file, mode=os.R_OK|os.W_OK, path=path)

        >>> os.chmod(name, stat.S_IRWXU)
        >>> test([name], file, mode=os.R_OK|os.W_OK|os.X_OK, path=path)

        >>> ### Test paths
        >>> _save_path = os.environ.get('PATH', '')
        >>> cwd = os.getcwd()

        >>> test([], file, path='')
        >>> test([], file, path=nonexistent)
        >>> test([], nonexistent, path=path)
        >>> test([name], file, path=path)
        >>> test([name], name, path=path)
        >>> test([name], name, path='')
        >>> test([name], name, path=nonexistent)

        >>> os.chdir(dir)
        >>> test([name], file, path=path)
        >>> test([here], file, path=os.curdir)
        >>> test([name], name, path=os.curdir)
        >>> test([], file, path='')
        >>> test([], file, path=nonexistent)

        >>> os.environ['PATH'] = path
        >>> test(_windows and [here] or [name], file)
        ... # current directory is always searched first on Windows
        >>> os.environ['PATH'] = os.curdir
        >>> test([here], file)
        >>> test([name], name)
        >>> os.environ['PATH'] = ''
        >>> test(_windows and [here] or [], file)
        >>> os.environ['PATH'] = nonexistent
        >>> test(_windows and [here] or [], file)

        >>> os.chdir(cwd)
        >>> os.environ['PATH'] = path
        >>> test([name], file)
        >>> os.environ['PATH'] = _save_path

        >>> ### Test extensions
        >>> test([], file[:-4], path=path, pathext='')
        >>> test([], file[:-4], path=path, pathext=nonexistent)
        >>> test([name], file[:-4], path=path, pathext=ext)

        >>> test([name], file, path=path, pathext=ext)
        >>> test([name], file, path=path, pathext='')
        >>> test([name], file, path=path, pathext=nonexistent)

        >>> ### Tear down
        >>> tmp.close()
        >>> os.rmdir(dir)

    """
    filepath, file = os.path.split(file)

    if filepath:
        path = (filepath, )
    elif path is None:
        path = os.environ.get('PATH', os.defpath).split(os.pathsep)
        if _windows and os.curdir not in path:
            path.insert(
                0, os.curdir
            )  # current directory is always searched first on Windows
    elif isinstance(path, basestring):
        path = path.split(os.pathsep)

    if pathext is None:
        pathext = ['']
        if _windows:
            pathext += (os.environ.get('PATHEXT', '') or
                        _getwinpathext()).lower().split(os.pathsep)
    elif isinstance(pathext, basestring):
        pathext = pathext.split(os.pathsep)

    if '' not in pathext:
        pathext.insert(
            0, ''
        )  # always check command without extension, even for an explicitly passed pathext

    seen = set()
    for dir in path:
        if dir:  # only non-empty directories are searched
            id = os.path.normcase(os.path.abspath(dir))
            if id not in seen:  # each directory is searched only once
                seen.add(id)
                woex = os.path.join(dir, file)
                for ext in pathext:
                    name = woex + ext
                    if os.path.isfile(name) and os.access(name, mode):
                        return name
#                        yield name
    return None


def which(file, mode=os.F_OK | os.X_OK, path=None, pathext=None):
    """ Return the first full path matched by which_files(), or raise IOError(errno.ENOENT).

        >>> # See which_files() for a doctest.
    """
    return which_files(file, mode, path, pathext)
#    try:
#        return iter(which_files(file, mode, path, pathext)).next()
#    except StopIteration:
#        try:
#            from errno import ENOENT
#        except ImportError:
#            ENOENT = 2
#        raise IOError(ENOENT, '%s not found' % (mode & os.X_OK and 'command' or 'file'), file)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
