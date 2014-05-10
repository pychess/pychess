import sys
import time
import traceback
import threading

from pychess.System import glock
from pychess.System.Log import log
from pychess.System.ThreadPool import pool

def start_thread_dump ():
    def thread_dumper ():
        def dump_threads ():
            id2thread = {}
            for thread in threading.enumerate():
                id2thread[thread.ident] = thread
            
            stacks = []
            for thread_id, frame in sys._current_frames().items():
                stack = traceback.format_list(traceback.extract_stack(frame))
                if glock.has(thread=id2thread[thread_id]):
                    stacks.append("has glock")
                stacks.append("Thread: %s (%d)" % (id2thread[thread_id].name, thread_id))
                stacks.append("".join(stack))
            
            log.debug("\n" + "\n".join(stacks))
        
        while 1:
            dump_threads()
            time.sleep(10)
    
    pool.start(thread_dumper, thread_dumper)
