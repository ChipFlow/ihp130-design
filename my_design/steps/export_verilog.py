from amaranth.back import verilog
from ._chipflow_top import ChipflowTop

from os import path
from pathlib import Path

from chipflow_lib.platforms.silicon import SiliconPlatform

class ExportVerilogStep:
    """Export Verilog for a Verilator simulation"""

    def __init__(self, config):
        self.platform = SiliconPlatform(config)

    def _export_verilog(self, name, elab, export_dir):
        # Verilog export for Verilator verification

        self.platform.instantiate_ports()

        Path(export_dir).mkdir(parents=True, exist_ok=True)
        fragment = self.platform._prepare(elab, name)
        verilog_text, _ = verilog.convert_fragment(fragment, name)
        with open(path.join(export_dir, f"{name}.v"), "w") as f:
            f.write(verilog_text)
        for filename, content in self.platform._files.items():
            with open(path.join(export_dir, f"{path.basename(filename)}"), "wb") as f:
                f.write(content)

    def build_cli_parser(self, parser):
        parser.add_argument("--dir", default="build/export")

    def run_cli(self, args):
        self._export_verilog("testchip_top", ChipflowTop(), args.dir)
