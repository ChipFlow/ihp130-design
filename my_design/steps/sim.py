from chipflow_lib.steps.sim import SimStep
from chipflow_lib.platforms.sim import SimPlatform

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import connect, flipped

from ..design import MySoC
from ..sim import doit_build

class SocWrapper(wiring.Component):
    def __init__(self):
        super().__init__({})
    def elaborate(self, platform):
        m = Module()
        m.submodules.soc = soc = MySoC()

        m.submodules.clock_reset_provider = platform.providers.ClockResetProvider()

        m.submodules.spiflash_provider = spiflash_provider = platform.providers.QSPIFlashProvider()
        connect(m, flipped(spiflash_provider.pins), soc.flash)

        m.submodules.led_gpio_provider = led_gpio_provider = platform.providers.LEDGPIOProvider()
        connect(m, flipped(led_gpio_provider.pins), soc.gpio_0)

        m.submodules.uart_provider = uart_provider = platform.providers.UARTProvider()
        connect(m, flipped(uart_provider.pins), soc.uart_0)

        return m

class MySimStep(SimStep):
    doit_build_module = doit_build

    def __init__(self, config):
        platform = SimPlatform()

        super().__init__(config, platform)

    def build(self):
        my_design = SocWrapper()

        self.platform.build(my_design)
        self.doit_build()
