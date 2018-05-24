import time
import logging

from .prefix import addUserDataPrefix

newName = time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
logformat = "%(asctime)s.%(msecs)03d %(task)s %(levelname)s: %(message)s"

# delay=True argument prevents creating empty .log files
file_handler = logging.FileHandler(
    addUserDataPrefix(newName),
    delay=True,
    encoding="utf-8")


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


class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)

    def flush(self):
        pass


def setup_glib_logging():
    """ Code from https://github.com/GNOME/meld/blob/master/bin/meld """
    from gi.repository import GLib
    levels = {
        GLib.LogLevelFlags.LEVEL_DEBUG: logging.DEBUG,
        GLib.LogLevelFlags.LEVEL_INFO: logging.INFO,
        GLib.LogLevelFlags.LEVEL_MESSAGE: logging.INFO,
        GLib.LogLevelFlags.LEVEL_WARNING: logging.WARNING,
        GLib.LogLevelFlags.LEVEL_ERROR: logging.ERROR,
        GLib.LogLevelFlags.LEVEL_CRITICAL: logging.CRITICAL,
    }

    # Just to make sphinx happy...
    try:
        level_flag = (
            GLib.LogLevelFlags.LEVEL_WARNING |
            GLib.LogLevelFlags.LEVEL_ERROR |
            GLib.LogLevelFlags.LEVEL_CRITICAL
        )
    except TypeError:
        level_flag = GLib.LogLevelFlags.LEVEL_INFO

    log_domain = "Gtk"
    log = logging.getLogger(log_domain)

    def silence(message):
        if "gtk_container_remove: assertion" in message:
            # Looks like it was some hackish code in GTK+ which is now removed:
            # https://git.gnome.org/browse/gtk+/commit/?id=a3805333361fee37a3b1a974cfa6452a85169f08
            return True
        elif "GdkPixbuf" in message:
            return True
        return False

    # This logging handler is for "old" glib logging using a simple
    # syslog-style API.
    def log_adapter(domain, level, message, user_data):
        if not silence(message):
            log.log(levels.get(level, logging.WARNING), message)

    try:
        GLib.log_set_handler(log_domain, level_flag, log_adapter, None)
    except AttributeError:
        # Only present in glib 2.46+
        pass

    # This logging handler is for new glib logging using a structured
    # API. Unfortunately, it was added in such a way that the old
    # redirection API became a no-op, so we need to hack both of these
    # handlers to get it to work.
    def structured_log_adapter(level, fields, field_count, user_data):
        try:
            message = GLib.log_writer_format_fields(level, fields, True)
        except UnicodeDecodeError:
            for field in fields:
                print(field.key, field.value)
            return GLib.LogWriterOutput.HANDLED

        if not silence(message):
            log.log(levels.get(level, logging.WARNING), message)
        return GLib.LogWriterOutput.HANDLED

    try:
        GLib.log_set_writer_func(structured_log_adapter, None)
    except AttributeError:
        # Only present in glib 2.50+
        pass
