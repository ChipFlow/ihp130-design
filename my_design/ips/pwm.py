from amaranth import *
from amaranth import Elaboratable, Module
from amaranth.build import Platform

from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect
from amaranth.lib.cdc import FFSynchronizer
from amaranth_soc import csr

from chipflow_lib.platforms import OutputPinSignature, InputPinSignature

__all__ = ["PWMPeripheral", "PWMPins"]


class PWMPins(wiring.PureInterface):
    class Signature(wiring.Signature):
        def __init__(self):
            super().__init__({
                "pwm":  Out(OutputPinSignature(1)),
                "dir":  Out(OutputPinSignature(1)),
                "stop":  In(InputPinSignature(1)),
            })

        def create(self, *, path=(), src_loc_at=0):
            return PWMPins(path=path, src_loc_at=1 + src_loc_at)

    def __init__(self, *, path=(), src_loc_at=0):
        super().__init__(self.Signature(), path=path, src_loc_at=1 + src_loc_at)


class PWMPeripheral(wiring.Component):
    class Numr(csr.Register, access="rw"):
        """Numerator value for PWM duty cycle"""
        val: csr.Field(csr.action.RW, unsigned(16))

    class Denom(csr.Register, access="rw"):
        """Denominator value for PWM duty cycle
        """
        val: csr.Field(csr.action.RW, unsigned(16))

    class Conf(csr.Register, access="rw"):
        """Enable register
        """
        en: csr.Field(csr.action.RW, unsigned(1))
        dir: csr.Field(csr.action.RW, unsigned(1))
 
    class Stop_int(csr.Register, access="rw"):
        """Stop_int register
        """
        stopped: csr.Field(csr.action.RW1C, unsigned(1))   
            
    class Status(csr.Register, access="r"):
        """Status register
        """
        stop_pin: csr.Field(csr.action.R, unsigned(1))   
      
    """pwm peripheral."""
    def __init__(self, *, name, pins):
        self.pins = pins

        regs = csr.Builder(addr_width=5, data_width=8, name=name)

        self._numr = regs.add("numr", self.Numr(), offset=0x0)
        self._denom = regs.add("denom", self.Denom(), offset=0x4)
        self._conf = regs.add("conf", self.Conf(), offset=0x8)
        self._stop_int = regs.add("stop_int", self.Stop_int(), offset=0xC)
        self._status = regs.add("status", self.Status(), offset=0x10)

        self._bridge = csr.Bridge(regs.as_memory_map())

        super().__init__({
            "bus": In(csr.Signature(addr_width=regs.addr_width, data_width=regs.data_width)),
        })
        self.bus.memory_map = self._bridge.bus.memory_map

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge       
        count = Signal(unsigned(16), reset=0x0)
        connect(m, flipped(self.bus), self._bridge.bus)
        
        #synchronizer
        stop = Signal()
        m.submodules += FFSynchronizer(i=self.pins.stop.i, o=stop)
        m.d.comb += self._stop_int.f.stopped.set.eq(stop)

        with m.If((self._conf.f.en.data == 1) & (self._stop_int.f.stopped.data == 0) ):
            m.d.sync += count.eq(count+1)
        with m.Else():
            m.d.sync += count.eq(0)
            
        with m.If((self._numr.f.val.data > 0) & (count <= self._numr.f.val.data) & (self._conf.f.en.data == 1) & (self._stop_int.f.stopped.data == 0 )):
            m.d.comb += self.pins.pwm.o.eq(1)
        with m.Else():
            m.d.comb += self.pins.pwm.o.eq(0)
            
        with m.If(count >= self._denom.f.val.data):
            m.d.sync += count.eq(0)

        m.d.comb += self.pins.dir.o.eq(self._conf.f.dir.data)
        m.d.comb += self._status.f.stop_pin.r_data.eq(stop)

        return m
