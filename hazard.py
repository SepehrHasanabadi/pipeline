class Hazard:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.forwarding = False
        self.stall = 0
        self.forward = 0

    # should return boolean indicates if hazard occurs, the pipeline
    # should be rectifed if hazard exists.
    def control_hazards(self):
        return False

    def structural_hazards(self):
        return False

    def raw_hazards(self):
        inst1 = self.pipeline.pipeline[1]  # ID stage (the reader)
        if not inst1 or (inst1.source1 is None and inst1.source2 is None):
            return False

        # Check against writers in EX, MEM, WB
        for j in range(2, 5):
            inst2 = self.pipeline.pipeline[j]
            if not inst2 or inst2.destination is None:
                continue
            if inst1.source1 == inst2.destination or inst1.source2 == inst2.destination:
                if self.forwarding:
                    self.forward += 1
                    return False
                self.pipeline.move_instructions(from_index=j)
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
