import subprocess


class Command():
    def __init__(self, command, inputstr):
        self.command = command
        self.inputstr = inputstr

    def run(self, timeout=None):
        """ Run a command then return: (status, output, error). """
        status = None
        output = ""
        error = ""
        try:
            process = subprocess.Popen(self.command,
                                       universal_newlines=True,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        except OSError:
            return status, output, error
        except ValueError:
            return status, output, error

        try:
            output, error = process.communicate(
                input=self.inputstr,
                timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            output, error = process.communicate()

        status = process.returncode
        return status, output, error
