class Instruction:
    def __init__(self, command, exe_clock=1):
        label = None
        try:
            label, command = command.split(":")
        except ValueError:
            pass
        name = command.strip().split(" ")[0]
        self.label = label
        self.command = command
        self.name = name
        self.stage = "IF"
        self.valid = True
        self.branch = None
        self.execution_clock = exe_clock
        self.order = 0
        self.init_source_destination(command)

    def __repr__(self):
        return self.command

    def init_source_destination(self, command):
        name, input1, input2, input3 = command.strip().split(" ")
        branch_insts = ["BEQ", "BNE", "BGTZ", "BLTZ", "BGEZ", "BLEZ"]
        if name in branch_insts:
            self.branch = input3
            self.destination = None
            self.source1 = input1
            self.source2 = input2
        else:
            self.destination = input1
            self.source1 = input2
            self.source2 = input3

    def noop_instuction(self):
        self.command = "NO_OP"
        self.name = "NO_OP"
        self.execution_clock = 0
        self.destination = None
        self.source1 = None
        self.source2 = None
