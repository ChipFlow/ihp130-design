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
        cmd_tr = SpiSeqItem("cmd_tr", 0x0, 0x3c, Ops.WR)
        await self.start_item(cmd_tr)
        """cmd_tr.randomize_data()"""
        await self.finish_item(cmd_tr)

class SpiWR4Seq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0x4, 0x0, Ops.WR)
        await self.start_item(cmd_tr)
        """cmd_tr.randomize_data()"""
        await self.finish_item(cmd_tr)

class SpiWRSeq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0xb, 0xab, Ops.WR)
        await self.start_item(cmd_tr)
        """cmd_tr.randomize_data()"""
        await self.finish_item(cmd_tr)

class SpiRDSeq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0xc, 0xaa, Ops.RD)
        await self.start_item(cmd_tr)
        """cmd_tr.randomize_data()"""
        await self.finish_item(cmd_tr)

class TestSeq(uvm_sequence):
    async def body(self):
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwrtest = SpiWR0Seq("spiwrtest")
        await spiwrtest.start(seqr)

class TestWrSeq(uvm_sequence):
    async def body(self):
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwr0 = SpiWR0Seq("spiwr0")
        spiwr4 = SpiWR4Seq("spiwr4")
        spiwr = SpiWRSeq("spiwr")
        spird = SpiRDSeq("spird")
        await spiwr0.start(seqr)
        await spiwr4.start(seqr)
        await spiwr.start(seqr)
        await spird.start(seqr)

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
        uvm_root().logger.info(f"LAUNCH")
        while True:
            cmd = await self.seq_item_port.get_next_item()
            await self.bfm.send_op(cmd.addr, cmd.data, cmd.op)
            uvm_root().logger.info(f"RUN PHASE addr: {cmd.addr} data: {cmd.data} op: {cmd.op}")
            result = await self.bfm.get_result()
            self.seq_item_port.item_done()
            uvm_root().logger.info(f"RUN PHASE LAUNCH DONE")
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
        uvm_root().logger.info(f"BUILD ENV")
        self.env = SpiEnv("env", self)

    def end_of_elaboration_phase(self):
        uvm_root().logger.info(f"CREATE TestSeq")
        self.test_all = TestSeq.create("test_all")

    async def run_phase(self):
        self.raise_objection()
        uvm_root().logger.info(f"START TEST")
        await self.test_all.start()
        uvm_root().logger.info(f"END TEST")
        self.drop_objection()

@pyuvm.test()
class WrDataTest(BasicTest):

    def build_phase(self):
        uvm_factory().set_type_override_by_type(TestSeq, TestWrSeq)
        super().build_phase()