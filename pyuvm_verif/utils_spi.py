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
    async def get_result(self):
        result = await self.result_mon_queue.get()
        return result
    async def result_mon_bfm(self):
        prev_done = 0
        while True:
            await FallingEdge(self.dut.clk_test)
            done = get_int(self.dut.done)
            if prev_done == 0 and done == 1:
                result = get_int(self.dut.done)
                self.result_mon_queue.put_nowait(done)
            prev_done = done

    async def reset(self):
        await FallingEdge(self.dut.clk_test)
        self.dut.rst.value = 1
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        self.dut.miso.value = 1
        await FallingEdge(self.dut.clk_test)
        await FallingEdge(self.dut.clk_test)
        await FallingEdge(self.dut.clk_test)
        self.dut.rst.value = 0
        await FallingEdge(self.dut.clk_test)
        uvm_root().logger.info(f"RESET DONE")

    async def driver_bfm(self):
        uvm_root().logger.info(f"START DRIVER BFM")
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        while True:
            await FallingEdge(self.dut.clk_test)
            uvm_root().logger.info(f"START before done")
            done = get_int(self.dut.done)
            uvm_root().logger.info(f"START done value:{done}")
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
                        uvm_root().logger.info(f"READ OP START addr: {addr} data(not important): {data}")
                        self.dut.rstb.value = 1
                        self.dut.addr.value = addr
                        await FallingEdge(self.dut.clk_test)
                        self.dut.rstb.value = 0
                        uvm_root().logger.info(f"READ OP END addr: {addr} data(not important): {data}")
                    else:
                         uvm_root().logger.error(f"NOT VALID OP!!!")
                except QueueEmpty:
                    uvm_root().logger.info(f"QUEUE EMPTY")
                    pass
            else:
                uvm_root().logger.info(f"DONE: {done}")
        uvm_root().logger.info(f"FINISH BFM DRIVER")
    def start_bfm(self):
        cocotb.start_soon(self.driver_bfm())
        cocotb.start_soon(self.result_mon_bfm())
