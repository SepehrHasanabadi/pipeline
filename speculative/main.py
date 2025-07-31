from collections import deque

# Instruction types supported include: ADD, SUB, LOAD, STORE, BRANCH, DIV (for exception demonstration)
class Instruction:
    def __init__(self, op, dest=None, src1=None, src2=None, addr=None, label=None):
        self.op = op
        self.dest = dest
        self.src1 = src1
        self.src2 = src2
        self.addr = addr
        self.label = label
        self.rob_id = None

class ROBEntry:
    def __init__(self, instr, idx):
        self.instr = instr
        self.idx = idx
        self.ready = False
        self.value = None
        self.mispredicted = False
        self.exception = None

class FunctionalUnit:
    def __init__(self, name, latency=1):
        self.name = name
        self.latency = latency
        self.busy = False
        self.entry = None
        self.counter = 0

    def start(self, rob_entry):
        self.busy = True
        self.entry = rob_entry
        self.counter = self.latency

    def step(self, regs, memory):
        if not self.busy:
            return None
        self.counter -= 1
        if self.counter > 0:
            return None
        instr = self.entry.instr
        try:
            if instr.op == 'ADD':
                self.entry.value = regs[instr.src1] + regs[instr.src2]
            elif instr.op == 'SUB':
                self.entry.value = regs[instr.src1] - regs[instr.src2]
            elif instr.op == 'LOAD':
                addr = instr.addr
                self.entry.value = memory.get(addr, 0)
            elif instr.op == 'STORE':
                self.entry.value = regs[instr.src1]
            elif instr.op == 'DIV':
                # Demonstrate exception: division by zero
                if regs[instr.src2] == 0:
                    raise ZeroDivisionError('Divide by zero')
                self.entry.value = regs[instr.src1] // regs[instr.src2]
            elif instr.op == 'BRANCH':
                cond = (regs[instr.src1] == regs[instr.src2])
                # simple always-not-taken predictor
                pred = False
                if cond != pred:
                    self.entry.mispredicted = True
                self.entry.value = cond
        except Exception as e:
            self.entry.exception = e
        finally:
            self.entry.ready = True
            finished = self.entry
            self.busy = False
            self.entry = None
            return finished

class Simulator:
    def __init__(self, program, name='Program'):
        self.name = name
        self.program = program
        self.pc = 0
        self.registers = {f'R{i}': 0 for i in range(16)}
        self.memory = {}
        self.rob = deque()
        self.rob_size = 8
        self.next_rob_id = 1
        self.reservation = deque()
        # functional units
        self.alu = FunctionalUnit('ALU', latency=1)
        self.mem_fu = FunctionalUnit('MEM', latency=2)
        self.branch_fu = FunctionalUnit('BR', latency=1)
        self.div_fu = FunctionalUnit('DIV', latency=3)
        self.cycle = 0

    def issue(self):
        if self.pc >= len(self.program):
            return
        if len(self.rob) >= self.rob_size:
            return
        instr = self.program[self.pc]
        self.pc += 1
        rob_ent = ROBEntry(instr, self.next_rob_id)
        instr.rob_id = self.next_rob_id
        self.next_rob_id += 1
        self.rob.append(rob_ent)
        self.reservation.append(rob_ent)

    def execute(self):
        # dispatch to available FU
        for fu, ops in [(self.branch_fu, ['BRANCH']),
                        (self.alu, ['ADD','SUB']),
                        (self.div_fu, ['DIV']),
                        (self.mem_fu, ['LOAD','STORE'])]:
            if not fu.busy:
                for entry in list(self.reservation):
                    if entry.instr.op in ops:
                        fu.start(entry)
                        self.reservation.remove(entry)
                        break
        # step all FUs
        for fu in [self.branch_fu, self.alu, self.div_fu, self.mem_fu]:
            finished = fu.step(self.registers, self.memory)
            if finished:
                if finished.instr.op == 'BRANCH' and finished.mispredicted:
                    # flush on mispredict
                    self.flush(finished.idx, finished.instr.label)

    def commit(self):
        if not self.rob:
            return
        head = self.rob[0]
        if not head.ready:
            return
        # handle exception
        if head.exception:
            print(f"Exception at ROB#{head.idx}: {head.exception}")
            # flush all
            self.rob.clear()
            self.reservation.clear()
            return
        instr = head.instr
        if instr.op in ['ADD','SUB','DIV','LOAD']:
            self.registers[instr.dest] = head.value
        elif instr.op == 'STORE':
            self.memory[instr.addr] = head.value
        elif instr.op == 'BRANCH':
            if head.value:
                self.pc = instr.label
        self.rob.popleft()

    def flush(self, rob_id, target):
        # remove speculative entries after branch
        self.rob = deque([e for e in self.rob if e.idx <= rob_id])
        self.reservation.clear()
        self.pc = target
        # clear FUs
        for fu in [self.branch_fu, self.alu, self.div_fu, self.mem_fu]:
            fu.busy = False; fu.entry = None

    def step(self):
        print(f"=== {self.name} Cycle {self.cycle+1} ===")
        self.issue()
        self.execute()
        self.commit()
        self.print_state()
        print()
        self.cycle += 1

    def run(self, max_cycles=20):
        while (self.rob or self.reservation or self.pc < len(self.program)) and self.cycle < max_cycles:
            self.step()

    def print_state(self):
        print("PC=", self.pc)
        print("Regs:", {r: self.registers[r] for r in sorted(self.registers) if self.registers[r] != 0})
        print("Mem:", self.memory)
        print("ROB:", [(e.idx, e.instr.op, e.ready, e.value, e.exception) for e in self.rob])
        print("RS:", [e.instr.op+str(e.idx) for e in self.reservation])

if __name__ == '__main__':
    # Define test cases covering all examples:
    tests = []
    # 1. Arithmetic and RAW hazard
    prog1 = [
        Instruction('ADD', dest='R1', src1='R2', src2='R3'),
        Instruction('SUB', dest='R4', src1='R1', src2='R5'),
    ]
    # 2. Load-use hazard
    prog2 = [
        Instruction('LOAD', dest='R6', addr=100),
        Instruction('ADD', dest='R7', src1='R6', src2='R8'),
    ]
    # 3. Store then Load
    prog3 = [
        Instruction('STORE', src1='R6', addr=200),
        Instruction('LOAD', dest='R9', addr=200),
    ]
    # 4. Branch taken vs not-taken
    prog4 = [
        Instruction('ADD', dest='R2', src1='R0', src2='R0'),
        Instruction('BRANCH', src1='R2', src2='R0', label=4),
        Instruction('ADD', dest='R3', src1='R0', src2='R0'),  # skipped if taken
        Instruction('ADD', dest='R4', src1='R0', src2='R0'),
        Instruction('ADD', dest='R5', src1='R0', src2='R0'),
    ]
    # 5. Exception (divide by zero)
    prog5 = [
        Instruction('DIV', dest='R10', src1='R2', src2='R11'),
        Instruction('ADD', dest='R12', src1='R10', src2='R0'),
    ]
    tests.append((prog1, 'Arithmetic RAW'))
    tests.append((prog2, 'Load-Use Hazard'))
    tests.append((prog3, 'Store-Load'))
    tests.append((prog4, 'Branch Test'))
    tests.append((prog5, 'Deferred Exception'))

    # Initialize & run each test
    for prog, name in tests:
        sim = Simulator(prog, name=name)
        # preset registers and memory for testing
        sim.registers['R2'] = 5
        sim.registers['R3'] = 3
        sim.registers['R5'] = 8
        sim.registers['R6'] = 7
        sim.registers['R8'] = 2
        sim.registers['R11'] = 0  # zero for exception
        sim.memory[100] = 42
        sim.memory[200] = 0
        print(f"\n### Running test: {name} ###\n")
        sim.run(max_cycles=10)
        print("=======================================\n")
