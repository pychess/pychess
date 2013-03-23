import sys
import time
import traceback
import threading

from pychess.System.glock import gdklocks
from pychess.System.Log import log
from pychess.System.ThreadPool import pool


def start_thread_dump ():
    def thread_dumper ():
        def dump_threads ():
            id2name = {}
            for thread in threading.enumerate():
                id2name[thread.ident] = thread.name
            
            stacks = []
            for thread_id, frame in sys._current_frames().items():
                stack = traceback.format_list(traceback.extract_stack(frame))
                if thread_id in gdklocks:
                    stacks.append("Thread GdkLock count: %s" % str(gdklocks[thread_id]))
                stacks.append("Thread: %s (%d)" % (id2name[thread_id], thread_id))
                stacks.append("".join(stack))
            
            log.debug("\n".join(stacks))
        
        while 1:
            dump_threads()
            time.sleep(10)
    
    pool.start(thread_dumper)
