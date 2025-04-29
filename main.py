from pipeline import Pipeline

p = Pipeline()

def text_raw_hazard():
    p.add_instruction('ADD R1 R2 R3')
    p.add_instruction('SUB R3 R1 R4')

if __name__ == "__main__":
    text_raw_hazard()
    p.run()
