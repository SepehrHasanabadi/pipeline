from pipeline import Pipeline


if __name__ == "__main__":
    p = Pipeline()
    p.add_instruction('ADD R1 R2 R3')
    p.add_instruction('SUB R4 R5 R6')
    p.add_instruction('AND R7 R8 R9')
    p.add_instruction('OR R10 R11 R12')
    p.add_instruction('XOR R13 R14 R15')
    p.run()
