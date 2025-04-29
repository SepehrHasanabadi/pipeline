class Instruction:
    def __init__(self, command):
        name, destination, source1, source2 = command.split(' ')
        self.command = command
        self.name = name
        self.destination = destination
        self.source1 = source1
        self.source2 = source2 
        self.stage = 'IF'

    def __repr__(self):
        return self.command