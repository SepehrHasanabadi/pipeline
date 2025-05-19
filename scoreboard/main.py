# import sys
# from collections import deque, defaultdict

ISA = {
    "LD": {"fu": "LS", "cycles": None},
    "ST": {"fu": "LS", "cycles": None},
    "ADD": {"fu": "ALU", "cycles": None},
    "SUB": {"fu": "ALU", "cycles": None},
    "MUL": {"fu": "MUL", "cycles": None},
    "DIV": {"fu": "MUL", "cycles": None},
    "AND": {"fu": "ALU", "cycles": None},
    "OR": {"fu": "ALU", "cycles": None},
    "XOR": {"fu": "ALU", "cycles": None},
    "NOT": {"fu": "ALU", "cycles": None},
    "ROL": {"fu": "ALU", "cycles": None},
    "ROR": {"fu": "ALU", "cycles": None},
    "SHL": {"fu": "ALU", "cycles": None},
    "SHR": {"fu": "ALU", "cycles": None},
}


class Instruction:
    def __init__(self, op, dest, src1=None, src2=None):
        self.op = op
        self.dest = dest
        self.src1 = src1
        self.src2 = src2
        self.stage_cycles = {}
        self.remaining_exec = 0


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
            header += f"{key:<6}"
        print(header)
        print("-" * len(header))
        for value in self.RS.values():
            print(f"{str(value):<6}", end="")

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
        for inst in waiting_clone:
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
                self.waiting.pop(0)
            else:
                dependencies.extend(
                    [r for r in [inst.dest, inst.src1, inst.src2] if r is not None]
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
    FU_CONFIG = {"ALU": 2, "MUL": 1, "LS": 2}
    prog = [
        Instruction("LD", "R1", "0"),
        Instruction("LD", "R2", "1"),
        Instruction("ADD", "R3", "R1", "R2"),
        Instruction("MUL", "R4", "R3", "R2"),
        Instruction("ST", None, "R4", "2"),
    ]
    sb = Scoreboard(prog, TIMING, FU_CONFIG)
    sb.run()
