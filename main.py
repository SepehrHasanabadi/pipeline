from pipeline import Pipeline

p = Pipeline()


def inst_raw_hazard():
    p.add_instruction("ADD R1 R2 R3", 1)
    p.add_instruction("SUB R3 R1 R4", 1)


def inst_control_hazard():
    p.branch_inst = True
    p.add_instruction("BEQ R1 R2 LABEL", 1)
    p.add_instruction("ADD R3 R4 R5")
    p.add_instruction("SUB R6 R7 R8")
    p.add_instruction("SUB R9 R10 R11")
    p.add_instruction("SUB R12 R13 R14")
    p.add_instruction("LABEL: MUL R9 R10 R11")


def inst_structural_hazard():
    p.add_instruction("MUL R1 R2 R3", 2)
    p.add_instruction("MUL R4 R5 R6", 2)



def inst_waw_hazard():
    p.add_instruction("ADD R1 R2 R3", 1)
    p.add_instruction("SUB R1 R4 R5", 1)


def inst_war_hazard():
    p.add_instruction("ADD R2 R3 R4", 2)
    p.add_instruction("SUB R5 R2 R6", 1)


if __name__ == "__main__":
    # inst_raw_hazard()
    # inst_control_hazard()
    #inst_structural_hazard()
    #inst_waw_hazard()
    inst_war_hazard()

    p.run()
