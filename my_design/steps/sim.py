import os
from pathlib import Path

from amaranth import *
from amaranth.lib import io
from amaranth.back import rtlil

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from chipflow_lib.steps.sim import SimStep

from ..design import MySoC
from ..sim import doit_build
from ..ips.ports import PortGroup


__all__ = ["MySimStep"]


class _SimTop(Elaboratable):
    def __init__(self):
        self.ports = PortGroup()

        self.ports.qspi = PortGroup()
        self.ports.qspi.sck = io.SimulationPort("o",  1, name="qspi_sck")
        self.ports.qspi.io  = io.SimulationPort("io", 4, name="qspi_io")
        self.ports.qspi.cs  = io.SimulationPort("o",  1, name="qspi_cs")

        self.ports.i2c = PortGroup()
        self.ports.i2c.scl = io.SimulationPort("io", 1, name="i2c_scl")
        self.ports.i2c.sda = io.SimulationPort("io", 1, name="i2c_sda")

        self.ports.uart = PortGroup()
        self.ports.uart.rx = io.SimulationPort("i", 1, name="uart_rx")
        self.ports.uart.tx = io.SimulationPort("o", 1, name="uart_tx")

    def elaborate(self, platform):
        m = Module()
        m.submodules.soc = soc = MySoC(self.ports)
        return m


class _SimPlatform:
    def __init__(self):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()

    def add_file(self, filename, content):
        if not isinstance(content, (str, bytes)):
            content = content.read()
        self.extra_files[filename] = content

    def build(self, e):
        Path(self.build_dir).mkdir(parents=True, exist_ok=True)

        ports = [
            e.ports.qspi.sck.o, e.ports.qspi.sck.oe,
            e.ports.qspi.io.o, e.ports.qspi.io.oe, e.ports.qspi.io.i,
            e.ports.qspi.cs.o, e.ports.qspi.cs.oe,

            e.ports.i2c.scl.o, e.ports.i2c.scl.oe, e.ports.i2c.scl.i,
            e.ports.i2c.sda.o, e.ports.i2c.sda.oe, e.ports.i2c.sda.i,

            e.ports.uart.rx.i,
            e.ports.uart.tx.o,
        ]
        output = rtlil.convert(e, name="sim_top", ports=ports, platform=self)

        top_rtlil = Path(self.build_dir) / "sim_soc.il"
        with open(top_rtlil, "w") as rtlil_file:
            rtlil_file.write(output)
        top_ys = Path(self.build_dir) / "sim_soc.ys"
        with open(top_ys, "w") as yosys_file:
            for extra_filename, extra_content in self.extra_files.items():
                extra_path = Path(self.build_dir) / extra_filename
                with open(extra_path, "w") as extra_file:
                    extra_file.write(extra_content)
                if extra_filename.endswith(".il"):
                    print(f"read_rtlil {extra_path}", file=yosys_file)
                else:
                    # FIXME: use -defer (workaround for YosysHQ/yosys#4059)
                    print(f"read_verilog {extra_path}", file=yosys_file)
            print("read_ilang sim_soc.il", file=yosys_file)
            print("hierarchy -top sim_top", file=yosys_file)
            print("write_cxxrtl -header sim_soc.cc", file=yosys_file)


class MySimStep(SimStep):
    def __init__(self, config):
        platform = _SimPlatform()
        super().__init__(config, platform)

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        rtlil_subparser = action_argument.add_parser(
            "build-rtlil", help="(internal) Build the RTLIL of the design.")
        build_subparser = action_argument.add_parser(
            "build", help="Build the CXXRTL simulation.")
        run_subparser = action_argument.add_parser(
            "run", help="Run the CXXRTL simulation.")

    def run_cli(self, args):
        if args.action == "build-rtlil":
            self.build_rtlil()
        if args.action == "build":
            self.build()
        if args.action == "run":
            self.run()

    def build_rtlil(self):
        self.platform.build(_SimTop())

    def build(self):
        DoitMain(ModuleTaskLoader(doit_build)).run(["build_sim"])

    def run(self):
        DoitMain(ModuleTaskLoader(doit_build)).run(["run_sim"])
