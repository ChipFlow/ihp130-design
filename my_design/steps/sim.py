from chipflow_lib.steps.sim import SimStep

from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import connect, flipped
from amaranth.back import rtlil

from ..design import MySoC
from ..sim import doit_build

import os
from pathlib import Path

class SimPlatform:

    def __init__(self):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()

    def add_file(self, filename, content):
        if not isinstance(content, (str, bytes)):
            content = content.read()
        self.extra_files[filename] = content

    def build(self, e):
        Path(self.build_dir).mkdir(parents=True, exist_ok=True)

        output = rtlil.convert(e, name="sim_top", ports=None, platform=self)

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
            print("read_rtlil sim_soc.il", file=yosys_file)
            print("hierarchy -top sim_top", file=yosys_file)
            print("write_cxxrtl -header sim_soc.cc", file=yosys_file)


class MySimStep(SimStep):
    doit_build_module = doit_build

    def __init__(self, config):
        platform = SimPlatform()

        super().__init__(config, platform)

    def build(self):
        my_design = MySoC()

        self.platform.build(my_design)
        self.doit_build()
