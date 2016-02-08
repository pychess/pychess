#! /usr/bin/env python
from __future__ import print_function

import sys
import threading
import subprocess
import traceback


class Command(object):
    """
    Enables to run subprocess commands in a different thread with TIMEOUT option.

    Based on jcollado's solution:
    http://stackoverflow.com/questions/1191374/subprocess-with-timeout/4825933#4825933
    """
    command = None
    inputstr = None
    process = None
    status = None
    output, error = '', ''

    def __init__(self, command, inputstr):
        self.command = command
        self.inputstr = inputstr

    def run(self, timeout=None, **kwargs):
        """ Run a command then return: (status, output, error). """

        # default stdin, stdout and stderr
        if 'stdin' not in kwargs:
            kwargs['stdin'] = subprocess.PIPE
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE

        try:
            self.process = subprocess.Popen(self.command,
                                            universal_newlines=True,
                                            **kwargs)
        except OSError:
            return self.status, self.output, self.error
        except ValueError:
            return self.status, self.output, self.error

        if sys.version_info >= (3, 3, 0):
            try:
                self.output, self.error = self.process.communicate(
                    input=self.inputstr,
                    timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.output, self.error = self.process.communicate()
            self.status = self.process.returncode
            return self.status, self.output, self.error
        else:

            def target(**kwargs):
                try:
                    self.output, self.error = self.process.communicate(
                        input=self.inputstr)
                    self.status = self.process.returncode
                except:
                    self.error = traceback.format_exc()
                    self.status = -1
            # thread
            thread = threading.Thread(target=target, kwargs=kwargs)
            thread.start()
            thread.join(timeout)
            if thread.is_alive():
                self.process.kill()
                thread.join()
            return self.status, self.output, self.error


if __name__ == "__main__":
    command = Command("DC", "xboard\nprotover 2\n")
    command = Command("DC", "uci\n")
    print(command.run(timeout=3))
