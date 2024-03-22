from cocotb.triggers import Join, Combine
from pyuvm import *
import random
import cocotb
import pyuvm
import sys
from pathlib import Path
sys.path.append(str(Path("..").resolve()))
from utils_spi import SpiBfm,Ops

class SpiSeqItem(uvm_sequence_item):
    def __init__(self, name, address, data, op):
        super().__init__(name)
        self.addr = address
        self.data = data
        self.op = Ops(op)

    def randomize_data(self):
        self.data = random.randint(0, 255)

    def __eq__(self, other):
        same = self.data == other.data
        return same

    def __str__(self):
        return f"{self.get_name()} : ADDR: 0x{self.addr:02x} \
        OP: {self.op.name} ({self.op.value}) DATA: 0x{self.data:02x}"

class SpiWR0Seq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0x0, None, Ops.WR)
        await self.start_item(cmd_tr)
        cmd_tr.randomize_data()
        await self.finish_item(cmd_tr)

class TestSeq(uvm_sequence):
    async def body(self):
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwr0test = SpiWR0Seq("random")
        await spiwr0test.start(seqr)

class Driver(uvm_driver):
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)

    def start_of_simulation_phase(self):
        self.bfm = SpiBfm()

    async def launch_tb(self):
        await self.bfm.reset()
        self.bfm.start_bfm()

    async def run_phase(self):
        await self.launch_tb()
        while True:
            cmd = await self.seq_item_port.get_next_item()
            await self.bfm.send_op(cmd.addr, cmd.data, cmd.op)
            result = await self.bfm.get_result()
            self.ap.write(result)
            cmd.result = result
            self.seq_item_port.item_done()

class SpiEnv(uvm_env):
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        ConfigDB().set(None, "*", "SEQR", self.seqr)
        self.driver = Driver.create("driver", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)

@pyuvm.test()
class BasicTest(uvm_test):
    def build_phase(self):
        self.env = SpiEnv("env", self)

    def end_of_elaboration_phase(self):
        self.test_spi_wr = TestSeq.create("test_spi_wr")

    async def run_phase(self):
        self.raise_objection()
        await self.test_spi_wr.start()
        self.drop_objection()
