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
    """Legal ops for the Spi"""
    WR = 1
    RD = 2

def get_int(signal):
    try:
        sig = int(signal.value)
    except ValueError:
        sig = 0
    return sig

def spi_prediction(addr, data, op):
    """Python model of the TinyALU"""
    assert isinstance(op, Ops), "The spi op must be of type Ops"
    if op == Ops.WR:
        result = data
    return result

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
    async def cmd_mon_bfm(self):
        prev_start = 0
        while True:
            await RisingEdge(self.dut.clk_test)
            wstb = get_int(self.dut.wstb)
            rstb = get_int(self.dut.rstb)
            if wstb == 1 or rstb == 1:
                if wstb == 1:
                    op = 1
                else:
                    op = 2
                cmd_tuple = (get_int(self.dut.addr),
                             get_int(self.dut.rdata),
                             op)
                self.cmd_mon_queue.put_nowait(cmd_tuple)
                uvm_root().logger.info(f"PUT CMD TUPLE {cmd_tuple}")
    async def result_mon_bfm(self):
        while True:
            await RisingEdge(self.dut.clk_test)
            wstb = get_int(self.dut.wstb)
            rstb = get_int(self.dut.rstb)
            if wstb == 1:
                await FallingEdge(self.dut.clk_test)
                result = get_int(self.dut.wdata)
                self.result_mon_queue.put_nowait(result)
                uvm_root().logger.info(f"PUT WR RESULT {result}")
            if rstb == 1:
                await FallingEdge(self.dut.clk_test)
                result = get_int(self.dut.rdata)
                self.result_mon_queue.put_nowait(result)
                uvm_root().logger.info(f"PUT RD RESULT {result}")

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

        uvm_root().logger.info(f"FINISH BFM DRIVER")
    def start_bfm(self):
        cocotb.start_soon(self.driver_bfm())
        cocotb.start_soon(self.cmd_mon_bfm())
        cocotb.start_soon(self.result_mon_bfm())