
import sys
import time
import logging

from .prefix import addUserDataPrefix

newName = time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
logformat = "%(asctime)s.%(msecs)03d %(task)s %(levelname)s: %(message)s"

# delay=True argument prevents creating empty .log files
encoding = "utf-8" if sys.platform == "win32" else None
file_handler = logging.FileHandler(
    addUserDataPrefix(newName),
    delay=True,
    encoding=encoding)


class TaskFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        if not hasattr(record, "task"):
            record.task = "unknown"

        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)

        s = self._fmt % record.__dict__

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text

        return s


formatter = TaskFormatter(fmt=logformat, datefmt='%H:%M:%S')
file_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(file_handler)


class ExtraAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs["extra"] = kwargs.get("extra", {"task": "Default"})
        return msg, kwargs


log = ExtraAdapter(logger, {})


class LogPipe:
    def __init__(self, to, flag=""):
        self.to = to
        self.flag = flag

    def write(self, data):
        try:
            self.to.write(data)
            self.flush()
        except IOError:
            if self.flag == "stdout":
                # Certainly hope we never end up here
                pass
            else:
                log.error("Could not write data '%s' to pipe '%s'" %
                          (data, repr(self.to)))
        except BrokenPipeError:
            pass

        if log:
            for line in data.splitlines():
                if line:
                    log.debug(line, extra={"task": self.flag})

    def flush(self):
        self.to.flush()

    def fileno(self):
        return self.to.fileno()
