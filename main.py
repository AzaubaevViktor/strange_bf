from typing import List

from bf_interpreter import BrainFuck


class Pointer:
    def __init__(self, memory, addr: int):
        self.addr: int = addr
        self.memory = memory
        self.usable = True

    def __neg__(self) -> "Pointer":
        return Pointer(self.memory, -self.addr)

    def free(self):
        self.memory.free(self.addr)
        self.usable = False

    def __str__(self):
        return f"${self.addr}"


class MemoryNameSpace:
    def __init__(self, memory: "Memory"):
        self.mem = memory
        self.my: List[Pointer] = []

    def reg(self):
        return Pointer(self.mem, self.mem.get())

    def clear(self):
        for p in self.my:
            if p.usable:
                p.free()


class Memory:
    def __init__(self, count: int = 30000):
        self.free_mem = [False] * count

    def get_ns(self):
        return MemoryNameSpace(self)

    def get(self):
        for i, v in enumerate(self.free_mem):
            if not v:
                self.free_mem[i] = True
                return i
        raise ValueError("Не свободной памяти")

    def free(self, i):
        if self.free_mem[i] == False:
            raise ValueError("Память уже освобождена")
        self.free_mem[i] = False


class ParentCode:
    pass

class Executor:
    def __init__(self):
        self._code = ""
        self._mem = Memory()
        self._global_ns = self._mem.get_ns()
        self.ns: MemoryNameSpace = None

    @property
    def optimised(self):
        a = []
        for c in self._code:
            if a:
                if a[-1] == '<' and c == '>':
                    a.pop()
                elif a[-1] == ">" and c == "<":
                    a.pop()
                elif a[-1] == "+" and c == '-':
                    a.pop()
                elif a[-1] == '-' and c == '+':
                    a.pop()
                elif c in "<>+-[].,":
                    a.append(c)
            elif c in "<>+-[].,":
                a.append(c)

        return "".join(a)

    @staticmethod
    def _ns(func):
        def wrapper(self: "Executor", *args, **kwargs):
            old_ns = self.ns

            self.ns = self._mem.get_ns()

            for code in func(self, *args, **kwargs):
                if code:
                    self._code += code

            self.ns.clear()

            self.ns = old_ns

        return wrapper

    ns = _ns.__func__

    @staticmethod
    def _block(func):
        class With:
            def __init__(self, _self, *args, **kwargs):
                self.executor = _self

                self.old_ns = self.executor.ns

                self.executor.ns = self.executor._mem.get_ns()

                self.gen = func(self.executor, *args, **kwargs)
                self.args = args
                self.kwargs = kwargs

            def __enter__(self):
                for code in self.gen:
                    if isinstance(code, ParentCode):
                        break
                    if code:
                        self.executor._code += code

            def __exit__(self, exc_type, exc_val, exc_tb):
                for code in self.gen:
                    if code:
                        self.executor._code += code

                self.executor.ns.clear()

                self.executor.ns = self.old_ns

        With.__name__ = "ClassBlock_" + func.__name__

        def wrapper(_self, *args, **kwargs):
            return With(_self, *args, **kwargs)

        wrapper.__name__ = "Block_" + func.__name__

        return wrapper

    block = _block.__func__

    def global_var(self):
        return self._global_ns.reg()

    @ns
    def _Ladd(self, v: int):
        yield "+" * v if v > 0 else '-' * (-v)

    @ns
    def _Lmove(self, p: Pointer):
        yield ">" * p.addr if p.addr > 0 else '<' * (-p.addr)

    @ns
    def _Lprint(self):
        yield "."

    @ns
    def _Lread(self):
        yield ","

    @block
    def cycle(self, cond: Pointer):
        self._Lmove(cond)
        yield '['
        self._Lmove(-cond)

        yield ParentCode()

        self._Lmove(cond)
        yield "]"
        self._Lmove(-cond)

    @ns
    def printPointer(self, p: Pointer):
        self._Lmove(p)
        self._Lprint()
        self._Lmove(-p)
        yield ""

    @ns
    def add(self, p: Pointer, v: int):
        self._Lmove(p)
        self._Ladd(v)
        self._Lmove(-p)
        yield ""

    @ns
    def null(self, p: Pointer):
        with self.cycle(p):
            self.add(p, -1)
        yield ""

    @ns
    def set(self, p: Pointer, v: int):
        self.null(p)
        self.add(p, v)
        yield ""

    @ns
    def printStr(self, s: str):
        res = self.ns.reg()
        for c in s:
            self.set(res, ord(c))
            self.printPointer(res)
        yield ""

    @ns
    def move(self, to: Pointer, _from: Pointer):
        with self.cycle(_from):
            self.add(_from, -1)
            self.add(to, 1)
        yield ""

    @ns
    def isub(self, to: Pointer, _from: Pointer):
        with self.cycle(_from):
            self.add(_from, -1)
            self.add(to, -1)
        yield ""

    @ns
    def move2(self, to1: Pointer, to2: Pointer, _from: Pointer):
        with self.cycle(_from):
            self.add(_from, -1),
            self.add(to1, 1),
            self.add(to2, 1)
        yield ""

    @ns
    def mmove(self, *tos: Pointer):
        _from = tos[-1]
        tos = tos[:-1]
        with self.cycle(_from):
            self.add(_from, -1)
            [self.add(to, 1) for to in tos]
        yield ""

    @ns
    def copy(self, to: Pointer, _from: Pointer):
        res = self.ns.reg()

        self.null(to)
        self.null(res)
        self.mmove(to, res, _from)
        self.mmove(_from, res)

        yield ""

    @block
    def iff(self, cond: Pointer):
        _cond = self.ns.reg()

        self.copy(_cond, cond)

        with self.cycle(_cond):
            yield ParentCode()
            self.null(_cond)

        yield ""

    @block
    def ifzero(self, cond: Pointer):
        false_cond = self.ns.reg()
        self.set(false_cond, 1)

        with self.iff(cond):
            self.set(false_cond, 0)

        with self.cycle(false_cond):
            yield ParentCode()
            self.null(false_cond)

        yield ""

    @ns
    def mul(self, h: Pointer, l: Pointer, a: Pointer, b: Pointer):
        """ h = a * b // 256
            l = a * b % 255
        """

        _a = self.ns.reg()
        _b = self.ns.reg()

        self.null(h)
        self.null(l)
        self.copy(_a, a)
        self.copy(_b, b)
        with self.cycle(_a):
            with self.cycle(_b):
                self.add(l, 1),
                with self.ifzero(l):
                    self.add(h, 1)
                self.add(_b, -1)
            self.copy(_b, b)
            self.add(_a, -1)

        yield ""

    @ns
    def div(self, d: Pointer, m: Pointer, a: Pointer, b: Pointer):
        """ d = a // b
            m = a % b
        """
        _a = self.ns.reg()
        _b = self.ns.reg()

        self.null(d)
        self.null(m)
        self.copy(_a, a)
        self.copy(_b, b)

        with self.iff(_a):
            with self.ifzero(_b):
                # if _b == 0: inf, 0
                self.set(d, 255)
                self.set(m, 0)

            with self.iff(_b):
                # if _b != 0
                with self.cycle(_a):
                    self.add(_a, -1),
                    self.add(_b, -1),
                    with self.ifzero(_b):
                        # _b == 0:  _b = b; d += 1
                        self.copy(_b, b)
                        self.add(d, 1)

                self.copy(m, _b)

        yield ""

    @ns
    def sum(self, r: Pointer, a: Pointer, b: Pointer):
        res = self.ns.reg()

        self.copy(r, a)
        self.mmove(res, r, b)
        self.mmove(b, res)
        yield ""

    def test_code(self, code):
        if self.optimised != code:
            raise ValueError(
                f"Need `{code}`, but `{self.optimised}`"
            )
        print(".", end='')
        return True

    def test_out(self, s, mem):
        bf = BrainFuck(self.optimised, print_char=True)

        bf.run()

        if s and bf.out != s:
            raise ValueError(
                f"Need `{bf.out}`, but `{s}`"
            )

        if mem:
            for i, v in enumerate(mem):
                if v is None:
                    continue
                if bf.mem[i] != v:
                    raise ValueError(
                        f"Mem[{i}] need `{v}`, but `{bf.mem[i]}`"
                    )
        print('.')


print("_Ladd")

e = Executor()
e._Ladd(4)
e.test_code("++++")

print("Cycle")
e = Executor()
a = e.global_var()
with e.cycle(a):
    e.add(a, -1)
e.test_code("[-]")

print("printStr")
e = Executor()
e.printStr("Hello!")
e.test_out("Hello!", None)

print("set+copy")
e = Executor()
a = e.global_var()
b = e.global_var()

e.set(a, 10)
e.copy(b, a)
e.test_out(None, [10, 10])

print("sum")
e = Executor()
a = e.global_var()
b = e.global_var()
c = e.global_var()

e.set(a, 10)
e.set(b, 20)

e.sum(c, b, a)
print(e.optimised)
e.test_out(None, [10, 20, 30])


print("iff")
e = Executor()
a = e.global_var()
b = e.global_var()
c = e.global_var()

e.set(a, 10)

with e.iff(a):
    e.set(c, 20)

with e.iff(b):
    e.set(c, 10)

print(e.optimised)
e.test_out(None, [10, 0, 20])


print("ifzero")
e = Executor()
a = e.global_var()
b = e.global_var()
c = e.global_var()

e.set(a, 10)

with e.ifzero(a):
    e.set(c, 20)

with e.ifzero(b):
    e.set(c, 10)

print(e.optimised)
e.test_out(None, [10, 0, 10])


print("mul")
e = Executor()
h = e.global_var()
l = e.global_var()
a = e.global_var()
b = e.global_var()

e.set(a, 25)
e.set(b, 20)

e.mul(h, l, a, b)
print(e.optimised)
e.test_out(None, [1, 244, 25, 20])


print("div")
e = Executor()
d = e.global_var()
m = e.global_var()
a = e.global_var()
b = e.global_var()

e.set(a, 25)
e.set(b, 10)

e.div(d, m, a, b)
print(e.optimised)
e.test_out(None, [2, 5, 25, 10])

