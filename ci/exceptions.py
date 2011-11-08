class CommandError(Exception):
    def __init__(self, msg, command):
        super(CommandError, self).__init__(msg)
        self.command = command
