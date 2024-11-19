from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr


__all__ = ["RISCVMachineTimer"]


class RISCVMachineTimer(wiring.Component):
    class MTIME(csr.Register, access="r"):
        def __init__(self):
            super().__init__(csr.Field(csr.action.R, 32))

    class MTIMECMP(csr.Register, access="rw"):
        def __init__(self):
            super().__init__(csr.Field(csr.action.RW, 32))

    def __init__(self):
        regs = csr.Builder(addr_width=4, data_width=8)

        self._mtime_lo    = regs.add("mtime_lo",    self.MTIME(),    offset=0x0)
        self._mtime_hi    = regs.add("mtime_hi",    self.MTIME(),    offset=0x4)
        self._mtimecmp_lo = regs.add("mtimecmp_lo", self.MTIMECMP(), offset=0x8)
        self._mtimecmp_hi = regs.add("mtimecmp_hi", self.MTIMECMP(), offset=0xc)

        self._bridge = csr.Bridge(regs.as_memory_map())

        super().__init__({
            "csr_bus": In(csr.Signature(addr_width=regs.addr_width, data_width=regs.data_width)),
            "irq": Out(1),
        })
        self.csr_bus.memory_map = self._bridge.bus.memory_map

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge

        connect(m, flipped(self.csr_bus), self._bridge.bus)

        mtime    = Signal(64)
        mtimecmp = Signal(64)

        m.d.comb += [
            mtime.eq(Cat(self._mtime_lo.f.r_data, self._mtime_hi.f.r_data)),
            mtimecmp.eq(Cat(self._mtimecmp_lo.f.data, self._mtimecmp_hi.f.data)),
        ]

        m.d.sync += [
            Cat(self._mtime_lo.f.r_data, self._mtime_hi.f.r_data).eq(mtime + 1),
            self.irq.eq((mtimecmp != 0) & (mtimecmp <= mtime)),
        ]

        return m
