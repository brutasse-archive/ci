class BuildException(Exception):
    def __init__(self, msg, command):
        self.command = command
        super(BuildException, self).__init__(msg)
