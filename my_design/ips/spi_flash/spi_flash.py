from amaranth import *
from amaranth.lib import enum, data, wiring, stream
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from amaranth_soc import wishbone
from amaranth_soc.memory import MemoryMap

from ..ports import PortGroup
from .glasgow_qspi import QSPIMode, QSPIController


__all__ = ["WishboneQSPIFlashController"]


class QSPIFlashCommand(enum.Enum, shape=8):
    Read                = 0x03
    FastRead            = 0x0B
    FastReadDualOut     = 0x3B
    FastReadQuadOut     = 0x6B
    FastReadDualInOut   = 0xBB
    FastReadQuadInOut   = 0xEB


class WishboneQSPIFlashController(wiring.Component):
    def __init__(self, *, addr_width, data_width):
        super().__init__({
            "wb_bus": In(wishbone.Signature(addr_width=addr_width, data_width=data_width, granularity=8)),
            "spi_bus": Out(wiring.Signature({
                "o_octets": Out(stream.Signature(data.StructLayout({
                    "chip": 1,
                    "mode": QSPIMode,
                    "data": 8,
                }))),
                "i_octets": In(stream.Signature(data.StructLayout({
                    "data": 8,
                }))),
                "divisor": Out(16),
            })),
        })

        self.wb_bus.memory_map = MemoryMap(addr_width=addr_width + exact_log2(data_width // 8),
                                           data_width=8)
        self.wb_bus.memory_map.add_resource(self, name="data", size=0x400000) # FIXME

    def elaborate(self, platform):
        m = Module()

        wb_data_octets = self.wb_bus.data_width // 8

        o_addr_count = Signal(range(3))
        o_data_count = Signal(range(wb_data_octets + 1))
        i_data_count = Signal(range(wb_data_octets + 1))

        flash_addr = self.wb_bus.adr << exact_log2(wb_data_octets)

        with m.FSM():
            with m.State("Wait"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX1)
                m.d.comb += self.spi_bus.o_octets.p.data.eq(QSPIFlashCommand.Read)
                with m.If(self.wb_bus.cyc & self.wb_bus.stb & ~self.wb_bus.we):
                    m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                    with m.If(self.spi_bus.o_octets.ready):
                        m.d.sync += o_addr_count.eq(2)
                        m.next = "SPI-Address"

            with m.State("SPI-Address"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX1)
                m.d.comb += self.spi_bus.o_octets.p.data.eq(flash_addr.word_select(o_addr_count, 8))
                m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                with m.If(self.spi_bus.o_octets.ready):
                    with m.If(o_addr_count != 0):
                        m.d.sync += o_addr_count.eq(o_addr_count - 1)
                    with m.Else():
                        m.next = "SPI-Data-Read"

            with m.State("SPI-Data-Read"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.GetX1)
                with m.If(o_data_count != wb_data_octets):
                    m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                    with m.If(self.spi_bus.o_octets.ready):
                        m.d.sync += o_data_count.eq(o_data_count + 1)

                m.d.comb += self.spi_bus.i_octets.ready.eq(1)
                with m.If(self.spi_bus.i_octets.valid):
                    m.d.sync += self.wb_bus.dat_r.word_select(i_data_count, 8).eq(self.spi_bus.i_octets.p.data)
                    with m.If(i_data_count != wb_data_octets - 1):
                        m.d.sync += i_data_count.eq(i_data_count + 1)
                    with m.Else():
                        m.d.sync += self.wb_bus.ack.eq(1)
                        m.d.sync += o_data_count.eq(0)
                        m.d.sync += i_data_count.eq(0)
                        m.next = "SPI-Deselect"

            with m.State("SPI-Deselect"):
                m.d.sync += self.wb_bus.ack.eq(0)
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(0)
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.Dummy)
                m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                with m.If(self.spi_bus.o_octets.ready):
                    m.next = "Wait"

        return m
