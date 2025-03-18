from chipflow_lib.platforms.sim import SimPlatform
from chipflow_lib.software.soft_gen import SoftwareGenerator

from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect

from amaranth_soc import csr, wishbone
from amaranth_soc.csr.wishbone import WishboneCSRBridge

from amaranth_orchard.base import SoCID
from amaranth_orchard.memory import SPIMemIO
from amaranth_orchard.memory import SRAMPeripheral
from amaranth_orchard.io import GPIOPeripheral
from amaranth_orchard.io import UARTPeripheral
from amaranth_orchard.io import SPISignature, SPIPeripheral
from amaranth_orchard.io import I2CSignature, I2CPeripheral

from amaranth_cv32e40p.cv32e40p import CV32E40P, DebugModule
from chipflow_lib.platforms import InputPinSignature, OutputPinSignature
from .ips.pwm import PWMPins, PWMPeripheral
# from .ips.pdm import PDMPeripheral

__all__ = ["JTAGSignature", "MySoC"]

JTAGSignature = wiring.Signature({
    "trst": Out(InputPinSignature(1)),
    "tck": Out(InputPinSignature(1)),
    "tms": Out(InputPinSignature(1)),
    "tdi": Out(InputPinSignature(1)),
    "tdo": Out(OutputPinSignature(1)),
})


class MySoC(wiring.Component):
    def __init__(self):
        # Top level interfaces

        interfaces = {
            "flash": Out(SPIMemIO.Signature()),
            "cpu_jtag": Out(JTAGSignature)
        }

        self.user_spi_count = 3
        self.i2c_count = 2
        self.motor_count = 10
        self.pdm_ao_count = 6
        self.uart_count = 2

        self.gpio_banks = 2
        self.gpio_width = 8

        for i in range(self.user_spi_count):
            interfaces[f"user_spi_{i}"] = Out(SPISignature)

        for i in range(self.i2c_count):
            interfaces[f"i2c_{i}"] = Out(I2CSignature)

        for i in range(self.motor_count):
            interfaces[f"motor_pwm{i}"] = Out(PWMPins.Signature())

#        for i in range(self.pdm_ao_count):
#            interfaces[f"pdm_ao_{i}"] = Out(PDMPins.Signature())

        for i in range(self.uart_count):
            interfaces[f"uart_{i}"] = Out(UARTPeripheral.Signature())

        for i in range(self.gpio_banks):
            interfaces[f"gpio_{i}"] = Out(GPIOPeripheral.Signature(pin_count=self.gpio_width))

        super().__init__(interfaces)

        # Memory regions:
        self.mem_spiflash_base = 0x00000000
        self.mem_sram_base     = 0x10000000

        # Debug region
        self.debug_base        = 0xa0000000

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

        # Software

        sw = SoftwareGenerator(rom_start=self.bios_start, rom_size=0x00100000,
                               # place BIOS data in SRAM
                               ram_start=self.mem_sram_base, ram_size=self.sram_size)


        # CPU

        cpu = CV32E40P(config="default", reset_vector=self.bios_start, dm_haltaddress=self.debug_base+0x800)
        wb_arbiter.add(cpu.ibus)
        wb_arbiter.add(cpu.dbus)

        m.submodules.cpu = cpu

        # Debug
        debug = DebugModule()
        wb_arbiter.add(debug.initiator)
        wb_decoder.add(debug.target, name="debug", addr=self.debug_base)
        m.d.comb += cpu.debug_req.eq(debug.debug_req)

        m.d.comb += [
            debug.jtag_tck.eq(self.cpu_jtag.tck.i),
            debug.jtag_tms.eq(self.cpu_jtag.tms.i),
            debug.jtag_tdi.eq(self.cpu_jtag.tdi.i),
            debug.jtag_trst.eq(self.cpu_jtag.trst.i),
            self.cpu_jtag.tdo.o.eq(debug.jtag_tdo),
        ]
        # TODO: TRST

        m.submodules.debug = debug
        # SPI flash

        spiflash = SPIMemIO()
        wb_decoder .add(spiflash.data_bus, addr=self.mem_spiflash_base)
        csr_decoder.add(spiflash.ctrl_bus, name="spiflash", addr=self.csr_spiflash_base - self.csr_base)
        m.submodules.spiflash = spiflash

        connect(m, flipped(self.flash), spiflash.pins)

        sw.add_periph("spiflash",   "SPIFLASH", self.csr_spiflash_base)

        # SRAM

        sram = SRAMPeripheral(size=self.sram_size)
        wb_decoder.add(sram.bus, name="sram", addr=self.mem_sram_base)

        m.submodules.sram = sram

        # User SPI
        for i in range(self.user_spi_count):
            user_spi = SPIPeripheral()

            base_addr = self.csr_user_spi_base + i * self.periph_offset
            csr_decoder.add(user_spi.bus, name=f"user_spi_{i}", addr=base_addr  - self.csr_base)
            sw.add_periph("spi", f"USER_SPI_{i}", base_addr)

            # FIXME: These assignments will disappear once we have a relevant peripheral available
            pins = getattr(self, f"user_spi_{i}")
            connect(m, flipped(pins), user_spi.spi_pins)

            setattr(m.submodules, f"user_spi_{i}", user_spi)

        # GPIOs
        for i in range(self.gpio_banks):
            gpio = GPIOPeripheral(pin_count=self.gpio_width)
            base_addr = self.csr_gpio_base + i * self.periph_offset
            csr_decoder.add(gpio.bus, name=f"gpio_{i}", addr=base_addr - self.csr_base)
            sw.add_periph("gpio", f"GPIO_{i}", base_addr)

            pins = getattr(self, f"gpio_{i}")
            connect(m, flipped(pins), gpio.pins)
            setattr(m.submodules, f"gpio_{i}", gpio)

        # UART
        for i in range(self.uart_count):
            uart = UARTPeripheral(init_divisor=int(25e6//115200), addr_width=5)
            base_addr = self.csr_uart_base + i * self.periph_offset
            csr_decoder.add(uart.bus, name=f"uart_{i}", addr=base_addr - self.csr_base)
            sw.add_periph("uart", f"UART_{i}", base_addr)

            pins = getattr(self, f"uart_{i}")
            connect(m, flipped(pins), uart.pins)
            setattr(m.submodules, f"uart_{i}", uart)

        # I2Cs
        for i in range(self.i2c_count):
            # TODO: create a I2C peripheral and replace this GPIO
            i2c = I2CPeripheral()

            base_addr = self.csr_i2c_base + i * self.periph_offset
            csr_decoder.add(i2c.bus, name=f"i2c_{i}", addr=base_addr - self.csr_base)
            sw.add_periph("i2c", f"I2C_{i}", base_addr)

            i2c_pins = getattr(self, f"i2c_{i}")
            connect(m, flipped(i2c_pins), i2c.i2c_pins)

            setattr(m.submodules, f"i2c_{i}", i2c)

        # Motor drivers
        for i in range(self.motor_count):
            motor_pwm = PWMPeripheral(pins=getattr(self, f"motor_pwm{i}"))
            base_addr = self.csr_motor_base + i * self.motor_offset
            csr_decoder.add(motor_pwm.bus, name=f"motor_pwm{i}", addr=base_addr - self.csr_base)

            sw.add_periph("motor_pwm", f"MOTOR_PWM{i}", base_addr)
            setattr(m.submodules, f"motor_pwm{i}", motor_pwm)

        # # pdm_ao
        # for i in range(self.pdm_ao_count):
        #     pdm = PDMPeripheral(bitwidth=10)
        #     base_addr = self.csr_pdm_ao_base + i * self.pdm_ao_offset
        #     csr_decoder.add(pdm.bus, name=f"pdm{i}", addr=base_addr  - self.csr_base)
        # 
        #     sw.add_periph("pdm", f"PDM{i}", base_addr)
        #     setattr(m.submodules, f"pdm{i}", pdm)
        #     m.d.comb += getattr(self, f"pdm_ao_{i}").eq(pdm.pdm_ao)

        # SoC ID

        soc_id = SoCID(type_id=0xCA7F100F)
        csr_decoder.add(soc_id.bus, name="soc_id", addr=self.csr_soc_id_base - self.csr_base)

        m.submodules.soc_id = soc_id

        # Wishbone-CSR bridge

        wb_to_csr = WishboneCSRBridge(csr_decoder.bus, data_width=32)
        wb_decoder.add(wb_to_csr.wb_bus, name="csr", addr=self.csr_base, sparse=False)

        m.submodules.wb_to_csr = wb_to_csr

        # Debug support

        # m.submodules.jtag_provider = platform.providers.JTAGProvider(debug)

        if isinstance(platform, SimPlatform):
            m.submodules.wb_mon = platform.add_monitor("wb_mon", wb_decoder.bus)

        sw.add_periph("soc_id",     "SOC_ID",   self.csr_soc_id_base)
        #sw.add_periph("gpio",       "BTN_GPIO", self.csr_btn_gpio_base)

        sw.generate("build/software/generated")

        return m


if __name__ == "__main__":
    from amaranth.back import verilog
    soc_top = MySoC()
    with open("build/soc_top.v", "w") as f:
        f.write(verilog.convert(soc_top, name="soc_top"))
