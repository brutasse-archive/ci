import os
import logging
import subprocess

logger = logging.getLogger('ci')


class Command(object):
    def __init__(self, command, stdin=None, environ={}):
        self.command = command
        env = os.environ
        env.update(environ)
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        logger.info("Running: '%s'" % self.command)
        self.out, self.err = self.process.communicate(stdin)
        self.return_code = self.process.returncode

    def __repr__(self):
        return '<Command: %s (%s)>' % (self.command, self.return_code)
