import sys
import time
import traceback
import threading
from threading import Thread

from pychess.System import fident
from pychess.System.Log import log

def dump_threads ():
    id2thread = {}
    for thread in threading.enumerate():
        id2thread[thread.ident] = thread
    
    stacks = []
    for thread_id, frame in sys._current_frames().items():
        stack = traceback.format_list(traceback.extract_stack(frame))
        stacks.append("Thread: %s (%d)" % (id2thread[thread_id].name, thread_id))
        stacks.append("".join(stack))
    
    log.debug("\n" + "\n".join(stacks))

def start_thread_dump ():
    def thread_dumper ():
        while True:
            dump_threads()
            time.sleep(10)
    
    t = Thread(target=thread_dumper, name=fident(thread_dumper))
    t.daemon = True
    t.start()
