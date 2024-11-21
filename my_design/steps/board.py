import asyncio
import pathlib
import usb1

from amaranth import *

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from chipflow_lib.steps.board import BoardStep

from glasgow.platform.generic import GlasgowPlatformPort
from glasgow.platform.rev_c import GlasgowRevC123Platform
from glasgow.target.hardware import GlasgowBuildPlan
from glasgow.target.toolchain import find_toolchain

from ..design import MySoC
from ..board import doit_glasgow
from ..ips.ports import PortGroup


__all__ = ["GlasgowBoardStep"]


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


class GlasgowBoardStep(BoardStep):
    def __init__(self, config):
        platform = GlasgowRevC123Platform()
        super().__init__(config, platform)

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        build_subparser = action_argument.add_parser(
            "build-bitstream", help="Build the FPGA bitstream.")
        bitstream_subparser = action_argument.add_parser(
            "load-bitstream", help="Load the FPGA bitstream to the board.")
        software_subparser = action_argument.add_parser(
            "flash-software", help="Write the software to the board SPI flash.")

    def run_cli(self, args):
        if args.action == "build-bitstream":
            self.build_bitstream()
        if args.action == "load-bitstream":
            self.load_bitstream()
        if args.action == "flash-software":
            self.flash_software()

    def build_bitstream(self):
        plan = GlasgowBuildPlan(
            find_toolchain(),
            self.platform.prepare(_GlasgowTop(), nextpnr_opts="--timing-allow-fail"))
        plan.execute(build_dir="build/board", debug=True)

    def load_bitstream(self):
        DoitMain(ModuleTaskLoader(doit_glasgow)).run(["load_bitstream"])

    def flash_software(self):
        DoitMain(ModuleTaskLoader(doit_glasgow)).run(["flash_software"])
