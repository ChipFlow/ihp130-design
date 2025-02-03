from chipflow_lib.platforms.sim import SimPlatform
from chipflow_lib.software.soft_gen import SoftwareGenerator

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr, wishbone
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc import gpio

from amaranth_orchard.memory.spimemio import SPIMemIO, QSPIPins
from amaranth_orchard.io.uart import UARTPeripheral, UARTPins
from amaranth_orchard.memory.sram import SRAMPeripheral
from amaranth_orchard.base.platform_timer import PlatformTimer
from amaranth_orchard.base.soc_id import SoCID

from minerva.core import Minerva

from .ips.spi import SPISignature, SPIPeripheral
from .ips.i2c import I2CSignature, I2CPeripheral
from .ips.pwm import PWMPins, PWMPeripheral
from .ips.pdm import PDMPeripheral

__all__ = ["MySoC"]


class MySoC(wiring.Component):
    def __init__(self):
        # Top level interfaces

        interfaces = {}
        self.uart_count = 1

        for i in range(self.uart_count):
            interfaces[f"uart_{i}"] = Out(UARTPins.Signature())

        super().__init__(interfaces)


        # CSR regions:
        self.csr_base          = 0xb0000000
        self.periph_offset     = 0x00100000
         
        self.csr_uart_base     = 0xb1000000
        self.csr_soc_id_base   = 0xb4000000

        self.sram_size  = 0x800 # 2KiB
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
        cpu = Minerva(reset_address=self.bios_start)
        wb_arbiter.add(cpu.ibus)
        wb_arbiter.add(cpu.dbus)

        m.submodules.cpu = cpu

        # TODO: TRST


        # UART
        for i in range(self.uart_count):
            uart = UARTPeripheral(init_divisor=int(25e6//115200), pins=getattr(self, f"uart_{i}"))
            base_addr = self.csr_uart_base + i * self.periph_offset
            csr_decoder.add(uart.bus, name=f"uart_{i}", addr=base_addr - self.csr_base)

            setattr(m.submodules, f"uart_{i}", uart)

        # SoC ID

        soc_id = SoCID(type_id=0xCA7F100F)
        csr_decoder.add(soc_id.bus, name="soc_id", addr=self.csr_soc_id_base - self.csr_base)

        m.submodules.soc_id = soc_id


        # Wishbone-CSR bridge

        wb_to_csr = WishboneCSRBridge(csr_decoder.bus, data_width=32)
        wb_decoder.add(wb_to_csr.wb_bus, name="csr", addr=self.csr_base, sparse=False)

        m.submodules.wb_to_csr = wb_to_csr


        if isinstance(platform, SimPlatform):
            m.submodules.wb_mon = platform.add_monitor("wb_mon", wb_decoder.bus)


        return m


if __name__ == "__main__":
    from amaranth.back import verilog
    soc_top = MySoC()
    with open("build/soc_top.v", "w") as f:
        f.write(verilog.convert(soc_top, name="soc_top"))
