from amaranth_boards.ulx3s import ULX3S_85F_Platform
from chipflow_lib.steps.board import BoardStep
from chipflow_lib.providers import board_ulx3s as board_ulx3s_providers

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import connect, flipped

from ..design import MySoC

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
        connect(m, flipped(led_gpio_provider.pins), soc.led_gpio)

        m.submodules.uart_provider = uart_provider = platform.providers.UARTProvider()
        connect(m, flipped(uart_provider.pins), soc.uart)

        return m

class MyBoardStep(BoardStep):
    def __init__(self, config):

        platform = ULX3S_85F_Platform()
        platform.providers = board_ulx3s_providers

        super().__init__(config, platform)

    def build(self):
        my_design = SocWrapper()

        self.platform.build(my_design, do_program=False)
