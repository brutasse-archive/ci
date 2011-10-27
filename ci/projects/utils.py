import os
import logging
import subprocess

logger = logging.getLogger('ci')


class Command(object):
    def __init__(self, command, stdin=None, environ={}, stream_to=None):
        self.command = command
        env = os.environ
        env.update(environ)
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.out = ''
        logger.info("Running: '%s'" % self.command)

        while self.process.poll() is None:
            output = self.process.stdout.readline()
            if stream_to is None:
                self.out += output
            else:
                stream_to(output)

        output, err = self.process.communicate(stdin)
        if output:
            self.out += output
        self.return_code = self.process.returncode

    def __repr__(self):
        return '<Command: %s (%s)>' % (self.command, self.return_code)
