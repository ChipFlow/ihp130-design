from amaranth import *
from amaranth.lib import enum, data, wiring, stream, io
from amaranth.lib.wiring import In, Out
from amaranth.sim import Simulator, BrokenTrigger
from amaranth.utils import exact_log2

from amaranth_soc import wishbone
from amaranth_soc.memory import MemoryMap

from ..ports import PortGroup
from .qspi import QSPIMode, QSPIController


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
                # m.d.comb += self.spi_bus.o_octets.p.data.eq(QSPIFlashCommand.FastReadQuadInOut) # FIXME
                m.d.comb += self.spi_bus.o_octets.p.data.eq(QSPIFlashCommand.Read)
                with m.If(self.wb_bus.cyc & self.wb_bus.stb & ~self.wb_bus.we):
                    m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                    with m.If(self.spi_bus.o_octets.ready):
                        m.d.sync += o_addr_count.eq(2)
                        m.next = "SPI-Address"

            with m.State("SPI-Address"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                # m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX4) # FIXME
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX1)
                m.d.comb += self.spi_bus.o_octets.p.data.eq(flash_addr.word_select(o_addr_count, 8))
                m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                with m.If(self.spi_bus.o_octets.ready):
                    with m.If(o_addr_count != 0):
                        m.d.sync += o_addr_count.eq(o_addr_count - 1)
                    with m.Else():
                        m.next = "SPI-Dummy"

            with m.State("SPI-Dummy"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                # m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX4) # FIXME
                m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.PutX1)
                m.d.comb += self.spi_bus.o_octets.valid.eq(1)
                with m.If(self.spi_bus.o_octets.ready):
                    m.next = "SPI-Data-Read"

            with m.State("SPI-Data-Read"):
                m.d.comb += self.spi_bus.o_octets.p.chip.eq(1)
                # m.d.comb += self.spi_bus.o_octets.p.mode.eq(QSPIMode.GetX4) # FIXME
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


async def stream_get(ctx, stream):
    ctx.set(stream.ready, 1)
    payload, = await ctx.tick().sample(stream.payload).until(stream.valid)
    ctx.set(stream.ready, 0)
    return payload


async def stream_put(ctx, stream, payload):
    ctx.set(stream.payload, payload)
    ctx.set(stream.valid, 1)
    await ctx.tick().until(stream.ready)
    ctx.set(stream.valid, 0)


async def wishbone_read(ctx, bus, addr):
    ctx.set(bus.cyc, 1)
    ctx.set(bus.stb, 1)
    ctx.set(bus.adr, addr)
    data, = await ctx.tick().sample(bus.dat_r).until(bus.ack)
    return data


def simulate_flash(ports, memory):
    class CSDeasserted(Exception):
        pass

    async def watch_cs(cs_o, triggers):
        try:
            *values, posedge_cs_o = await triggers.posedge(cs_o)
        except BrokenTrigger: # Workaround for amaranth bug: https://github.com/amaranth-lang/amaranth/issues/1508
            raise CSDeasserted # both our original trigger and posedge of cs happened at the same time. We choose to prioritize CS being deasserted.
        if posedge_cs_o == 1:
            raise CSDeasserted
        return values

    async def dev_get(ctx, ports, *, x):
        sck, io0, io1, io2, io3, cs = ports.sck, *ports.io, ports.cs
        word = 0
        for _ in range(0, 8, x):
            if ctx.get(sck.o):
                await watch_cs(cs.o, ctx.negedge(sck.o))
            _, io0_oe, io0_o, io1_oe, io1_o, io2_oe, io2_o, io3_oe, io3_o = \
                await watch_cs(cs.o, ctx.posedge(sck.o).sample(
                    io0.oe, io0.o, io1.oe, io1.o, io2.oe, io2.o, io3.oe, io3.o))
            if x == 1:
                assert (io0_oe, io1_oe, io2_oe, io3_oe) == (1, 0, 0, 0)
                word = (word << 1) | (io0_o << 0)
            if x == 2:
                assert (io0_oe, io1_oe, io2_oe, io3_oe) == (1, 1, 0, 0)
                word = (word << 2) | (io1_o << 1) | (io0_o << 0)
            if x == 4:
                assert (io0_oe, io1_oe, io2_oe, io3_oe) == (1, 1, 1, 1)
                word = (word << 4) | (io3_o << 3) | (io2_o << 2) | (io1_o << 1) | (io0_o << 0)
        return word

    async def dev_nop(ctx, ports, *, x, cycles):
        sck, io0, io1, io2, io3, cs = ports.sck, *ports.io, ports.cs
        for _ in range(cycles):
            if ctx.get(sck.o):
                await watch_cs(cs.o, ctx.negedge(sck.o))
            _, io0_oe, io1_oe, io2_oe, io3_oe = \
                await watch_cs(cs.o, ctx.posedge(sck.o).sample(io0.oe, io1.oe, io2.oe, io3.oe))
            if x == 1:
                assert (        io1_oe, io2_oe, io3_oe) == (   0, 0, 0)
            else:
                pass # assert (io0_oe, io1_oe, io2_oe, io3_oe) == (0, 0, 0, 0)

    async def dev_put(ctx, ports, word, *, x):
        sck, io0, io1, io2, io3, cs = ports.sck, *ports.io, ports.cs
        for _ in range(0, 8, x):
            if ctx.get(sck.o):
                await watch_cs(cs.o, ctx.negedge(sck.o))
            if x == 1:
                ctx.set(Cat(io1.i), (word >> 7))
                word = (word << 1) & 0xff
            if x == 2:
                ctx.set(Cat(io0.i, io1.i), (word >> 6))
                word = (word << 2) & 0xff
            if x == 4:
                ctx.set(Cat(io0.i, io1.i, io2.i, io3.i), (word >> 4))
                word = (word << 4) & 0xff
            _, io0_oe, io1_oe, io2_oe, io3_oe = \
                await watch_cs(cs.o, ctx.posedge(sck.o).sample(io0.oe, io1.oe, io2.oe, io3.oe))
            assert (io0_oe, io1_oe, io2_oe, io3_oe) == (x == 1, 0, 0, 0)

    async def testbench(ctx):
        await ctx.negedge(ports.cs.o)
        while True:
            try:
                cmd = await dev_get(ctx, ports, x=1)
                if cmd in (0x03, 0x0B, 0x3B, 0x6B, 0xBB, 0xEB):
                    if cmd in (0x03, 0x0B, 0x3B, 0x6B):
                        addr2 = await dev_get(ctx, ports, x=1)
                        addr1 = await dev_get(ctx, ports, x=1)
                        addr0 = await dev_get(ctx, ports, x=1)
                    if cmd == 0xBB:
                        addr2 = await dev_get(ctx, ports, x=2)
                        addr1 = await dev_get(ctx, ports, x=2)
                        addr0 = await dev_get(ctx, ports, x=2)
                    if cmd == 0xEB:
                        addr2 = await dev_get(ctx, ports, x=4)
                        addr1 = await dev_get(ctx, ports, x=4)
                        addr0 = await dev_get(ctx, ports, x=4)
                    if cmd == 0x03:
                        pass
                    if cmd == 0x0B:
                        await dev_nop(ctx, ports, x=1, cycles=8)
                    if cmd in (0x3B, 0xBB):
                        await dev_nop(ctx, ports, x=2, cycles=4)
                    if cmd in (0x6B, 0xEB):
                        await dev_nop(ctx, ports, x=4, cycles=2)
                    addr = (addr2 << 16) | (addr1 << 8) | (addr0 << 0)
                    while True:
                        if addr >= len(memory):
                            addr = 0
                        if cmd in (0x03, 0x0B):
                            await dev_put(ctx, ports, memory[addr], x=1)
                        if cmd in (0x3B, 0xBB):
                            await dev_put(ctx, ports, memory[addr], x=2)
                        if cmd in (0x6B, 0xEB):
                            await dev_put(ctx, ports, memory[addr], x=4)
                        addr += 1
            except CSDeasserted:
                await ctx.negedge(ports.cs.o)
                continue

    return testbench


def test_wishbone_spi_flash_controller_unit():
    dut = WishboneQSPIFlashController(addr_width=30, data_width=32)

    async def tb_wishbone(ctx):
        assert (data := await wishbone_read(ctx, dut.wb_bus, 0x012345)) == 0xab01cd02, f"{data:x}"

    async def tb_spi_flash(ctx):
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.PutX1, "data": QSPIFlashCommand.FastReadQuadInOut}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.PutX4, "data": 0x04}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.PutX4, "data": 0x8d}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.PutX4, "data": 0x14}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.PutX4, "data": 0}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.GetX4, "data": 0}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.GetX4, "data": 0}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.GetX4, "data": 0}, f"{payload}"
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 1, "mode": QSPIMode.GetX4, "data": 0}, f"{payload}"
        await stream_put(ctx, dut.spi_bus.i_octets, {"data": 0x02})
        await stream_put(ctx, dut.spi_bus.i_octets, {"data": 0xcd})
        await stream_put(ctx, dut.spi_bus.i_octets, {"data": 0x01})
        await stream_put(ctx, dut.spi_bus.i_octets, {"data": 0xab})
        assert (payload := await stream_get(ctx, dut.spi_bus.o_octets)) == \
            {"chip": 0, "mode": QSPIMode.Dummy, "data": 0}, f"{payload}"

    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_testbench(tb_wishbone)
    sim.add_testbench(tb_spi_flash)
    with sim.write_vcd("test_unit.vcd"):
        sim.run()


def test_wishbone_spi_flash_controller_integration():
    ports = PortGroup()
    ports.sck = io.SimulationPort("o",  1)
    ports.io  = io.SimulationPort("io", 4)
    ports.cs  = io.SimulationPort("o",  1)

    m = Module()
    m.submodules.qspi = dut_qspi = QSPIController(ports)
    m.submodules.ctrl = dut_ctrl = WishboneQSPIFlashController(addr_width=30, data_width=32)
    wiring.connect(m, dut_ctrl.spi_bus, dut_qspi)

    async def tb_wishbone(ctx):
        assert (data := await wishbone_read(ctx, dut_ctrl.wb_bus, 0x00)) == 0x01020304, f"{data:x}"
        assert (data := await wishbone_read(ctx, dut_ctrl.wb_bus, 0x01)) == 0x0a0b0c0d, f"{data:x}"
        assert (data := await wishbone_read(ctx, dut_ctrl.wb_bus, 0x02)) == 0x00000000, f"{data:x}"

    sim = Simulator(m)
    sim.add_clock(1e-6)
    sim.add_testbench(tb_wishbone)
    sim.add_testbench(simulate_flash(ports, b"\x04\x03\x02\x01\x0d\x0c\x0b\x0a\x00\x00\x00\x00"),
        background=True)
    with sim.write_vcd("test_integration.vcd"):
        sim.run()


if __name__ == "__main__":
    test_wishbone_spi_flash_controller_unit()
    test_wishbone_spi_flash_controller_integration()
