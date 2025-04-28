class Hazard:
    def __init__(self, pipeline, stages):
        self.pipeline = pipeline
        self.stages = stages
        self.forwarding = True
        self.stall = 0
        self.forward = 0

    # should return the indices of pipelines where hazard occured
    # like [0,1]. i.e the pipeline[0] and pipeline[1] experience hazards.
    def control_hazards(self):
        pass

    def structural_hazards(self):
        pass

    def raw_hazards(self):
        pass

    def waw_hazards(self):
        pass

    def war_hazards(self):
        pass

    def move_forward(self):
        self.forward += 1
        #todo: should be implemented

    def move_stall(self):
        self.stall += 1
        #todo: should be implemented

    def move_instructions(self):
        if self.forwarding:
            return self.move_forward()
        else:
            return self.move_stall()

    def validate(self):
        return True
