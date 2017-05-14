#! /usr/bin/env python
from __future__ import print_function

import subprocess


class Command(object):
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

        try:
            self.output, self.error = self.process.communicate(
                input=self.inputstr,
                timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.output, self.error = self.process.communicate()
        self.status = self.process.returncode

        return self.status, self.output, self.error


if __name__ == "__main__":
    command = Command("DC", "xboard\nprotover 2\n")
    command = Command("DC", "uci\n")
    print(command.run(timeout=3))
