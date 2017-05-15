import collections
import socket
import subprocess
from asyncio import base_subprocess, futures, transports


class BaseTransport(transports.BaseTransport):
    def __init__(self, loop, sock, protocol, waiter=None, extra=None, server=None):
        if hasattr(self, '_sock'):
            return  # The joys of multiple inheritance

        transports.BaseTransport.__init__(self, extra)

        self._loop = loop
        self._sock = sock
        self._protocol = protocol
        self._server = server
        self._closing = False
        self._closing_delayed = False
        self._closed = False
        self._cancelable = set()

        if sock is not None:
            self._loop._transports[sock.fileno()] = self

        if self._server is not None:
            self._server._attach()

        def transport_async_init():
            self._protocol.connection_made(self)
            if waiter is not None and not waiter.cancelled():
                waiter.set_result(None)
        self._loop.call_soon(transport_async_init)

    def close(self):
        self._closing = True
        if not self._closing_delayed:
            self._force_close(None)

    def is_closing(self):
        return self._closing

    def set_protocol(self, protocol):
        self._protocol = protocol

    def get_protocol(self):
        return self._protocol

    def _fatal_error(self, exc, message='Fatal error on pipe transport'):
        self._loop.call_exception_handler({
            'message': message,
            'exception': exc,
            'transport': self,
            'protocol': self._protocol,
        })
        self._force_close(exc)

    def _force_close(self, exc):
        if self._closed:
            return
        self._closed = True

        # Stop all running tasks
        for cancelable in self._cancelable:
            cancelable.cancel()
        self._cancelable.clear()

        self._loop.call_soon(self._force_close_async, exc)

    def _force_close_async(self, exc):
        try:
            self._protocol.connection_lost(exc)
        finally:
            if self._sock is not None:
                self._sock.close()
                self._sock = None
            if self._server is not None:
                self._server._detach()
                self._server = None


class ReadTransport(BaseTransport, transports.ReadTransport):
    max_size = 256 * 1024

    def __init__(self, *args, **kwargs):
        BaseTransport.__init__(self, *args, **kwargs)

        self._paused = False
        self._read_fut = None
        self._loop.call_soon(self._loop_reading)

    def pause_reading(self):
        if self._closing:
            raise RuntimeError('Cannot pause_reading() when closing')
        if self._paused:
            raise RuntimeError('Already paused')
        self._paused = True

    def resume_reading(self):
        if not self._paused:
            raise RuntimeError('Not paused')
        self._paused = False
        if self._closing:
            return
        self._loop.call_soon(self._loop_reading, self._read_fut)

    def _close_read(self):
        # Separate method to allow `Transport.close()` to call us without
        # us delegating to `BaseTransport.close()`
        if self._read_fut is not None:
            self._read_fut.cancel()
            self._read_fut = None

    def close(self):
        self._close_read()

        super().close()

    def _create_read_future(self, size):
        return self._loop.sock_recv(self._sock, size)

    def _submit_read_data(self, data):
        if data:
            self._protocol.data_received(data)
        else:
            keep_open = self._protocol.eof_received()
            if not keep_open:
                self.close()

    def _loop_reading(self, fut=None):
        if self._paused:
            return
        data = None

        try:
            if fut is not None:
                assert self._read_fut is fut or (self._read_fut is None and self._closing)
                if self._read_fut in self._cancelable:
                    self._cancelable.remove(self._read_fut)
                self._read_fut = None
                data = fut.result()  # Deliver data later in "finally" clause

            if self._closing:
                # Since `.close()` has been called we ignore any read data
                data = None
                return

            if data == b'':
                # No need to reschedule on end-of-file
                return

            # Reschedule a new read
            self._read_fut = self._create_read_future(self.max_size)
            self._cancelable.add(self._read_fut)
        except ConnectionAbortedError as exc:
            if not self._closing:
                self._fatal_error(exc, 'Fatal read error on pipe transport')
        except ConnectionResetError as exc:
            self._force_close(exc)
        except OSError as exc:
            self._fatal_error(exc, 'Fatal read error on pipe transport')
        except futures.CancelledError:
            if not self._closing:
                raise
        except futures.InvalidStateError:
            self._read_fut = fut
            self._cancelable.add(self._read_fut)
        else:
            self._read_fut.add_done_callback(self._loop_reading)
        finally:
            if data is not None:
                self._submit_read_data(data)


class WriteTransport(BaseTransport, transports._FlowControlMixin):
    _buffer_factory = bytearray

    def __init__(self, loop, *args, **kwargs):
        transports._FlowControlMixin.__init__(self, None, loop)
        BaseTransport.__init__(self, loop, *args, **kwargs)

        self._buffer = self._buffer_factory()
        self._buffer_empty_callbacks = set()
        self._write_fut = None
        self._eof_written = False

    def abort(self):
        self._force_close(None)

    def can_write_eof(self):
        return True

    def get_write_buffer_size(self):
        return len(self._buffer)

    def _close_write(self):
        if self._write_fut is not None:
            self._closing_delayed = True

            def transport_write_done_callback():
                self._closing_delayed = False
                self.close()
            self._buffer_empty_callbacks.add(transport_write_done_callback)

    def close(self):
        self._close_write()

        super().close()

    def write(self, data):
        if self._eof_written:
            raise RuntimeError('write_eof() already called')

        # Ignore empty data sets or requests to write to a dying connection
        if not data or self._closing:
            return

        if self._write_fut is None:  # No data is currently buffered or being sent
            self._loop_writing(data=data)
        else:
            self._buffer_add_data(data)
            self._maybe_pause_protocol()  # From _FlowControlMixin

    def _create_write_future(self, data):
        return self._loop.sock_sendall(self._sock, data)

    def _buffer_add_data(self, data):
        self._buffer.extend(data)

    def _buffer_pop_data(self):
        if len(self._buffer) > 0:
            data = self._buffer
            self._buffer = bytearray()
            return data
        else:
            return None

    def _loop_writing(self, fut=None, data=None):
        try:
            assert fut is self._write_fut
            if self._write_fut in self._cancelable:
                self._cancelable.remove(self._write_fut)
            self._write_fut = None

            # Raise possible exception stored in `fut`
            if fut:
                fut.result()

            # Use buffer as next data object if invoked from done callback
            if data is None:
                data = self._buffer_pop_data()

            if not data:
                if len(self._buffer_empty_callbacks) > 0:
                    for callback in self._buffer_empty_callbacks:
                        callback()
                    self._buffer_empty_callbacks.clear()

                self._maybe_resume_protocol()
            else:
                self._write_fut = self._create_write_future(data)
                self._cancelable.add(self._write_fut)
                if not self._write_fut.done():
                    self._write_fut.add_done_callback(self._loop_writing)
                    self._maybe_pause_protocol()
                else:
                    self._write_fut.add_done_callback(self._loop_writing)
        except ConnectionResetError as exc:
            self._force_close(exc)
        except OSError as exc:
            self._fatal_error(exc, 'Fatal write error on pipe transport')

    def write_eof(self):
        self.close()


class Transport(ReadTransport, WriteTransport):
    def __init__(self, *args, **kwargs):
        ReadTransport.__init__(self, *args, **kwargs)
        WriteTransport.__init__(self, *args, **kwargs)

        # Set expected extra attributes (available through `.get_extra_info()`)
        self._extra['socket'] = self._sock
        try:
            self._extra['sockname'] = self._sock.getsockname()
        except (OSError, AttributeError):
            pass
        if 'peername' not in self._extra:
            try:
                self._extra['peername'] = self._sock.getpeername()
            except (OSError, AttributeError) as error:
                pass

    def close(self):
        # Need to invoke both the read's and the write's part of the transport `close` function
        self._close_read()
        self._close_write()

        BaseTransport.close(self)


class SocketTransport(Transport):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def write_eof(self):
        if self._closing or self._eof_written:
            return
        self._eof_written = True

        if self._write_fut is None:
            self._sock.shutdown(socket.SHUT_WR)
        else:
            def transport_write_eof_callback():
                if not self._closing:
                    self._sock.shutdown(socket.SHUT_WR)
            self._buffer_empty_callbacks.add(transport_write_eof_callback)


class DatagramTransport(Transport, transports.DatagramTransport):
    _buffer_factory = collections.deque

    def __init__(self, loop, sock, protocol, address=None, *args, **kwargs):
        self._address = address
        super().__init__(loop, sock, protocol, *args, **kwargs)


    def _create_read_future(self, size):
        return self._loop.sock_recvfrom(self._sock, size)

    def _submit_read_data(self, args):
        (data, addr) = args

        self._protocol.datagram_received(data, addr)

    def _create_write_future(self, args):
        (data, addr) = args

        if self._address:
            return self._loop.sock_sendall(self._sock, data)
        else:
            return self._loop.sock_sendallto(self._sock, data, addr)

    def _buffer_add_data(self, args):
        (data, addr) = args

        self._buffer.append((bytes(data), addr))

    def _buffer_pop_data(self):
        if len(self._buffer) > 0:
            return self._buffer.popleft()
        else:
            return None

    def write(self, data, addr=None):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data argument must be a bytes-like object, "
                            "not {!r}".format(type(data).__name__))

        if not data or self.is_closing():
            return

        if self._address and addr not in (None, self._address):
            raise ValueError("Invalid address: must be None or {0}".format(self._address))

        # Do not copy the data yet, as we might be able to send it synchronously
        super().write((data, addr))
    sendto = write


class PipeReadTransport(ReadTransport):
    def __init__(self, loop, channel, protocol, waiter, extra):
        self._channel = channel
        self._channel.set_close_on_unref(True)
        super().__init__(loop, None, protocol, waiter, extra)

    def _create_read_future(self, size):
        return self._loop._channel_read(self._channel, size)

    def _force_close_async(self, exc):
        try:
            super()._force_close_async(exc)
        finally:
            self._channel.shutdown(True)


class PipeWriteTransport(WriteTransport):
    def __init__(self, loop, channel, protocol, waiter, extra):
        self._channel = channel
        self._channel.set_close_on_unref(True)
        super().__init__(loop, None, protocol, waiter, extra)

    def _create_write_future(self, data):
        return self._loop._channel_write(self._channel, data)

    def _force_close_async(self, exc):
        try:
            super()._force_close_async(exc)
        finally:
            self._channel.shutdown(True)


class SubprocessTransport(base_subprocess.BaseSubprocessTransport):
    def _start(self, args, shell, stdin, stdout, stderr, bufsize, **kwargs):
        self._proc = subprocess.Popen(
            args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr,
            bufsize=bufsize, **kwargs)
