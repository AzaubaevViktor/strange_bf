class BrainFuck:
    def __init__(self, code: str, print_char=True):
        self.source_code = code
        self.code = None
        self.parse()
        self.mem = [0] * 30000
        self.pc = 0
        self.mp = 0
        self.print_char = print_char
        self.out = ""

    def parse(self):
        cycle_stack = []
        opcodes = []

        def gen_do(what_prev, add_if_prev):
            def do():
                default_opcode, default_value = what_prev, add_if_prev
                if opcodes and opcodes[-1][0] == what_prev:
                    opcodes[-1][1] += add_if_prev
                else:
                    opcodes.append([default_opcode, default_value])
            return do

        def cycle_op_do():
            opcodes.append(['[', -1])
            cycle_stack.append(len(opcodes) - 1)  # this opcode

        def cycle_cl_do():
            pc = cycle_stack.pop()
            opcodes.append([']', pc])
            opcodes[pc][1] = len(opcodes)  # next from `]`

        op_func = {
            '+': gen_do('+', 1),
            '-': gen_do('+', -1),
            '>': gen_do('>', 1),
            '<': gen_do('>', -1),
            '.': gen_do('.', 1),
            ',': gen_do(',', -1),
            '[': cycle_op_do,
            ']': cycle_cl_do,
        }

        for i, opcode in enumerate(self.source_code):
            func = op_func.get(opcode, None)
            if func:
                func()

        if cycle_stack:
            raise ValueError("count(`]`) != count(`]`)")

        self.code = tuple(map(tuple, opcodes))

    def _step(self):
        if self.pc >= len(self.code):
            return False
        opcode = self.code[self.pc]

        if opcode[0] == "+":
            self.mem[self.mp] += opcode[1]
            self.mem[self.mp] %= 256
        elif opcode[0] == ">":
            self.mp += opcode[1]
            if self.mp < 0:
                raise ValueError("Mem pointer < 0")
            if self.mp > 30000:
                raise ValueError("Mem pointer > 0")
        elif opcode[0] == ".":
            c = self.mem[self.mp]
            self.out += chr(c)
            if self.print_char:
                print(chr(c) * opcode[1], end="")
            else:
                print(f"{chr(c)}({c})\n" * opcode[1], end="")
        elif opcode[0] == ",":
            pass
        elif opcode[0] == "[":
            if not self.mem[self.mp]:
                self.pc = opcode[1] - 1
        elif opcode[0] == "]":
            self.pc = opcode[1] - 1

        self.pc += 1
        return True

    def run(self, info=None):
        while self._step():
            if info:
                print(info(self))
                input()

