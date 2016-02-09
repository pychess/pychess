import sys
import time
import traceback
import threading
from threading import Thread

from pychess.System import fident
from pychess.System.Log import log


# This may cause random crashes
# https://github.com/pychess/pychess/issues/1023
def dump_threads():
    stacks = []
    for thread in threading.enumerate():
        frame = sys._current_frames()[thread.ident]
        stack = traceback.format_list(traceback.extract_stack(frame))
        stacks.append("Thread: %s (%d)" % (thread.name, thread.ident))
        stacks.append("".join(stack))

    log.debug("\n" + "\n".join(stacks))


def start_thread_dump():
    def thread_dumper():
        while True:
            dump_threads()
            time.sleep(10)

    thread = Thread(target=thread_dumper, name=fident(thread_dumper))
    thread.daemon = True
    thread.start()
