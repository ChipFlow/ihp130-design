from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out, flipped, connect
from amaranth.utils import exact_log2

from amaranth_orchard.memory.spimemio import SPIMemIO, QSPIPins
from amaranth_soc import csr, wishbone

# QSPI flash module Verilog export so it can be verified with pyuvm/verilator

# TODO: we wouldn't need this wrapper if SPIMemIO had flash as part of its signature
class SPIMemIOWrapper(wiring.Component):
    def __init__(self):
        super().__init__({
            "flash": Out(QSPIPins.Signature()),
            "ctrl_bus": In(csr.Signature(addr_width=exact_log2(4), data_width=8)),
            "data_bus": In(wishbone.Signature(addr_width=exact_log2(4*1024*1024), data_width=32,
                                              granularity=8)),
        })
    def elaborate(self, platform):
        m = Module()
        m.submodules.memio = memio = SPIMemIO(flash=self.flash)
        wiring.connect(m, flipped(self.ctrl_bus), memio.ctrl_bus)
        wiring.connect(m, flipped(self.data_bus), memio.data_bus)
        return m

if __name__ == '__main__':
    from amaranth.back import verilog
    from pathlib import Path
    spi = SPIMemIOWrapper()
    Path("build/export/ips").mkdir(parents=True, exist_ok=True)
    with open("build/export/ips/spimemio_ip.v", "w") as f:
        f.write(verilog.convert(spi, name="spimemio_ip"))
