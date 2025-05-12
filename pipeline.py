from instruction import Instruction
from hazard import Hazard


class Pipeline:
    def __init__(self):
        self.stages = ["IF", "ID", "EX", "MEM", "WB"]
        self.pipeline = [None, None, [], None, []]
        self.clock = 0
        self.instructions = []
        self.completed_instructions = []
        self.instruction_pointer = 0
        self.hazard = Hazard(self)
        self.branch_inst = True

    def add_instruction(self, instruction_name, exe_clock=1):
        self.instructions.append(Instruction(instruction_name, exe_clock))

    def move_instructions(self, from_index=0):
        max_order = max([obj.order for obj in self.pipeline[-1]], default=None)
        self.pipeline[-1] = [obj for obj in self.pipeline[-1] if obj.order != max_order]
        for i in range(len(self.stages) - 1, from_index, -1):
            if i == 2:  # Ex stage
                for item in self.pipeline[i]:
                    item.execution_clock -= 1
                    item.order += 1
                if self.pipeline[i - 1]:
                    inst = self.pipeline[i - 1]
                    inst.execution_clock -= 1
                    inst.stage = self.stages[i]
                    self.pipeline[i].append(inst)
                    self.pipeline[i - 1] = None
            elif i == 3:  # Mem stage
                for idx, item in enumerate(self.pipeline[i - 1] or []):
                    if item.execution_clock <= 0:
                        inst = self.pipeline[2].pop(idx)
                        self.pipeline[i] = inst
                        inst.stage = self.stages[i]
                        break
            elif i == 4 and self.pipeline[i - 1]:
                inst = self.pipeline[i - 1]
                inst.stage = self.stages[i]
                self.pipeline[i].append(inst)
                self.pipeline[i - 1] = None
            elif self.pipeline[i - 1]:
                self.pipeline[i] = self.pipeline[i - 1]
                self.pipeline[i - 1] = None
                self.pipeline[i].stage = self.stages[i]

    def insert_instruction(self):
        if (
            self.instructions
            and self.pipeline[0] is None
            and self.instruction_pointer < len(self.instructions)
        ):
            new_instr = self.instructions[self.instruction_pointer]
            self.pipeline[0] = new_instr
            new_instr.stage = "IF"
            self.instruction_pointer += 1

    def step(self):
        self.clock += 1
        print(f"\nClock Cycle {self.clock}:")

        valid = self.hazard.validate()
        if valid:
            self.move_instructions()

        self.insert_instruction()
        self.print_pipeline()

    def print_pipeline(self):
        for idx, instr in enumerate(self.pipeline):
            stage_name = self.stages[idx]
            if instr:
                print(f"{stage_name}: {instr}")
            else:
                print(f"{stage_name}: Empty")

    def run(self):
        any_inst = False
        while self.instruction_pointer < len(self.instructions) or any_inst:
            any_inst = False
            for item in self.pipeline:
                if isinstance(item, list):
                    any_inst = any(item)
                elif item is not None:
                    any_inst = True
                if any_inst:
                    break
            if self.instruction_pointer < len(self.instructions) or any_inst:
                self.step()
        
        print(f"\nStall Numbers: {self.hazard.stall}")
        print(f"Forward Numbers: {self.hazard.forward}")
        print(f"Cycles: {self.clock}")
