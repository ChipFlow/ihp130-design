from chipflow_lib.platforms.sim import SimPlatform
from chipflow_lib.software.soft_gen import SoftwareGenerator

from amaranth import *
from amaranth.lib import io, wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr, wishbone
from amaranth_soc.csr.wishbone import WishboneCSRBridge
from amaranth_soc.wishbone.sram import WishboneSRAM
from amaranth_soc import gpio

from amaranth_orchard.io.uart import UARTPeripheral, UARTPins
from amaranth_orchard.base.platform_timer import PlatformTimer
from amaranth_orchard.base.soc_id import SoCID

from minerva.core import Minerva

from .ips.spi_flash import PortGroup, QSPIController, WishboneQSPIFlashController
from .ips.spi import SPISignature, SPIPeripheral
from .ips.i2c import I2CSignature, I2CPeripheral
from .ips.pwm import PWMPins, PWMPeripheral
from .ips.pdm import PDMPeripheral


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
        # Top level interfaces

        self.user_spi_count = 3
        self.i2c_count      = 2
        self.motor_count    = 10
        self.pdm_ao_count   = 6
        self.uart_count     = 2
        self.gpio_banks     = 2
        self.gpio_width     = 8

        members = {"flash": Out(_QSPIPinsSignature())}

        for i in range(self.user_spi_count):
            members[f"user_spi_{i}"] = Out(SPISignature)
        for i in range(self.i2c_count):
            members[f"i2c_{i}"] = Out(I2CSignature)
        for i in range(self.motor_count):
            members[f"motor_pwm{i}"] = Out(PWMPins.Signature())
        for i in range(self.pdm_ao_count):
            members[f"pdm_ao_{i}"] = Out(1)
        for i in range(self.uart_count):
            members[f"uart_{i}"] = Out(UARTPins.Signature())
        for i in range(self.gpio_banks):
            members[f"gpio_{i}"] = Out(gpio.PinSignature()).array(self.gpio_width)

        super().__init__(members)

        # Memory regions:
        self.mem_spiflash_base = 0x00000000
        self.mem_sram_base     = 0x10000000

        # CSR regions:
        self.csr_base          = 0xb0000000
        self.csr_spiflash_base = 0xb0000000

        self.csr_gpio_base     = 0xb1000000
        self.csr_uart_base     = 0xb2000000
        self.csr_soc_id_base   = 0xb4000000

        self.csr_user_spi_base = 0xb5000000
        self.csr_i2c_base      = 0xb6000000
        self.csr_motor_base    = 0xb7000000
        self.csr_pdm_ao_base   = 0xb8000000

        self.periph_offset     = 0x00100000
        self.motor_offset      = 0x00000100
        self.pdm_ao_offset     = 0x00000010

        self.sram_size  = 0x2000   # 8KiB
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

        # Software

        sw = SoftwareGenerator(rom_start=self.bios_start, rom_size=0x00100000,
                               # place BIOS data in SRAM
                               ram_start=self.mem_sram_base, ram_size=self.sram_size)

        # CPU

        m.submodules.cpu = cpu = Minerva(with_muldiv=True, reset_address=self.bios_start)

        wb_arbiter.add(cpu.ibus)
        wb_arbiter.add(cpu.dbus)

        # SPI flash

        qspi_port = PortGroup(
            sck = io.SimulationPort("o",  1),
            io  = io.SimulationPort("io", 4),
            cs  = io.SimulationPort("o",  1),
        )
        qspi_port = PortGroup()
        qspi_port.sck = io.SimulationPort("o",  1)
        qspi_port.io0 = io.SimulationPort("io", 1)
        qspi_port.io1 = io.SimulationPort("io", 1)
        qspi_port.io2 = io.SimulationPort("io", 1)
        qspi_port.io3 = io.SimulationPort("io", 1)
        qspi_port.cs  = io.SimulationPort("o",  1)

        m.d.comb += [
            self.flash.clk_o.eq(qspi_port.sck.o),
            self.flash.csn_o.eq(~qspi_port.cs.o),

            self.flash.d_o [0].eq(qspi_port.io0.o),
            self.flash.d_o [1].eq(qspi_port.io1.o),
            self.flash.d_o [2].eq(qspi_port.io2.o),
            self.flash.d_o [3].eq(qspi_port.io3.o),

            self.flash.d_oe[0].eq(qspi_port.io0.oe),
            self.flash.d_oe[1].eq(qspi_port.io1.oe),
            self.flash.d_oe[2].eq(qspi_port.io2.oe),
            self.flash.d_oe[3].eq(qspi_port.io3.oe),

            qspi_port.io0.i.eq(self.flash.d_i[0]),
            qspi_port.io1.i.eq(self.flash.d_i[1]),
            qspi_port.io2.i.eq(self.flash.d_i[2]),
            qspi_port.io3.i.eq(self.flash.d_i[3]),
        ]

        qspi = QSPIController(qspi_port)
        spiflash = WishboneQSPIFlashController(addr_width=24, data_width=32)
        m.submodules.qspi = qspi
        m.submodules.spiflash = spiflash

        connect(m, spiflash.spi_bus, qspi)

        wb_decoder.add(spiflash.wb_bus, name="spiflash", addr=self.mem_spiflash_base)

        # SRAM

        m.submodules.sram = sram = WishboneSRAM(size=self.sram_size, data_width=32, granularity=8)
        wb_decoder.add(sram.wb_bus, name="sram", addr=self.mem_sram_base)

        # User SPI

        for i in range(self.user_spi_count):
            m.submodules[f"user_spi_{i}"] = user_spi = SPIPeripheral()

            base_addr = self.csr_user_spi_base + i * self.periph_offset
            csr_decoder.add(user_spi.bus, name=f"user_spi_{i}", addr=base_addr  - self.csr_base)

            # FIXME: These assignments will disappear once we have a relevant peripheral available
            spi_pins = getattr(self, f"user_spi_{i}")
            connect(m, flipped(spi_pins), user_spi.spi_pins)

            sw.add_periph("spi", f"USER_SPI_{i}", base_addr)

        # GPIOs

        for i in range(self.gpio_banks):
            gpio_bank = gpio.Peripheral(pin_count=8, addr_width=4, data_width=8)
            m.submodules[f"gpio_{i}"] = gpio_bank

            base_addr = self.csr_gpio_base + i * self.periph_offset
            csr_decoder.add(gpio_bank.bus, name=f"gpio_{i}", addr=base_addr - self.csr_base)

            gpio_bank_pins = getattr(self, f"gpio_{i}")
            for n in range(8):
                connect(m, gpio_bank.pins[n], flipped(gpio_bank_pins[n]))

            sw.add_periph("gpio", f"GPIO_{i}", base_addr)

        # UART

        for i in range(self.uart_count):
            m.submodules[f"uart_{i}"] = uart = UARTPeripheral(init_divisor=int(25e6//115200),
                                                              pins=getattr(self, f"uart_{i}"))

            base_addr = self.csr_uart_base + i * self.periph_offset
            csr_decoder.add(uart.bus, name=f"uart_{i}", addr=base_addr - self.csr_base)

            sw.add_periph("uart", f"UART_{i}", base_addr)

        # I2Cs

        for i in range(self.i2c_count):
            # TODO: create a I2C peripheral and replace this GPIO
            m.submodules[f"i2c_{i}"] = i2c = I2CPeripheral()

            base_addr = self.csr_i2c_base + i * self.periph_offset
            csr_decoder.add(i2c.bus, name=f"i2c_{i}", addr=base_addr  - self.csr_base)

            i2c_pins = getattr(self, f"i2c_{i}")
            connect(m, flipped(i2c_pins), i2c.i2c_pins)

            sw.add_periph("i2c", f"I2C_{i}", base_addr)

        # Motor drivers

        for i in range(self.motor_count):
            motor_pwm = PWMPeripheral(pins=getattr(self, f"motor_pwm{i}"))
            m.submodules[f"motor_pwm{i}"] = motor_pwm

            base_addr = self.csr_motor_base + i * self.motor_offset
            csr_decoder.add(motor_pwm.bus, name=f"motor_pwm{i}", addr=base_addr  - self.csr_base)

            sw.add_periph("motor_pwm", f"MOTOR_PWM{i}", base_addr)

        # pdm_ao

        for i in range(self.pdm_ao_count):
            m.submodules[f"pdm{i}"] = pdm = PDMPeripheral(bitwidth=10)
            m.d.comb += getattr(self, f"pdm_ao_{i}").eq(pdm.pdm_ao)

            base_addr = self.csr_pdm_ao_base + i * self.pdm_ao_offset
            csr_decoder.add(pdm.bus, name=f"pdm{i}", addr=base_addr  - self.csr_base)

            sw.add_periph("pdm", f"PDM{i}", base_addr)

        # SoC ID

        m.submodules.soc_id = soc_id = SoCID(type_id=0xCA7F100F)
        csr_decoder.add(soc_id.bus, name="soc_id", addr=self.csr_soc_id_base - self.csr_base)

        sw.add_periph("soc_id", "SOC_ID", self.csr_soc_id_base)

        # Wishbone-CSR bridge

        m.submodules.wb_to_csr = wb_to_csr = WishboneCSRBridge(csr_decoder.bus, data_width=32)
        wb_decoder.add(wb_to_csr.wb_bus, name="csr", addr=self.csr_base, sparse=False)

        # Debug support

        if isinstance(platform, SimPlatform):
            m.submodules.wb_mon = platform.add_monitor("wb_mon", wb_decoder.bus)

        sw.generate("build/software/generated")

        return m


if __name__ == "__main__":
    from amaranth.back import verilog
    soc_top = MySoC()
    with open("build/soc_top.v", "w") as f:
        f.write(verilog.convert(soc_top, name="soc_top"))
