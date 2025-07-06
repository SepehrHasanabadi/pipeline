iid = 0


class Instruction:
    def __init__(self, op, dest, src1=None, src2=None):
        global iid
        self.iid = iid
        iid += 1
        self.op = op
        self.dest = dest
        self.src1 = src1
        self.src2 = src2
        self.remaining_exec = 1

    def __str__(self):
        return f"{self.op} {self.dest}:{self.src1},{self.src2}"


class Fu:
    accept_cmds = []
    name = None
    bf_size = 0
    res_station = []
    reg_status = None
    res_status = None
    inst_status = None

    def __init__(
        self, name, reg_status, res_status, inst_status, accept_cmds, bf_size=3
    ):
        self.res_station = []
        self.name = name
        self.bf_size = bf_size
        self.reg_status = reg_status
        self.res_status = res_status
        self.inst_status = inst_status
        self.accept_cmds = accept_cmds

    def accept(self, inst, clock):
        if len(self.res_station) == self.bf_size:
            return False
        if inst.op in self.accept_cmds:
            self.res_station.append(inst)
            self.res_status.create(inst, self.name)
            self.inst_status.issue_inst(inst, clock)
            return True
        return False

    def tick(self, clock):
        insts = self.res_status.get_ready_insts()
        ticked = False
        for inst in insts:
            if inst.op not in self.accept_cmds:
                continue
            if inst.remaining_exec == 0:
                self.inst_status.move_inst(inst, clock)
                inst_id = self.res_status.get_inst_id(inst)
                self.reg_status.update(inst.dest, inst_id)
            elif self.inst_status.exec_inst(inst, clock):
                inst.remaining_exec -= 1
            ticked = True
        return ticked


class MemUnit:
    load_bf_size = 0
    store_bf_size = 0
    load_bf = []
    store_bf = []
    res_status = None
    reg_status = None
    inst_status = None

    def __init__(self, res_status, reg_status, inst_status, load_buffer, store_buffer):
        self.res_status = res_status
        self.reg_status = reg_status
        self.inst_status = inst_status
        self.load_bf_size = load_buffer
        self.store_bf_size = store_buffer

    def accept(self, inst, clock):
        if inst.op == "LD" and len(self.load_bf) == self.load_bf_size:
            return False
        if inst.op == "ST" and len(self.store_bf) == self.store_bf_size:
            return False
        if inst.op == "LD":
            self.load_bf.append(inst)
            self.inst_status.issue_inst(inst, clock)
            self.res_status.create(inst, "load")
            return True
        if inst.op == "ST":
            self.store_bf.append(inst)
            self.inst_status.issue_inst(inst, clock)
            self.res_status.create(inst, "store")
            return True
        return False

    def tick(self, clock):
        ticked = False
        ready_insts = self.res_status.get_ready_insts()
        for inst in ready_insts:
            if inst.op not in ["LD", "ST"]:
                continue
            if inst.remaining_exec == 0:
                self.inst_status.move_inst(inst, clock)
                inst_id = self.res_status.get_inst_id(inst)
                if inst.op == "LD":
                    self.reg_status.update(inst.dest, inst_id)
            elif self.inst_status.exec_inst(inst, clock):
                inst.remaining_exec -= 1
            ticked = True
        return ticked


class InstStatus:
    items = []

    class Item:
        stages = {
            "ST": ["issue", "EX", "memAccess"],
            "LD": ["issue", "EX", "memAccess", "CDN"],
            "ADD": ["issue", "EX", "CDN"],
            "SUB": ["issue", "EX", "CDN"],
            "AND": ["issue", "EX", "CDN"],
            "OR": ["issue", "EX", "CDN"],
            "XOR": ["issue", "EX", "CDN"],
        }
        inst = None
        issue = None
        EX = None
        memAccess = None
        CDN = None

    def __init__(self, inst_queue):
        for inst in inst_queue:
            item = self.Item()
            item.inst = inst
            self.items.append(item)

    def issue_inst(self, inst, clock):
        for item in self.items:
            if item.inst.iid == inst.iid:
                item.issue = clock

    def exec_inst(self, inst, clock):
        for item in self.items:
            if item.inst.iid == inst.iid and item.EX is None:
                if clock > item.issue:
                    item.EX = clock
                    return True
                return False
        return False

    def move_inst(self, inst, clock):
        for item in self.items:
            if item.inst.iid == inst.iid:
                for stage in item.stages.get(inst.op, []):
                    if getattr(item, stage) is None:
                        setattr(item, stage, clock)
                        break

    def finished_insts(self):
        result = []
        for item in self.items:
            last_stage = item.stages[item.inst.op][-1]
            if getattr(item, last_stage) is not None:
                result.append(item.inst)
        return result
                
    def display(self):
        print(f"{'Inst':<18}{'Issue':<12}{'Execute':<12}{'Mem Access':<12}{'CDN'}")
        for item in self.items:
            print(
                f"{item.inst}{'':<12}{str(item.issue):<12}{str(item.EX):<12}{str(item.memAccess):<12}{str(item.CDN)}"
            )


class ResStatus:
    items = []
    inst_queue = []

    class Item:
        inst_id = None
        inst = None
        name = None
        busy = False
        Vj, Vk, Qj, Qk = None, None, None, None

    def __init__(self, resource):
        for r in resource:
            for i in range(1, r["buffer"] + 1):
                item = self.Item()
                item.name = r["name"]
                item.inst_id = f"{r['name']}{i}"
                self.items.append(item)

    def create(self, inst, name):
        item = None
        for item in self.items:
            if item.name == name and not item.busy:
                item.busy = True
                item.inst = inst
                break
        Q = []
        V = [inst.src1, inst.src2]
        for element in self.items:
            if element.inst and inst.iid > element.inst.iid:
                if element.inst.dest in [inst.src1, inst.src2]:
                    Q.append(element.inst_id)
                    V = [i for i in V if i != inst.dest]

        item.Qj, item.Qk = (Q + [None, None])[:2]
        item.Vj, item.Vk = (V + [None, None])[:2]

    def delete(self, inst_id):
        for item in self.items:
            if item.inst_id == inst_id:
                item.inst = None
                item.busy = False
                item.Vj, item.Vk, item.Qj, item.Qk = None, None, None, None
            if inst_id == item.Qj:
                item.Qj = None
            if inst_id == item.Qk:
                item.Qk = None

    def get_inst_id(self, inst):
        for item in self.items:
            if item.inst and item.inst.iid == inst.iid:
                return item.inst_id

    def get_ready_insts(self):
        return [
            item.inst
            for item in self.items
            if item.Qj is None and item.Qk is None and item.inst
        ]


class RegStatus:
    Qi = {}

    def update(self, reg, res_id):
        self.Qi[reg] = res_id

    def __init__(self, inst_queue):
        for item in inst_queue:
            self.Qi[item.dest] = None


class IssueUnit:
    fus = []
    mem_unit = None
    mem_ops = ["LD", "ST"]

    def __init__(self, fus, mem_unit):
        self.fus = fus
        self.mem_unit = mem_unit

    def accept(self, inst, clock):
        accepted = False
        if inst.op in self.mem_ops:
            accepted = self.mem_unit.accept(inst, clock)
        for fu in self.fus:
            accepted = fu.accept(inst, clock) or accepted
        return accepted


class Tomasulo:
    clock = 1
    CDB = None
    fus = []
    mem_unit = None
    issue_unit = None
    inst_queue = []
    status = None
    ALU = [
        {"name": "adder", "accept_cmds": ["ADD", "SUB"], "buffer": 3},
        {"name": "multiplier", "accept_cmds": ["MUL"], "buffer": 3},
        {"name": "general", "accept_cmds": ["AND", "OR", "XOR"], "buffer": 3},
    ]
    LOAD_RES = {"name": "load", "accept_cmds": ["LD"], "buffer": 2}
    STORE_RES = {"name": "store", "accept_cmds": ["ST"], "buffer": 2}
    RESOURCE = [*ALU, LOAD_RES, STORE_RES]

    def tick(self):
        progress = True
        progress = self.mem_unit.tick(self.clock)
        for fu in self.fus:
            progress = fu.tick(self.clock) or progress
        finished_insts = self.inst_status.finished_insts()
        for inst in finished_insts:
            inst_id = self.res_status.get_inst_id(inst)
            self.res_status.delete(inst_id)
        return progress

    def __init__(self, inst_queue):
        self.res_status = ResStatus(self.RESOURCE)
        self.reg_status = RegStatus(self.inst_queue)
        self.inst_status = InstStatus(inst_queue)
        self.mem_unit = MemUnit(
            res_status=self.res_status,
            reg_status=self.reg_status,
            inst_status=self.inst_status,
            load_buffer=self.LOAD_RES["buffer"],
            store_buffer=self.STORE_RES["buffer"],
        )
        self.inst_queue = inst_queue
        self.fus = []
        for item in self.ALU:
            self.fus.append(
                Fu(
                    name=item["name"],
                    res_status=self.res_status,
                    reg_status=self.reg_status,
                    inst_status=self.inst_status,
                    accept_cmds=item["accept_cmds"],
                    bf_size=item["buffer"],
                )
            )

        self.issue_unit = IssueUnit(self.fus, self.mem_unit)

    def run(self):
        while True:
            if len(self.inst_queue) > 0:
                last_inst = self.inst_queue[0]
                if self.issue_unit.accept(last_inst, self.clock):
                    self.inst_queue.pop(0)
            if not self.tick():
                break
            self.clock += 1
        self.inst_status.display()


if __name__ == "__main__":
    instrs = [
        Instruction("LD", "R1", "0"),
        Instruction("ST", None, "R1", "1"),
        Instruction("ADD", "R1", "R1", "R2"),
        Instruction("SUB", "R1", "R1", "R2"),
        Instruction("ST", None, "R1", "2"),
        Instruction("AND", "R1", "R1", "R2"),
        Instruction("XOR", "R1", "R1", "R2"),
    ]
    tm = Tomasulo(inst_queue=instrs)
    tm.run()
