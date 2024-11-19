from amaranth import *
from amaranth.lib import io, wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr
from amaranth_stdio.serial import AsyncSerialRX, AsyncSerialTX

from .ports import PortGroup


__all__ = ["UARTPeripheral"]


class UARTPeripheral(wiring.Component):
    class TxData(csr.Register, access="w"):
        """valid to write to when tx_ready is 1, will trigger a transmit"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.W, 8))

    class RxData(csr.Register, access="r"):
        """valid to read from when rx_avail is 1, last received byte"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.R, 8))

    class TxReady(csr.Register, access="r"):
        """is '1' when 1-byte transmit buffer is empty"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.R, 1))

    class RxAvail(csr.Register, access="r"):
        """is '1' when 1-byte receive buffer is full; reset by a read from rx_data"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.R, 1))

    class Divisor(csr.Register, access="rw"):
        """baud divider, defaults to init_divisor"""
        def __init__(self, init_divisor):
            super().__init__(csr.Field(csr.action.RW, 24, init=init_divisor))

    """
    A custom, minimal UART.

    TODO: Interrupts support, perhaps mimic something with upstream Linux kernel support...
    """
    def __init__(self, *, ports, init_divisor):
        assert len(ports.rx) == 1 and ports.rx.direction in (io.Direction.Input, io.Direction.Bidir)
        assert len(ports.tx) == 1 and ports.tx.direction in (io.Direction.Output, io.Direction.Bidir)

        self.ports = PortGroup(rx=ports.rx, tx=ports.tx)
        self.init_divisor = init_divisor

        regs = csr.Builder(addr_width=5, data_width=8)

        self._tx_data  = regs.add("tx_data",  self.TxData(),  offset=0x00)
        self._rx_data  = regs.add("rx_data",  self.RxData(),  offset=0x04)
        self._tx_ready = regs.add("tx_ready", self.TxReady(), offset=0x08)
        self._rx_avail = regs.add("rx_avail", self.RxAvail(), offset=0x0c)
        self._divisor  = regs.add("divisor",  self.Divisor(init_divisor), offset=0x10)

        self._bridge = csr.Bridge(regs.as_memory_map())

        super().__init__({
            "csr_bus": In(csr.Signature(addr_width=regs.addr_width, data_width=regs.data_width)),
        })
        self.csr_bus.memory_map = self._bridge.bus.memory_map

    def elaborate(self, platform):
        m = Module()
        m.submodules.bridge = self._bridge

        connect(m, flipped(self.csr_bus), self._bridge.bus)

        m.submodules.rx_buffer = rx_buffer = io.Buffer("i", self.ports.rx)
        m.submodules.tx_buffer = tx_buffer = io.Buffer("o", self.ports.tx)

        m.submodules.tx = tx = AsyncSerialTX(divisor=self.init_divisor, divisor_bits=24)
        m.d.comb += [
            tx_buffer.o.eq(tx.o),
            tx.data.eq(self._tx_data.f.w_data),
            tx.ack.eq(self._tx_data.f.w_stb),
            self._tx_ready.f.r_data.eq(tx.rdy),
            tx.divisor.eq(self._divisor.f.data)
        ]

        rx_buf = Signal(unsigned(8))
        rx_avail = Signal()

        m.submodules.rx = rx = AsyncSerialRX(divisor=self.init_divisor, divisor_bits=24)

        with m.If(self._rx_data.f.r_stb):
            m.d.sync += rx_avail.eq(0)

        with m.If(rx.rdy):
            m.d.sync += [
                rx_buf.eq(rx.data),
                rx_avail.eq(1)
            ]

        m.d.comb += [
            rx.i.eq(rx_buffer.i),
            rx.ack.eq(~rx_avail),
            rx.divisor.eq(self._divisor.f.data),
            self._rx_data.f.r_data.eq(rx_buf),
            self._rx_avail.f.r_data.eq(rx_avail)
        ]

        return m
