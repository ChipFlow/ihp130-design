from pyuvm import *
import pyuvm
import cocotb
from cocotb.triggers import RisingEdge, ClockCycles, FallingEdge, Combine
from cocotb.queue import QueueEmpty, Queue
import enum
import logging

from pyuvm import utility_classes

logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

@enum.unique
class Ops(enum.IntEnum):
    """Legal ops for the TinyALU"""
    WR = 1
    RD = 2


def get_int(signal):
    try:
        sig = int(signal.value)
    except ValueError:
        sig = 0
    return sig

class SpiBfm(metaclass=utility_classes.Singleton):
    def __init__(self):
        self.dut = cocotb.top
        self.driver_queue = Queue(maxsize=1)
        self.cmd_mon_queue = Queue(maxsize=0)
        self.result_mon_queue = Queue(maxsize=0)

    async def send_op(self, addr, data, op):
        command_tuple = (addr, data, op)
        await self.driver_queue.put(command_tuple)

    async def reset(self):
        await FallingEdge(self.dut.clk_test)
        self.dut.rst.value = 1
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        self.dut.miso.value = 0
        await FallingEdge(self.dut.clk_test)
        self.dut.rst.value = 0
        await FallingEdge(self.dut.clk_test)
        uvm_root().logger.info(f"RESET DONE")

    async def driver_bfm(self):
        uvm_root().logger.info(f"START BFM")
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        uvm_root().logger.info(f"START BFM POST")
        while True:
            await FallingEdge(self.dut.clk_test)
            uvm_root().logger.info(f"START before done")
            done = get_int(self.dut.done)
            uvm_root().logger.info(f"START done {done}")
            if done == 0:
                try:
                    (addr, data, op) = self.driver_queue.get_nowait()
                    uvm_root().logger.info(f"QUEUE NOT EMPTY")
                    if op == Ops.WR:
                        uvm_root().logger.info(f"WRITE OP START addr: {addr} data: {data}")
                        self.dut.wstb.value = 1
                        self.dut.addr.value = addr
                        self.dut.wdata.value = data
                        await FallingEdge(self.dut.clk_test)
                        self.dut.wstb.value = 0
                        uvm_root().logger.info(f"WRITE OP END addr: {addr} data: {data}")
                    elif op == Ops.RD:
                        uvm_root().logger.info(f"READ OP START")
                        self.dut.rstb.value = 1
                        await FallingEdge(self.dut.clk_test)
                        self.dut.rstb.value = 0
                    else:
                        uvm_root().logger.error(f"NOT VALID OP!!!")
                except QueueEmpty:
                    uvm_root().logger.info(f"QUEUE EMPTY")
                    pass

    def start_bfm(self):
        cocotb.start_soon(self.driver_bfm())
