# -*- coding: UTF-8 -*-
"""PEP 3156 event loop based on GLib"""

import asyncio
import os
import signal
import socket
import sys
import threading
import weakref
from asyncio import constants, events, futures, sslproto, tasks

from gi.repository import GLib, Gio

from . import transports


if hasattr(os, 'set_blocking'):
    def _set_nonblocking(fd):
        os.set_blocking(fd, False)
elif sys.platform == 'win32':
    def _set_nonblocking(fd):
        pass
else:
    import fcntl

    def _set_nonblocking(fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        flags = flags | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)

__all__ = ['GLibEventLoop', 'GLibEventLoopPolicy']


# The Windows `asyncio` implementation doesn't actually use this, but
# `glib` abstracts so nicely over this that we can use it on any platform
if sys.platform == "win32":
    class AbstractChildWatcher:
        pass
else:
    from asyncio.unix_events import AbstractChildWatcher


class GLibChildWatcher(AbstractChildWatcher):
    def __init__(self):
        self._sources = {}
        self._handles = {}

    # On windows on has to open a process handle for the given PID number
    # before it's possible to use GLib's `child_watch_add` on it
    if sys.platform == "win32":

        def _create_handle_for_pid(self, pid):
            import _winapi
            return _winapi.OpenProcess(0x00100400, 0, pid)

        def _close_process_handle(self, handle):
            import _winapi
            _winapi.CloseHandle(handle)
    else:
        _create_handle_for_pid = lambda self, pid: pid
        _close_process_handle = lambda self, pid: None

    def attach_loop(self, loop):
        # just ignored
        pass

    def add_child_handler(self, pid, callback, *args):
        self.remove_child_handler(pid)

        handle = self._create_handle_for_pid(pid)
        source = GLib.child_watch_add(0, handle, self.__callback__)
        self._sources[pid] = source, callback, args, handle
        self._handles[handle] = pid

    def remove_child_handler(self, pid):
        try:
            source, callback, args, handle = self._sources.pop(pid)
            assert self._handles.pop(handle) == pid
        except KeyError:
            return False

        self._close_process_handle(handle)
        GLib.source_remove(source)
        return True

    def close(self):
        for source, callback, args, handle in self._sources.values():
            self._close_process_handle(handle)
            GLib.source_remove(source)
        self._sources = {}
        self._handles = {}

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass

    def __callback__(self, handle, status):
        try:
            pid = self._handles.pop(handle)
            source, callback, args, handle = self._sources.pop(pid)
        except KeyError:
            return

        self._close_process_handle(handle)
        GLib.source_remove(source)

        if hasattr(os, "WIFSIGNALED") and os.WIFSIGNALED(status):
            returncode = -os.WTERMSIG(status)
        elif hasattr(os, "WIFEXITED") and os.WIFEXITED(status):
            returncode = os.WEXITSTATUS(status)

            # FIXME: Hack for adjusting invalid status returned by GLIB
            #    Looks like there is a bug in glib or in pygobject
            if returncode > 128:
                returncode = 128 - returncode
        else:
            returncode = status

        callback(pid, returncode, *args)


class GLibHandle(events.Handle):
    __slots__ = ('_source', '_repeat', '_context')

    def __init__(self, *, loop, source, repeat, callback, args, context=None):
        super().__init__(callback, args, loop)

        if sys.version_info[:2] >= (3, 7) and context is None:
            import contextvars
            context = contextvars.copy_context()
        self._context = context
        self._source = source
        self._repeat = repeat
        loop._handlers.add(self)
        source.set_callback(self.__callback__, self)
        source.attach(loop._context)

    def cancel(self):
        super().cancel()
        self._source.destroy()
        self._loop._handlers.discard(self)

    def __callback__(self, ignore_self):
        # __callback__ is called within the MainContext object, which is
        # important in case that code includes a `Gtk.main()` or some such.
        # Otherwise what happens is the loop is started recursively, but the
        # callbacks don't finish firing, so they can't be rescheduled.
        self._run()
        if not self._repeat:
            self._source.destroy()
            self._loop._handlers.discard(self)

        return self._repeat


if sys.platform == "win32":
    class GLibBaseEventLoopPlatformExt:
        def __init__(self):
            pass

        def close(self):
            pass
else:
    from asyncio import unix_events

    class GLibBaseEventLoopPlatformExt(unix_events.SelectorEventLoop):
        """
        Semi-hack that allows us to leverage the existing implementation of Unix domain sockets
        without having to actually implement a selector based event loop.

        Note that both `__init__` and `close` DO NOT and SHOULD NOT ever call their parent
        implementation!
        """
        def __init__(self):
            self._sighandlers = {}

        def close(self):
            for sig in list(self._sighandlers):
                self.remove_signal_handler(sig)

        def add_signal_handler(self, sig, callback, *args):
            self.remove_signal_handler(sig)

            s = GLib.unix_signal_source_new(sig)
            if s is None:
                # Show custom error messages for signal that are uncatchable
                if sig == signal.SIGKILL:
                    raise RuntimeError("cannot catch SIGKILL")
                elif sig == signal.SIGSTOP:
                    raise RuntimeError("cannot catch SIGSTOP")
                else:
                    raise ValueError("signal not supported")

            assert sig not in self._sighandlers

            self._sighandlers[sig] = GLibHandle(
                loop=self,
                source=s,
                repeat=True,
                callback=callback,
                args=args)

        def remove_signal_handler(self, sig):
            try:
                self._sighandlers.pop(sig).cancel()
                return True
            except KeyError:
                return False


class _BaseEventLoop(asyncio.BaseEventLoop):
    """
    Extra inheritance step that needs to be inserted so that we only ever indirectly inherit from
    `asyncio.BaseEventLoop`. This is necessary as the Unix implementation will also indirectly
    inherit from that class (thereby creating diamond inheritance).
    Python permits and fully supports diamond inheritance so this is not a problem. However it
    is, on the other hand, not permitted to inherit from a class both directly *and* indirectly –
    hence we add this intermediate class to make sure that can never happen (see
    https://stackoverflow.com/q/29214888 for a minimal example a forbidden inheritance tree) and
    https://www.python.org/download/releases/2.3/mro/ for some extensive documentation of the
    allowed inheritance structures in python.
    """


class GLibBaseEventLoop(_BaseEventLoop, GLibBaseEventLoopPlatformExt):
    def __init__(self, context=None):
        self._handlers = set()

        self._accept_futures = {}
        self._context = context or GLib.MainContext()
        self._selector = self
        self._transports = weakref.WeakValueDictionary()
        self._readers = {}
        self._writers = {}

        self._channels = weakref.WeakValueDictionary()

        _BaseEventLoop.__init__(self)
        GLibBaseEventLoopPlatformExt.__init__(self)

    def close(self):
        for future in self._accept_futures.values():
            future.cancel()
        self._accept_futures.clear()

        for s in list(self._handlers):
            s.cancel()
        self._handlers.clear()

        GLibBaseEventLoopPlatformExt.close(self)
        _BaseEventLoop.close(self)

    def select(self, timeout=None):
        self._context.acquire()
        try:
            if timeout is None:
                self._context.iteration(True)
            elif timeout <= 0:
                self._context.iteration(False)
            else:
                # Schedule fake callback that will trigger an event and cause the loop to terminate
                # after the given number of seconds
                handle = GLibHandle(
                        loop=self,
                        source=GLib.Timeout(timeout*1000),
                        repeat=False,
                        callback=lambda: None,
                        args=())
                try:
                    self._context.iteration(True)
                finally:
                    handle.cancel()
            return ()  # Available events are dispatched immediately and not returned
        finally:
            self._context.release()

    def _make_socket_transport(self, sock, protocol, waiter=None, *,
                               extra=None, server=None):
        """Create socket transport."""
        return transports.SocketTransport(self, sock, protocol, waiter, extra, server)

    def _make_ssl_transport(self, rawsock, protocol, sslcontext, waiter=None,
                            *, server_side=False, server_hostname=None,
                            extra=None, server=None, ssl_handshake_timeout=None):
        """Create SSL transport."""
        # sslproto._is_sslproto_available was removed from asyncio, starting from Python 3.7.
        if hasattr(sslproto, '_is_sslproto_available') and not sslproto._is_sslproto_available():
            raise NotImplementedError("Proactor event loop requires Python 3.5"
                                      " or newer (ssl.MemoryBIO) to support "
                                      "SSL")
        # Support for the ssl_handshake_timeout keyword argument was added in Python 3.7.
        extra_protocol_kwargs = {}
        if sys.version_info[:2] >= (3, 7):
            extra_protocol_kwargs['ssl_handshake_timeout'] = ssl_handshake_timeout

        ssl_protocol = sslproto.SSLProtocol(self, protocol, sslcontext, waiter,
                                            server_side, server_hostname, **extra_protocol_kwargs)
        transports.SocketTransport(self, rawsock, ssl_protocol, extra=extra, server=server)
        return ssl_protocol._app_transport

    def _make_datagram_transport(self, sock, protocol,
                                 address=None, waiter=None, extra=None):
        """Create datagram transport."""
        return transports.DatagramTransport(self, sock, protocol, address, waiter, extra)

    def _make_read_pipe_transport(self, pipe, protocol, waiter=None,
                                  extra=None):
        """Create read pipe transport."""
        channel = self._channel_from_fileobj(pipe)
        return transports.PipeReadTransport(self, channel, protocol, waiter, extra)

    def _make_write_pipe_transport(self, pipe, protocol, waiter=None,
                                   extra=None):
        """Create write pipe transport."""
        channel = self._channel_from_fileobj(pipe)
        return transports.PipeWriteTransport(self, channel, protocol, waiter, extra)

    @asyncio.coroutine
    def _make_subprocess_transport(self, protocol, args, shell,
                                   stdin, stdout, stderr, bufsize,
                                   extra=None, **kwargs):
        """Create subprocess transport."""
        with events.get_child_watcher() as watcher:
            waiter = asyncio.Future(loop=self)
            transport = transports.SubprocessTransport(self, protocol, args, shell,
                                                       stdin, stdout, stderr, bufsize,
                                                       waiter=waiter, extra=extra, **kwargs)

            watcher.add_child_handler(transport.get_pid(), self._child_watcher_callback, transport)
            try:
                yield from waiter
            except Exception as exc:
                err = exc
            else:
                err = None
            if err is not None:
                transport.close()
                yield from transport._wait()
                raise err

        return transport

    def _child_watcher_callback(self, pid, returncode, transport):
        self.call_soon_threadsafe(transport._process_exited, returncode)

    def _write_to_self(self):
        self._context.wakeup()

    def _process_events(self, event_list):
        """Process selector events."""
        pass  # This is already done in `.select()`

    def _start_serving(self, protocol_factory, sock,
                       sslcontext=None, server=None, backlog=100,
                       ssl_handshake_timeout=getattr(constants, 'SSL_HANDSHAKE_TIMEOUT', 60.0)):
        self._transports[sock.fileno()] = server

        def server_loop(f=None):
            try:
                if f is not None:
                    (conn, addr) = f.result()
                    protocol = protocol_factory()
                    if sslcontext is not None:
                        # FIXME: add ssl_handshake_timeout to this call once 3.7 support is merged in.
                        self._make_ssl_transport(
                            conn, protocol, sslcontext, server_side=True,
                            extra={'peername': addr}, server=server)
                    else:
                        self._make_socket_transport(
                            conn, protocol,
                            extra={'peername': addr}, server=server)
                if self.is_closed():
                    return
                f = self.sock_accept(sock)
            except OSError as exc:
                if sock.fileno() != -1:
                    self.call_exception_handler({
                        'message': 'Accept failed on a socket',
                        'exception': exc,
                        'socket': sock,
                    })
                    sock.close()
            except futures.CancelledError:
                sock.close()
            else:
                self._accept_futures[sock.fileno()] = f
                f.add_done_callback(server_loop)

        self.call_soon(server_loop)

    def _stop_serving(self, sock):
        if sock.fileno() in self._accept_futures:
            self._accept_futures[sock.fileno()].cancel()
        sock.close()

    def _check_not_coroutine(self, callback, name):
        """Check whether the given callback is a coroutine or not."""
        from asyncio import coroutines
        if (coroutines.iscoroutine(callback) or
                coroutines.iscoroutinefunction(callback)):
            raise TypeError("coroutines cannot be used with {}()".format(name))

    def _ensure_fd_no_transport(self, fd):
        """Ensure that the given file descriptor is NOT used by any transport.

        Adding another reader to a fd that is already being waited for causes a hang on Windows."""
        try:
            transport = self._transports[fd]
        except KeyError:
            pass
        else:
            if not hasattr(transport, "is_closing") or not transport.is_closing():
                raise RuntimeError('File descriptor {!r} is used by transport {!r}'
                                   .format(fd, transport))

    def _channel_from_socket(self, sock):
        """Create GLib IOChannel for the given file object.

        This function will cache weak references to `GLib.Channel` objects
        it previously has created to prevent weird issues that can occur
        when two GLib channels point to the same underlying socket resource.

        On windows this will only work for network sockets.
        """
        fd = self._fileobj_to_fd(sock)

        sock_id = id(sock)
        try:
            channel = self._channels[sock_id]
        except KeyError:
            if sys.platform == "win32":
                channel = GLib.IOChannel.win32_new_socket(fd)
            else:
                channel = GLib.IOChannel.unix_new(fd)

            # disabling buffering requires setting the encoding to None
            channel.set_encoding(None)
            channel.set_buffered(False)

            self._channels[sock_id] = channel
        return channel

    def _channel_from_fileobj(self, fileobj):
        """Create GLib IOChannel for the given file object.

        On windows this will only work for files and pipes returned GLib's C library.
        """
        fd = self._fileobj_to_fd(fileobj)

        # pipes have been shown to be blocking here, so we'll do someone
        # else's job for them.
        _set_nonblocking(fd)

        if sys.platform == "win32":
            channel = GLib.IOChannel.win32_new_fd(fd)
        else:
            channel = GLib.IOChannel.unix_new(fd)

        # disabling buffering requires setting the encoding to None
        channel.set_encoding(None)
        channel.set_buffered(False)
        return channel

    def _fileobj_to_fd(self, fileobj):
        """Obtain the raw file descriptor number for the given file object."""
        if isinstance(fileobj, int):
            fd = fileobj
        else:
            try:
                fd = int(fileobj.fileno())
            except (AttributeError, TypeError, ValueError):
                raise ValueError("Invalid file object: {!r}".format(fileobj))
        if fd < 0:
            raise ValueError("Invalid file descriptor: {}".format(fd))
        return fd

    def _delayed(self, source, callback=None, *args):
        """Create a future that will complete after the given GLib Source object has become ready
        and the data it tracks has been processed."""
        future = None

        def handle_ready(*args):
            try:
                if callback:
                    (done, result) = callback(*args)
                else:
                    (done, result) = (True, None)

                if done:
                    future.set_result(result)
                    future.handle.cancel()
            except Exception as error:
                if not future.cancelled():
                    future.set_exception(error)
                future.handle.cancel()

        # Create future and properly wire up it's cancellation with the
        # handle's cancellation machinery
        future = asyncio.Future(loop=self)
        future.handle = GLibHandle(
            loop=self,
            source=source,
            repeat=True,
            callback=handle_ready,
            args=args
        )
        return future

    def _socket_handle_errors(self, sock):
        """Raise exceptions for error states (SOL_ERROR) on the given socket object."""
        errno = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if errno != 0:
            if sys.platform == "win32":
                msg = socket.errorTab.get(errno, "Error {0}".format(errno))
                raise OSError(errno, "[WinError {0}] {1}".format(errno, msg), None, errno)
            else:
                raise OSError(errno, os.strerror(errno))

    ###############################
    # Low-level socket operations #
    ###############################
    def sock_connect(self, sock, address):
        # Request connection on socket (it is expected that `sock` is already non-blocking)
        try:
            sock.connect(address)
        except BlockingIOError:
            pass

        # Create glib IOChannel for socket and wait for it to become writable
        channel = self._channel_from_socket(sock)
        source = GLib.io_create_watch(channel, GLib.IO_OUT)

        def sock_finish_connect(sock):
            self._socket_handle_errors(sock)
            return (True, sock)
        return self._delayed(source, sock_finish_connect, sock)

    def sock_accept(self, sock):
        channel = self._channel_from_socket(sock)
        source = GLib.io_create_watch(channel, GLib.IO_IN)

        def sock_connection_received(sock):
            return (True, sock.accept())

        @asyncio.coroutine
        def accept_coro(future, conn):
            # Coroutine closing the accept socket if the future is cancelled
            try:
                return (yield from future)
            except futures.CancelledError:
                sock.close()
                raise

        future = self._delayed(source, sock_connection_received, sock)
        return self.create_task(accept_coro(future, sock))

    def sock_recv(self, sock, nbytes, flags=0):
        channel = self._channel_from_socket(sock)
        read_func = lambda channel, nbytes: sock.recv(nbytes, flags)
        return self._channel_read(channel, nbytes, read_func)

    def sock_recvfrom(self, sock, nbytes, flags=0):
        channel = self._channel_from_socket(sock)
        read_func = lambda channel, nbytes: sock.recvfrom(nbytes, flags)
        return self._channel_read(channel, nbytes, read_func)

    def sock_sendall(self, sock, buf, flags=0):
        channel = self._channel_from_socket(sock)
        write_func = lambda channel, buf: sock.send(buf, flags)
        return self._channel_write(channel, buf, write_func)

    def sock_sendallto(self, sock, buf, addr, flags=0):
        channel = self._channel_from_socket(sock)
        write_func = lambda channel, buf: sock.sendto(buf, flags, addr)
        return self._channel_write(channel, buf, write_func)

    #####################################
    # Low-level GLib.Channel operations #
    #####################################
    def _channel_read(self, channel, nbytes, read_func=None):
        if read_func is None:
            read_func = lambda channel, nbytes: channel.read(nbytes)

        source = GLib.io_create_watch(channel, GLib.IO_IN | GLib.IO_HUP)

        def channel_readable(read_func, channel, nbytes):
            return (True, read_func(channel, nbytes))
        return self._delayed(source, channel_readable, read_func, channel, nbytes)

    def _channel_write(self, channel, buf, write_func=None):
        if write_func is None:
            # note: channel.write doesn't raise BlockingIOError, instead it
            # returns 0
            # gi.overrides.GLib.write has an isinstance(buf, bytes) check, so
            # we can't give it a bytearray or a memoryview.
            write_func = lambda channel, buf: channel.write(bytes(buf))
        buflen = len(buf)

        # Fast-path: If there is enough room in the OS buffer all data can be written synchronously
        try:
            nbytes = write_func(channel, buf)
        except BlockingIOError:
            nbytes = 0
        else:
            if nbytes >= len(buf):
                # All data was written synchronously in one go
                result = asyncio.Future(loop=self)
                result.set_result(nbytes)
                return result

        # Chop off the initially transmitted data and store result
        # as a bytearray for easier future modification
        buf = bytearray(buf[nbytes:])

        # Send the remaining data asynchronously as the socket becomes writable
        source = GLib.io_create_watch(channel, GLib.IO_OUT)

        def channel_writable(buflen, write_func, channel, buf):
            nbytes = write_func(channel, buf)
            if nbytes >= len(buf):
                return (True, buflen)
            else:
                del buf[0:nbytes]
                return (False, buflen)
        return self._delayed(source, channel_writable, buflen, write_func, channel, buf)

    def add_reader(self, fileobj, callback, *args):
        fd = self._fileobj_to_fd(fileobj)
        self._ensure_fd_no_transport(fd)

        self.remove_reader(fd)
        channel = self._channel_from_socket(fd)
        source = GLib.io_create_watch(channel, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR | GLib.IO_NVAL)

        assert fd not in self._readers
        self._readers[fd] = GLibHandle(
            loop=self,
            source=source,
            repeat=True,
            callback=callback,
            args=args)

    def remove_reader(self, fileobj):
        fd = self._fileobj_to_fd(fileobj)
        self._ensure_fd_no_transport(fd)

        try:
            self._readers.pop(fd).cancel()
            return True
        except KeyError:
            return False

    def add_writer(self, fileobj, callback, *args):
        fd = self._fileobj_to_fd(fileobj)
        self._ensure_fd_no_transport(fd)

        self.remove_writer(fd)
        channel = self._channel_from_socket(fd)
        source = GLib.io_create_watch(channel, GLib.IO_OUT | GLib.IO_ERR | GLib.IO_NVAL)

        assert fd not in self._writers
        self._writers[fd] = GLibHandle(
            loop=self,
            source=source,
            repeat=True,
            callback=callback,
            args=args)

    def remove_writer(self, fileobj):
        fd = self._fileobj_to_fd(fileobj)
        self._ensure_fd_no_transport(fd)

        try:
            self._writers.pop(fd).cancel()
            return True
        except KeyError:
            return False


class GLibEventLoop(GLibBaseEventLoop):
    def __init__(self, *, context=None, application=None):
        self._application = application
        self._running = False
        self._argv = None

        super().__init__(context)
        if application is None:
            self._mainloop = GLib.MainLoop(self._context)

    def is_running(self):
        return self._running

    def run(self):
        recursive = self.is_running()
        if not recursive and hasattr(events, "_get_running_loop") and events._get_running_loop():
            raise RuntimeError(
                'Cannot run the event loop while another loop is running')

        if not recursive:
            self._running = True
            if hasattr(events, "_set_running_loop"):
                events._set_running_loop(self)

        try:
            if self._application is not None:
                self._application.run(self._argv)
            else:
                self._mainloop.run()
        finally:
            if not recursive:
                self._running = False
                if hasattr(events, "_set_running_loop"):
                    events._set_running_loop(None)

    def run_until_complete(self, future, **kw):
        """Run the event loop until a Future is done.

        Return the Future's result, or raise its exception.
        """

        def stop(f):
            self.stop()

        future = tasks.ensure_future(future, loop=self)
        future.add_done_callback(stop)
        try:
            self.run_forever(**kw)
        finally:
            future.remove_done_callback(stop)

        if not future.done():
            raise RuntimeError('Event loop stopped before Future completed.')

        return future.result()

    def run_forever(self, application=None, argv=None):
        """Run the event loop until stop() is called."""
        if application is not None:
            self.set_application(application)
        if argv is not None:
            self.set_argv(argv)

        if self.is_running():
            raise RuntimeError(
                "Recursively calling run_forever is forbidden. "
                "To recursively run the event loop, call run().")

        if hasattr(self, '_mainloop') and hasattr(self._mainloop, "_quit_by_sigint"):
            del self._mainloop._quit_by_sigint

        try:
            self.run()
        finally:
            self.stop()

    # Methods scheduling callbacks.  All these return Handles.
    def call_soon(self, callback, *args, context=None):
        self._check_not_coroutine(callback, 'call_soon')
        source = GLib.Idle()

        source.set_priority(GLib.PRIORITY_DEFAULT)

        return GLibHandle(
            loop=self,
            source=source,
            repeat=False,
            callback=callback,
            args=args,
            context=context,
        )

    call_soon_threadsafe = call_soon

    def call_later(self, delay, callback, *args, context=None):
        self._check_not_coroutine(callback, 'call_later')

        return GLibHandle(
            loop=self,
            source=GLib.Timeout(delay*1000) if delay > 0 else GLib.Idle(),
            repeat=False,
            callback=callback,
            args=args,
            context=context,
        )

    def call_at(self, when, callback, *args, context=None):
        self._check_not_coroutine(callback, 'call_at')

        return self.call_later(
            when - self.time(), callback, *args, context=context)

    def time(self):
        return GLib.get_monotonic_time() / 1000000

    def stop(self):
        """Stop the inner-most invocation of the event loop.

        Typically, this will mean stopping the event loop completely.

        Note that due to the nature of GLib's main loop, stopping may not be
        immediate.
        """

        if self._application is not None:
            self._application.quit()
        else:
            self._mainloop.quit()

    def set_application(self, application):
        if not isinstance(application, Gio.Application):
            raise TypeError("application must be a Gio.Application object")
        if self._application is not None:
            raise ValueError("application is already set")
        if self.is_running():
            raise RuntimeError("You can't add the application to a loop that's already running.")
        self._application = application
        self._policy._application = application
        del self._mainloop

    def set_argv(self, argv):
        """Sets argv to be passed to Gio.Application.run()"""
        self._argv = argv


class GLibEventLoopPolicy(events.AbstractEventLoopPolicy):
    """Default GLib event loop policy

    In this policy, each thread has its own event loop.  However, we only
    automatically create an event loop by default for the main thread; other
    threads by default have no event loop.
    """

    # TODO add a parameter to synchronise with GLib's thread default contexts
    #   (g_main_context_push_thread_default())
    def __init__(self, application=None):
        self._default_loop = None
        self._application = application
        self._watcher_lock = threading.Lock()

        self._watcher = None
        self._policy = asyncio.DefaultEventLoopPolicy()
        self._policy.new_event_loop = self.new_event_loop
        self.get_event_loop = self._policy.get_event_loop
        self.set_event_loop = self._policy.set_event_loop

    def get_child_watcher(self):
        if self._watcher is None:
            with self._watcher_lock:
                if self._watcher is None:
                    self._watcher = GLibChildWatcher()
        return self._watcher

    def set_child_watcher(self, watcher):
        """Set a child watcher.

        Must be an an instance of GLibChildWatcher, as it ties in with GLib
        appropriately.
        """

        if watcher is not None and not isinstance(watcher, GLibChildWatcher):
            raise TypeError("Only GLibChildWatcher is supported!")

        with self._watcher_lock:
            self._watcher = watcher

    def new_event_loop(self):
        """Create a new event loop and return it."""
        if not self._default_loop and isinstance(threading.current_thread(), threading._MainThread):
            l = self.get_default_loop()
        else:
            l = GLibEventLoop()
        l._policy = self

        return l

    def get_default_loop(self):
        """Get the default event loop."""
        if not self._default_loop:
            self._default_loop = self._new_default_loop()
        return self._default_loop

    def _new_default_loop(self):
        l = GLibEventLoop(context=GLib.main_context_default(), application=self._application)
        l._policy = self
        return l
