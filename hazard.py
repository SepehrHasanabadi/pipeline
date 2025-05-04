class Hazard:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.forwarding = False
        self.stall = 0
        self.forward = 0
        self.flush = 0

    # should return a boolean indicates if hazard occurs, the pipeline
    # should move forward in a proper manner if hazard exists.
    def control_hazards_without_branch(self):
        return False

    def control_hazards_with_branch(self):
        branch_insts = ["BEQ", "BNE", "BGTZ", "BLTZ", "BGEZ", "BLEZ"]
        instructions = self.pipeline.pipeline[2]  # EX stage
        for instruction in instructions:
            if instruction.name in branch_insts:
                self.pipeline.instruction_pointer = next(
                    (
                        i
                        for i, obj in enumerate(self.pipeline.instructions)
                        if obj.label == instruction.branch
                    ),
                    None,
                )
                for j in range(0, 2):
                    self.pipeline.pipeline[j].noop_instuction()
                    self.flush += 1
                self.pipeline.move_instructions()
                return True
        return False

    def control_hazards(self):
        if self.pipeline.branch_inst:
            return self.control_hazards_with_branch()
        else:
            return self.control_hazards_without_branch()

    def structural_hazards(self):
        return False

    def raw_hazards(self):
        inst1 = self.pipeline.pipeline[1]  # ID stage (the reader)
        if not inst1 or (inst1.source1 is None and inst1.source2 is None):
            return False

        all_forward_insts = []
        for item in self.pipeline.pipeline[2:]:
            if isinstance(item, list):
                all_forward_insts.extend(item)
            elif item is not None:
                all_forward_insts.append(item)
        # Check against writers in EX, MEM, WB
        for inst2 in all_forward_insts:
            if inst2.destination is None:
                continue
            if inst1.source1 == inst2.destination or inst1.source2 == inst2.destination:
                if self.forwarding:
                    self.forward += 1
                    return False
                self.pipeline.move_instructions(from_index=2)
                self.stall += 1
                return True

        return False

    def waw_hazards(self):
        return False

    def war_hazards(self):
        return False

    def validate(self):
        return not (
            self.control_hazards()
            or self.structural_hazards()
            or self.raw_hazards()
            or self.waw_hazards()
            or self.war_hazards()
        )
