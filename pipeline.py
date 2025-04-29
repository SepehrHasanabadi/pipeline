from instruction import Instruction
from hazard import Hazard


class Pipeline:
    def __init__(self):
        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.pipeline = [None] * len(self.stages)
        self.clock = 0
        self.instructions = []
        self.completed_instructions = []
        self.hazard = Hazard(self)

    def add_instruction(self, instruction_name):
        self.instructions.append(Instruction(instruction_name))

    def move_instructions(self, from_index=0):
        self.pipeline[-1] = None
        for i in range(len(self.stages) - 1, from_index, -1):
            if self.pipeline[i - 1]:
                self.pipeline[i] = self.pipeline[i - 1]
                self.pipeline[i - 1] = None
                self.pipeline[i].stage = self.stages[i]

    def step(self):
        self.clock += 1
        print(f"\nClock Cycle {self.clock}:")

        valid = self.hazard.validate()
        if valid:
            self.move_instructions()

        if self.instructions and self.pipeline[0] is None:
            new_instr = self.instructions.pop(0)
            self.pipeline[0] = new_instr
            new_instr.stage = "IF"

        self.print_pipeline()

    def print_pipeline(self):
        for idx, instr in enumerate(self.pipeline):
            stage_name = self.stages[idx]
            if instr:
                print(f"{stage_name}: {instr}")
            else:
                print(f"{stage_name}: Empty")

    def run(self):
        while self.instructions or any(self.pipeline):
            self.step()
