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

    async def get_cmd(self):
        cmd = await self.cmd_mon_queue.get()
        return cmd

    async def get_result(self):
        result = await self.result_mon_queue.get()
        return result

    async def reset(self):
        await FallingEdge(self.dut.clk_tst)
        self.dut.rst.value = 1
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        self.dut.miso = 0
        await FallingEdge(self.dut.clk_tst)
        self.dut.rst.value = 0
        await FallingEdge(self.dut.clk_tst)

    async def driver_bfm(self):
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        while True:
            await FallingEdge(self.dut.clk_tst)
            try:
                (addr, data, op) = self.driver_queue.get_nowait()
                self.dut.addr.value = addr
                self.dut.wdata.value = data
                if op == Ops.WR:
                    uvm_root().logger.info(f"WRITE OP START addr: {addr} data: {data}")
                    self.dut.wstb.value = 1
                    uvm_root().logger.info(f"WRITE before falling edge")
                    await FallingEdge(self.dut.clk_tst)
                    self.dut.wstb.value = 0
                    uvm_root().logger.info(f"WRITE after falling edge")
                elif op == Ops.RD:
                    uvm_root().logger.info(f"READ OP START")
                    self.dut.rstb.value = 1
                    await FallingEdge(self.dut.clk_tst)
                    self.dut.rstb.value = 0
                else:
                    uvm_root().logger.error(f"NOT VALID OP!!!")
            except QueueEmpty:
                uvm_root().logger.info(f"EMPTY QUEUE")
                await ClockCycles(self.dut.clk_tst,30)
                break

    def start_bfm(self):
        cocotb.start_soon(self.driver_bfm())
