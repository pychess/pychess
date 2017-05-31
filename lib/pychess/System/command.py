#! /usr/bin/env python

import asyncio


class Command(object):
    command = None
    inputstr = None
    process = None
    status = None
    output, error = '', ''

    def __init__(self, command, inputstr):
        self.command = command
        self.inputstr = inputstr

    def run(self, timeout=None):

        def coro(timeout):
            p = yield from asyncio.create_subprocess_exec(*self.command,
                                                          stdin=asyncio.subprocess.PIPE,
                                                          stdout=asyncio.subprocess.PIPE)
            task = asyncio.async(p.communicate(input=self.inputstr))
            done, pending = yield from asyncio.wait([task], timeout=timeout)
            if pending:
                print("timeout!", task._state)
            res = yield from task  # Note: It is OK to await a task more than once
            return p.returncode, res[0].decode(), res[1]

        loop = asyncio.get_event_loop()
        ret = loop.run_until_complete(coro(timeout))
        return ret


if __name__ == "__main__":
    command = Command("DC", "xboard\nprotover 2\nquit\n")
    command = Command("DC", "uci\nquit\n")
    print(command.run(timeout=3))
