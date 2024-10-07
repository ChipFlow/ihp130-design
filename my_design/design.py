from amaranth import *
from amaranth.lib import io, wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr, wishbone
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc.wishbone.sram import WishboneSRAM

from amaranth_orchard.io.uart import UARTPeripheral, UARTPins

from minerva.core import Minerva

from .ips.i2c import I2CSignature, I2CPeripheral
from .ips.spi_flash import PortGroup, QSPIController, WishboneQSPIFlashController
from .ips.riscv_timer import RISCVMachineTimer


__all__ = ["MySoC"]


class _QSPIPinsSignature(wiring.Signature):
    def __init__(self):
        super().__init__({
            "clk_o": Out(1),
            "csn_o": Out(1),
            "d_o":   Out(4),
            "d_oe":  Out(4),
            "d_i":   In(4),
        })


class MySoC(wiring.Component):
    def __init__(self):
        super().__init__({
            "flash":  Out(_QSPIPinsSignature()),
            "i2c_0":  Out(I2CSignature),
            "uart_0": Out(UARTPins.Signature()),
        })

        # Memory regions:
        self.mem_spiflash_base = 0x00000000
        self.mem_sram_base     = 0x10000000

        # CSR regions:
        self.csr_base          = 0xb0000000
        self.csr_spiflash_base = 0xb0000000

        self.csr_uart_base     = 0xb2000000
        self.csr_timer_base    = 0xb3000000
        self.csr_i2c_base      = 0xb6000000

        self.sram_size  = 0x400 # 1KiB
        self.bios_start = 0x100000 # 1MiB into spiflash to make room for a bitstream

    def elaborate(self, platform):
        m = Module()

        wb_arbiter  = wishbone.Arbiter(addr_width=30, data_width=32, granularity=8)
        wb_decoder  = wishbone.Decoder(addr_width=30, data_width=32, granularity=8)
        csr_decoder = csr.Decoder(addr_width=28, data_width=8)

        m.submodules.wb_arbiter  = wb_arbiter
        m.submodules.wb_decoder  = wb_decoder
        m.submodules.csr_decoder = csr_decoder

        connect(m, wb_arbiter.bus, wb_decoder.bus)

        # CPU

        m.submodules.cpu = cpu = Minerva(reset_address=self.bios_start)

        wb_arbiter.add(cpu.ibus)
        wb_arbiter.add(cpu.dbus)

        # SPI flash

        qspi_port = PortGroup()
        qspi_port.sck = io.SimulationPort("o",  1)
        qspi_port.io0 = io.SimulationPort("io", 1)
        qspi_port.io1 = io.SimulationPort("io", 1)
        qspi_port.io2 = io.SimulationPort("io", 1)
        qspi_port.io3 = io.SimulationPort("io", 1)
        qspi_port.cs  = io.SimulationPort("o",  1)

        qspi = QSPIController(qspi_port)
        spiflash = WishboneQSPIFlashController(addr_width=24, data_width=32)
        m.submodules.qspi = qspi
        m.submodules.spiflash = spiflash

        wb_decoder.add(spiflash.wb_bus, name="spiflash", addr=self.mem_spiflash_base)

        connect(m, spiflash.spi_bus, qspi)

        m.d.comb += [
            self.flash.clk_o.eq(qspi_port.sck.o),
            self.flash.csn_o.eq(~qspi_port.cs.o),

            self.flash.d_o [0].eq(qspi_port.io0.o),
            self.flash.d_oe[0].eq(qspi_port.io0.oe),
            self.flash.d_o [1].eq(qspi_port.io1.o),
            self.flash.d_oe[1].eq(qspi_port.io1.oe),
            self.flash.d_o [2].eq(qspi_port.io2.o),
            self.flash.d_oe[2].eq(qspi_port.io2.oe),
            self.flash.d_o [3].eq(qspi_port.io3.o),
            self.flash.d_oe[3].eq(qspi_port.io3.oe),

            qspi_port.io0.i.eq(self.flash.d_i[0]),
            qspi_port.io1.i.eq(self.flash.d_i[1]),
            qspi_port.io2.i.eq(self.flash.d_i[2]),
            qspi_port.io3.i.eq(self.flash.d_i[3]),
        ]

        # SRAM

        m.submodules.sram = sram = WishboneSRAM(size=self.sram_size, data_width=32, granularity=8)
        wb_decoder.add(sram.wb_bus, name="sram", addr=self.mem_sram_base)

        # UART

        m.submodules.uart = uart = UARTPeripheral(init_divisor=int(25e6//115200), pins=self.uart_0)
        csr_decoder.add(uart.bus, name="uart", addr=self.csr_uart_base - self.csr_base)

        # Timer

        m.submodules.timer = timer = RISCVMachineTimer()
        csr_decoder.add(timer.bus, name="timer", addr=self.csr_timer_base - self.csr_base)

        m.d.comb += cpu.timer_interrupt.eq(timer.irq)

        # I²C

        m.submodules.i2c = i2c = I2CPeripheral()
        csr_decoder.add(i2c.bus, name="i2c", addr=self.csr_i2c_base  - self.csr_base)

        connect(m, flipped(self.i2c_0), i2c.i2c_pins)

        # Wishbone-CSR bridge

        m.submodules.wb_to_csr = wb_to_csr = WishboneCSRBridge(csr_decoder.bus, data_width=32)
        wb_decoder.add(wb_to_csr.wb_bus, name="csr", addr=self.csr_base, sparse=False)

        return m


if __name__ == "__main__":
    from amaranth.back import verilog
    soc_top = MySoC()
    with open("build/soc_top.v", "w") as f:
        f.write(verilog.convert(soc_top, name="soc_top"))
