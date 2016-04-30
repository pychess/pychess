import inspect
import sys

from pychess.compat import basestring


def fident(f):
    '''
    Get an identifier for a function or method
    '''
    joinchar = '.'
    if hasattr(f, 'im_class'):
        fparent = f.im_class.__name__
    else:
        joinchar = ':'
        fparent = f.__module__.split('.')[-1]

    # sometimes inspect.getsourcelines() segfaults on windows
    if getattr(sys, 'frozen', False) or sys.platform == "win32":
        lineno = 0
    else:
        lineno = inspect.getsourcelines(f)[1]

    fullname = joinchar.join((fparent, f.__name__))
    return ':'.join((fullname, str(lineno)))


def get_threadname(thread_namer):
    if isinstance(thread_namer, basestring):
        return thread_namer
    else:
        return fident(thread_namer)


# https://gist.github.com/techtonik/2151727
def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)   # function or a method
    del parentframe
    return ".".join(name)
