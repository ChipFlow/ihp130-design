from amaranth import *
from amaranth.lib.cdc import FFSynchronizer

from ..design import MySoC

class ChipflowTop(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        def _connect_interface(interface, name):
            pins = dict()
            for member in interface.signature.members:
                pin, suffix = member.rsplit("_", 2)
                assert suffix in ("o", "i", "oe"), suffix
                pins[pin] = getattr(interface, member).width
            for pin, width in pins.items():
                for i in range(width):
                    platform_pin = platform.request(f"{name}_{pin}{'' if width == 1 else str(i)}")
                    if hasattr(interface, f"{pin}_i"):
                        m.d.comb += getattr(interface, f"{pin}_i")[i].eq(platform_pin.i)
                    if hasattr(interface, f"{pin}_o"):
                        m.d.comb += platform_pin.o.eq(getattr(interface, f"{pin}_o")[i])
                    if hasattr(interface, f"{pin}_oe"):
                        m.d.comb += platform_pin.oe.eq(getattr(interface, f"{pin}_oe")[i])

        # Clock generation
        m.domains.sync = ClockDomain()

        clk = platform.request("sys_clk")
        m.d.comb += ClockSignal().eq(clk.i)
        m.submodules.rst_sync = FFSynchronizer(
            ~platform.request("sys_rst_n").i,
            ResetSignal())

        # heartbeat led (to confirm clock/reset alive)
        heartbeat_ctr = Signal(23)
        m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)
        m.d.comb += platform.request("heartbeat").o.eq(heartbeat_ctr[-1])

        m.submodules.soc = soc = MySoC()

        _connect_interface(soc.flash, "flash")

        _connect_interface(soc.user_spi_0, "user_spi0")
        _connect_interface(soc.user_spi_1, "user_spi1")
        _connect_interface(soc.user_spi_2, "user_spi2")

        _connect_interface(soc.i2c_0, "i2c0")
        _connect_interface(soc.i2c_1, "i2c1")

        for pwm_idx in range(10):
            _connect_interface(getattr(soc, f"motor_pwm{pwm_idx}"), f"motor_pwm{pwm_idx}")

        for ao_idx in range(6):
            m.d.comb += platform.request(f"pdm_ao_{ao_idx}").o.eq(getattr(soc, f"pdm_ao_{ao_idx}"))

        for gpio_bank in range(2):
            gpio = getattr(soc, f"gpio_{gpio_bank}")
            for i in range(8):
                platform_pin = platform.request(f"gpio{gpio_bank}_{i}")
                m.d.comb += [
                    platform_pin.o.eq(gpio.o[i]),
                    platform_pin.oe.eq(gpio.oe[i]),
                    gpio.i[i].eq(platform_pin.i),
                ]

        _connect_interface(soc.uart_0, "uart0")
        _connect_interface(soc.uart_1, "uart1")

        _connect_interface(soc.cpu_jtag, "cpu_jtag")

        return m

