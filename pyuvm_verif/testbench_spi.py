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
        if not hasattr(SpiSeqItem,'data'):
            cmd_tr.randomize_data()
        await self.finish_item(cmd_tr)

class SpiWR4Seq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0x4, 0x0, Ops.WR)
        await self.start_item(cmd_tr)
        cmd_tr.randomize_data()
        await self.finish_item(cmd_tr)

class SpiSeq(uvm_sequence):
    def __init__(self, name, address, data, op):
        super().__init__(name)
        self.addr = address
        self.data = data
        self.op = Ops(op)
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", address=self.addr, data=self.data, op=self.op)
        await self.start_item(cmd_tr)
        await self.finish_item(cmd_tr)

class SpiRD0Seq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0x0, None, Ops.RD)
        await self.start_item(cmd_tr)
        cmd_tr.randomize_data()
        await self.finish_item(cmd_tr)

class SpiRD4Seq(uvm_sequence):
    async def body(self):
        cmd_tr = SpiSeqItem("cmd_tr", 0x4, None, Ops.RD)
        await self.start_item(cmd_tr)
        cmd_tr.randomize_data()
        await self.finish_item(cmd_tr)

class TestSeq(uvm_sequence):
    async def body(self):
        uvm_root().logger.info(f"TEST: SINGLE WRITE TO 0x0 ADDRESS")
        seqr = ConfigDB().get(None, "", "SEQR")
        wrtest = SpiWR0Seq("wrtest")
        await wrtest.start(seqr)

class TestRegSeq(uvm_sequence):
    async def body(self):
        uvm_root().logger.info(f"TEST: REGISTER WRITE AND READ TO 0x0 and 0x4 ADDRESSES")
        seqr = ConfigDB().get(None, "", "SEQR")
        for i in range(100):
            spiwr0 = SpiWR0Seq("spiwr0")
            spird0 = SpiRD0Seq("spird0")
            await spiwr0.start(seqr)
            await spird0.start(seqr)

        for i in range(100):
            spiwr4 = SpiWR4Seq("spiwr4")
            spird4 = SpiRD4Seq("spird4")
            await spiwr4.start(seqr)
            await spird4.start(seqr)

class TestWrSeq(uvm_sequence):
    async def body(self):
        uvm_root().logger.info(f"TEST: WRITE TO 0xB ADDRESS, COLLECT AND COMPARE WRITTEN VALUES")
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwr0 = SpiSeq("spiwr0",0x0,0x3f,1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3e, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x87, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x86, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3d, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(0):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3c, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        spiwr2 = SpiSeq("spiwr2", 0xb, 0x45, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        await spiwr2.start(seqr)
        for i in range(0):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)

class TestRdSeq(uvm_sequence):
    async def body(self):
        uvm_root().logger.info(f"TEST: WRITE TO 0xB ADDRESS, READ TO 0xC ADDRESS AND COMPARE VALUES")
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwr0 = SpiSeq("spiwr0",0x0,0x3f,1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)
            spird = SpiSeq("spird", 0xc, data3,  2)
            await spird.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3e, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)
            spird = SpiSeq("spird", 0xc, data3, 2)
            await spird.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3d, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)
            spird = SpiSeq("spird", 0xc, data3, 2)
            await spird.start(seqr)

        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3c, 1)
        spiwr1 = SpiSeq("spiwr1", 0x4, 0x0, 1)
        await spiwr0.start(seqr)
        await spiwr1.start(seqr)
        for i in range(1):
            data3 = random.randint(0, 255)
            spiwr3 = SpiSeq("spiwr3", 0xb, data3, 1)
            await spiwr3.start(seqr)
            spird = SpiSeq("spird", 0xc, data3, 2)
            await spird.start(seqr)

class TestClkdivSeq(uvm_sequence):
    async def body(self):
        uvm_root().logger.info(f"TEST: CLOCK DIVIDER")
        seqr = ConfigDB().get(None, "", "SEQR")
        spiwr0 = SpiSeq("spiwr0", 0x0, 0x3f, 1)
        await spiwr0.start(seqr)
        data1 = random.randint(0, 255)
        spiwr1 = SpiSeq("spiwr1", 0x4, data1, 1)
        await spiwr1.start(seqr)
        data2 = random.randint(0, 255)
        spiwr2 = SpiSeq("spiwr2", 0xb, data2, 1)
        await spiwr2.start(seqr)

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
            uvm_root().logger.info(f"RUN PHASE addr: {hex(cmd.addr)} data: {hex(cmd.data)} op: {cmd.op}")
            result = await self.bfm.get_result()
            self.ap.write(result)
            uvm_root().logger.info(f"GET RESULT: {hex(result)}")
            self.seq_item_port.item_done()

class Monitor(uvm_component):
    def __init__(self, name, parent, method_name):
        super().__init__(name, parent)
        self.method_name = method_name

    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)
        self.bfm = SpiBfm()
        self.get_method = getattr(self.bfm, self.method_name)

    async def run_phase(self):
        while True:
            datum = await self.get_method()
            self.logger.debug(f"MONITORED {datum}")
            self.ap.write(datum)

class Scoreboard(uvm_component):

    def build_phase(self):
        self.cmd_fifo = uvm_tlm_analysis_fifo("cmd_fifo", self)
        self.result_fifo = uvm_tlm_analysis_fifo("result_fifo", self)

        self.cmd_get_port = uvm_get_port("cmd_get_port", self)
        self.result_get_port = uvm_get_port("result_get_port", self)

        self.cmd_export = self.cmd_fifo.analysis_export
        self.result_export = self.result_fifo.analysis_export

    def connect_phase(self):
        self.cmd_get_port.connect(self.cmd_fifo.get_export)
        self.result_get_port.connect(self.result_fifo.get_export)

    def check_phase(self):
        self.logger.info(f"CHECK SCB PHASE")
        passed = True
        while True:
            cmd_success, cmd = self.cmd_get_port.try_get()
            if not cmd_success:
                break
            else:
                result_success, data_read = self.result_get_port.try_get()
                if not result_success:
                    self.logger.critical(f"result {data_read} had no command")
                else:
                    (addr, data, op_numb) = cmd
                    if op_numb == 1 and addr in(0,4):
                        predicted_data = data_read
                        self.logger.info(f"WDATA  {hex(predicted_data)} ")
                    if op_numb == 1 and (addr == 11 or addr == 12):
                        predicted_data = data
                        self.logger.info(f"WDATA ADDR B {hex(predicted_data)} ")
                    if (op_numb == 2 and addr in(0,4,12)) or (op_numb == 1 and addr == 11):
                        if predicted_data == data_read:
                            self.logger.info(f"PASSED: {hex(predicted_data)} ="
                                             f" {hex(data_read)}")
                        else:
                            self.logger.error(f"FAILED: "
                                              f"ACTUAL:   {hex(data_read)} "
                                              f"EXPECTED: {hex(predicted_data)}")
                            passed = False
        assert passed

class SpiEnv(uvm_env):
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        ConfigDB().set(None, "*", "SEQR", self.seqr)
        self.driver = Driver.create("driver", self)
        self.cmd_mon = Monitor("cmd_mon", self, "get_cmd")
        self.scoreboard = Scoreboard("scoreboard", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)
        self.cmd_mon.ap.connect(self.scoreboard.cmd_export)
        self.driver.ap.connect(self.scoreboard.result_export)

@pyuvm.test()
class BasicTest(uvm_test):
    def build_phase(self):
        self.env = SpiEnv("env", self)

    def end_of_elaboration_phase(self):
        self.test_all = TestSeq.create("test_all")

    async def run_phase(self):
        self.raise_objection()
        uvm_root().logger.info(f"START TEST")
        await self.test_all.start()
        uvm_root().logger.info(f"END TEST")
        self.drop_objection()

@pyuvm.test()
class RegTest(BasicTest):

    def build_phase(self):
        uvm_factory().set_type_override_by_type(TestSeq, TestRegSeq)
        super().build_phase()


@pyuvm.test()
class WriteTest(BasicTest):

    def build_phase(self):
        uvm_factory().set_type_override_by_type(TestSeq, TestWrSeq)
        super().build_phase()

@pyuvm.test()
class ReadTest(BasicTest):

    def build_phase(self):
        uvm_factory().set_type_override_by_type(TestSeq, TestRdSeq)
        super().build_phase()

@pyuvm.test()
class ClkdividerTest(BasicTest):

    def build_phase(self):
        uvm_factory().set_type_override_by_type(TestSeq, TestClkdivSeq)
        super().build_phase()