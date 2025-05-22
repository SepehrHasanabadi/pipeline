# import sys
# from collections import deque, defaultdict

ISA = {
    "LD": {"fu": "LS", "cycles": None},
    "ST": {"fu": "LS", "cycles": None},
    "BRZ": {"fu": "BR", "cycles": None},
    "BRNZ": {"fu": "BR", "cycles": None},
    "ADD": {"fu": "ALU", "cycles": None},
    "SUB": {"fu": "ALU", "cycles": None},
    "ROR": {"fu": "ALU", "cycles": None},
    "ROL": {"fu": "ALU", "cycles": None},
    "SHR": {"fu": "ALU", "cycles": None},
    "SHL": {"fu": "ALU", "cycles": None},
    "OUT": {"fu": "IO", "cycles": None},
    "AND": {"fu": "ALU", "cycles": None},
    "OR": {"fu": "ALU", "cycles": None},
    "XOR": {"fu": "ALU", "cycles": None},
    "NOT": {"fu": "ALU", "cycles": None},
    "HLT": {"fu": "CTRL", "cycles": None},
}


class Instruction:
    def __init__(self, op, dest, src1=None, src2=None):
        self.op = op
        self.dest = dest
        self.src1 = src1
        self.src2 = src2
        self.stage_cycles = {}
        self.remaining_exec = 0

    def __str__(self):
        return f"{self.op} {self.dest}:{self.src1},{self.src2}"


class FunctionalUnit:
    def __init__(self, name, count):
        self.name = name
        self.units = [
            {
                "reserved": False,
                "busy": False,
                "op": None,
                "instr": None,
                "remaining": 0,
            }
            for _ in range(count)
        ]

    def allocate(self, instr, cycle, exec_cycles):
        for u in self.units:
            if not u["busy"]:
                u.update(
                    {
                        "reserved": True,
                        "busy": True,
                        "op": instr.op,
                        "instr": instr,
                        "remaining": exec_cycles,
                    }
                )
                instr.stage_cycles["EX"] = cycle
                instr.remaining_exec = exec_cycles
                return True
        return False

    def step(self):
        finished = []
        for u in self.units:
            if u["busy"]:
                u["remaining"] -= 1
                if u["remaining"] <= 0:
                    finished.append(u["instr"])
                    u.update(
                        {
                            "reserved": True,
                            "busy": False,
                            "op": None,
                            "instr": None,
                            "remaining": 0,
                        }
                    )
        return finished


class Scoreboard:
    def __init__(self, instructions, timing, fu_config):
        self.instructions = instructions
        self.timing = timing
        self.RS = {f"R{i}": None for i in range(8)}
        self.FUs = {name: FunctionalUnit(name, cnt) for name, cnt in fu_config.items()}
        self.clock = 0
        self.issue_ptr = 0
        self.waiting = list(instructions)
        self.in_flight = []

    def print_status(self, fu):
        header = ""
        print("Register Result Status")
        for key in self.RS:
            header += f"{key:<15}"
        print(header)
        print("-" * len(header))
        for value in self.RS.values():
            print(f"{str(value):<15}", end="")

        header = f"{'Name':<18}{'Busy':<6}{'Op':<6}{'Instr':<6}"
        print(f"\n\n\nFunction Unit Status\n{header}")
        print("-" * len(header))
        for unit in fu.units:
            instr_label = ""
            if unit["instr"] is not None:
                instr_label = (
                    f"{unit['instr'].op} {unit['instr'].dest}:{unit['instr'].src1},{unit['instr'].src2}"
                    if unit["instr"].src1 or unit["instr"].src2
                    else f"{unit['instr'].op} {unit['instr'].dest}"
                )
            print(
                f"{fu.name:<18}{unit['busy']:<6}{unit['op'] or '':<6}{instr_label:<6}"
            )
        print()
        print("*" * len(header))
        print()

    def step(self):
        self.clock += 1

        for fu in self.FUs.values():
            fu.step()
            self.print_status(fu)

        for instr in list(self.in_flight):
            if (
                "RO_ready" in instr.stage_cycles
                and "EX" not in instr.stage_cycles
                and self.clock >= instr.stage_cycles["RO_ready"]
            ):
                fu = self.FUs[ISA[instr.op]["fu"]]
                fu.allocate(instr, self.clock, self.timing[instr.op]["EX"])
            elif (
                "ISS" in instr.stage_cycles
                and "RO_ready" not in instr.stage_cycles
                and self.clock >= instr.stage_cycles["ISS"]
            ):
                instr.stage_cycles["RO_ready"] = self.clock
            elif (
                "EX" in instr.stage_cycles
                and self.clock <= instr.stage_cycles["EX"] + self.timing[instr.op]["EX"]
            ):
                instr.stage_cycles["WB_ready"] = self.clock
            elif (
                "WB_ready" in instr.stage_cycles
                and self.clock
                >= instr.stage_cycles["WB_ready"] + self.timing[instr.op]["WB"]
            ):
                if instr.dest and self.RS[instr.dest] == instr:
                    self.RS[instr.dest] = None
                self.in_flight.remove(instr)
                fu_reserved = next(
                    (
                        f
                        for f in self.FUs[ISA[instr.op]["fu"]].units
                        if f["reserved"] and not f["busy"]
                    ),
                    None,
                )
                fu_reserved["reserved"] = False

        waiting_clone = self.waiting[:]
        dependencies = []
        j = 0
        for inst in waiting_clone:
            if inst.op == "HLT" and len(waiting_clone) > 1:
                continue

            noRAW = all(self.RS.get(r) is None for r in (inst.src1, inst.src2) if r)
            noWAR = not any(
                inst.dest == r.src1 or inst.dest == r.src1 for r in self.in_flight
            )
            noWAW = self.RS.get(inst.dest) is None
            free_fu = next(
                (f for f in self.FUs[ISA[inst.op]["fu"]].units if not f["reserved"]),
                None,
            )
            no_dependency = not any(
                r in [inst.src1, inst.src2, inst.dest] for r in dependencies
            )
            if noRAW and noWAR and noWAW and free_fu and no_dependency:
                free_fu["reserved"] = True
                inst.stage_cycles["ISS"] = self.clock
                if inst.dest:
                    self.RS[inst.dest] = inst
                self.in_flight.append(inst)
                self.waiting.pop(j)
                break
            else:
                j += 1
                dependencies.extend(
                    [
                        r
                        for r in [
                            inst.dest if inst.dest and not inst.dest.isdigit() else None,
                            inst.src1 if inst.src1 and not inst.src1.isdigit() else None,
                            inst.src2 if inst.src2 and not inst.src2.isdigit() else None,
                        ]
                        if r is not None
                    ]
                )

    def run(self):
        while self.waiting or self.in_flight:
            self.step()
        print(f"Final at cycle {self.clock}\n")
        header = f"{'Instr':<18}{'ISS':<6}{'RO':<6}{'EX':<6}{'WB':<6}"
        print(header)
        print("-" * len(header))
        for i in self.instructions:
            instr_label = (
                f"{i.op} {i.dest}:{i.src1},{i.src2}"
                if i.src1 or i.src2
                else f"{i.op} {i.dest}"
            )
            print(
                f"{instr_label:<18}{str(i.stage_cycles.get('ISS', '')):<6}{str(i.stage_cycles.get('RO_ready', '')):<6}{str(i.stage_cycles.get('EX', '')):<6}{str(i.stage_cycles.get('WB_ready', '')):<6}"
            )


if __name__ == "__main__":
    TIMING = {op: {"ISS": 1, "RO": 1, "EX": 3, "WB": 1} for op in ISA}
    FU_CONFIG = {"ALU": 2, "LS": 2, "BR": 1, "IO": 1, "CTRL": 1}
    instrs = [
        Instruction("LD", "R1", "0"),  # ACC ← M[0]
        Instruction("ST", None, "R1", "1"),  # M[1] ← ACC
        Instruction("BRZ", None, "1"),  # if ACC == 0 then PC ← addr
        Instruction("BRNZ", None, "1"),  # if ACC ≠ 0 then PC ← addr
        Instruction("ADD", "R1", "R1", "R2"),  # ACC ← ACC + M[addr]
        Instruction("SUB", "R1", "R1", "R2"),  # ACC ← ACC - M[addr]
        Instruction("ROR", "R1"),  # ACC ← rotate-right(ACC)
        Instruction("ROL", "R1"),  # ACC ← rotate-left(ACC)
        Instruction("SHR", "R1"),  # ACC ← logical-shift-right(ACC)
        Instruction("SHL", "R1"),  # ACC ← logical-shift-left(ACC)
        Instruction("OUT", "R1"),  # OUT ← ACC
        Instruction("AND", "R1", "R1", "R2"),  # ACC ← ACC ∧ M[addr]
        Instruction("OR", "R1", "R1", "R2"),  # ACC ← ACC ∨ M[addr]
        Instruction("XOR", "R1", "R1", "R2"),  # ACC ← ACC ⊕ M[addr]
        Instruction("NOT", "R1"),  # ACC ← ¬ACC
        Instruction("HLT", None),  # stop execution
    ]
    sb = Scoreboard(instrs, TIMING, FU_CONFIG)
    sb.run()
