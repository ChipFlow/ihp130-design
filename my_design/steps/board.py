from amaranth import *

from glasgow.platform.generic import GlasgowPlatformPort
from glasgow.platform.rev_c import GlasgowRevC123Platform

from chipflow_lib.steps.board import BoardStep

from ..design import MySoC
from ..ips.ports import PortGroup


__all__ = ["MyBoardStep"]


class _GlasgowTop(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        a_ports = [platform.request("port_a", n, dir={"io": "-", "oe": "-"}) for n in range(8)]
        b_ports = [platform.request("port_b", n, dir={"io": "-", "oe": "-"}) for n in range(2)]

        ports = PortGroup()

        ports.qspi = PortGroup()
        ports.qspi.sck = GlasgowPlatformPort(io=a_ports[6].io, oe=a_ports[6].oe)
        ports.qspi.io = (GlasgowPlatformPort(io=a_ports[5].io, oe=a_ports[5].oe) +
                         GlasgowPlatformPort(io=a_ports[4].io, oe=a_ports[4].oe) +
                         GlasgowPlatformPort(io=b_ports[0].io, oe=b_ports[0].oe) +
                         GlasgowPlatformPort(io=b_ports[1].io, oe=b_ports[1].oe))
        ports.qspi.cs  = GlasgowPlatformPort(io=a_ports[7].io, oe=a_ports[7].oe)

        ports.i2c = PortGroup()
        ports.i2c.scl = GlasgowPlatformPort(io=a_ports[2].io, oe=a_ports[2].oe)
        ports.i2c.sda = GlasgowPlatformPort(io=a_ports[3].io, oe=a_ports[3].oe)

        ports.uart = PortGroup()
        ports.uart.rx = GlasgowPlatformPort(io=a_ports[0].io, oe=a_ports[0].oe)
        ports.uart.tx = GlasgowPlatformPort(io=a_ports[1].io, oe=a_ports[1].oe)

        m.submodules.soc = soc = MySoC(ports)

        return m


class MyBoardStep(BoardStep):
    def __init__(self, config):
        platform = GlasgowRevC123Platform()
        super().__init__(config, platform)

    def build(self):
        self.platform.build(_GlasgowTop(), do_program=False)
