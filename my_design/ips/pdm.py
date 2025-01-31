from amaranth import *
from amaranth import Elaboratable, Module
from amaranth.build import Platform

from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect
from amaranth_soc import csr

from chipflow_lib.platforms import OutputPinSignature

__all__ = ["PDMPeripheral"]


class PDMPeripheral(wiring.Component):
    class OutVal(csr.Register, access="rw"):
        """Analog sample value"""
        val: csr.Field(csr.action.RW, unsigned(16))

    class Conf(csr.Register, access="rw"):
        """Configuration register """
        en: csr.Field(csr.action.RW, unsigned(1))

    Signature = wiring.Signature({
        "bus": In(csr.Signature(addr_width=regs.addr_width, data_width=regs.data_width)),
        "pdm": Out(OutputPinSignature(1))
        })

    def __init__(self, *, name, bitwidth):
        self._bitwidth = bitwidth

        regs = csr.Builder(addr_width=3, data_width=8, name=name)

        self._outval = regs.add("outval", self.OutVal(), offset=0x0)
        self._conf = regs.add("conf", self.Conf(), offset=0x4)

        self._bridge = csr.Bridge(regs.as_memory_map())

        super().__init__(PDMPeripheral.Signature)
        self.bus.memory_map = self._bridge.bus.memory_map

    @property
    def bitwidth(self):
        return self._bitwidth

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge
        maxval = Const(int((2**self._bitwidth)-1), unsigned(self._bitwidth))        
        error = Signal(unsigned(self._bitwidth), reset=0x0)
        error_0 = Signal(unsigned(self._bitwidth), reset=0x0)
        error_1 = Signal(unsigned(self._bitwidth), reset=0x0)
        pdm_ao = Signal()
        connect(m, flipped(self.bus), self._bridge.bus)
        m.d.sync += [
            error_1.eq(error + maxval - self._outval.f.val.data),
            error_0.eq(error - self._outval.f.val.data),
        ]
        with m.If(self._outval.f.val.data >= error):
            m.d.sync += [ 
                pdm_ao.eq(1),
                error.eq(error_1),
            ]
        with m.Else():
            m.d.sync += [ 
                pdm_ao.eq(0),
                error.eq(error_0),
            ]

        with m.If(self._conf.f.en.data == 1):
            m.d.comb += self.pdm_ao.eq(pdm_ao)
        with m.Else():
            m.d.comb += self.pdm_ao.eq(0)            
        return m
