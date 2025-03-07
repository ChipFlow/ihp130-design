from pyuvm import *
import pyuvm
import random
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

class SpiBfm(metaclass=utility_classes.Singleton):
    def __init__(self):
        self.dut = cocotb.top
        self.driver_queue = Queue(maxsize=1)
        self.cmd_mon_queue = Queue(maxsize=0)
        self.result_mon_queue = Queue(maxsize=0)
        self.data_cipo = 0
        self.clk_div = 0
        self.width_num = 0
        self.width_en = 0
    def reverse_bits(self, number, bit_size):
        binary = bin(number)
        reverse = binary[-1:1:-1]
        reverse = reverse + (bit_size - len(reverse)) * '0'
        reverse = int(reverse, 2)
        return reverse

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
        global wid_end
        while True:
            await RisingEdge(self.dut.clk_test)
            wstb = get_int(self.dut.wstb)
            rstb = get_int(self.dut.rstb)
            addr = get_int(self.dut.addr)
            data = get_int(self.dut.wdata)
            if wstb == 1 or rstb == 1:
                if wstb == 1:
                    op = 1
                    if addr == 0:
                        self.sck_start  = (data & 0x01)
                        self.sck_edge   = (data & 0x02)
                        width_bin = bin(data)[2:].zfill(8)
                        self.width_num = int(width_bin[:5],2)
                        uvm_root().logger.info(f"SCK EDGE: {self.sck_edge}")
                        uvm_root().logger.info(f"SCK START: {self.sck_start}")
                        uvm_root().logger.info(f"!!!WIDTH NUMBER: {self.width_num}!!!")
                        wid_end = self.width_num + 10
                    if addr == 4:
                        self.clk_div = get_int(self.dut.wdata)
                        uvm_root().logger.info(f"CLK DIV: {self.clk_div}")
                    if addr == 11:
                        self.width_en = 1
                        for i in range(0,wid_end):
                            await FallingEdge(self.dut.clk_test)
                        self.width_en = 0
                else:
                    op = 2
                cmd_tuple = (addr,
                             data,
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
                addr = get_int(self.dut.addr)
                if addr in (0,4):
                    self.result_mon_queue.put_nowait(result)
                    uvm_root().logger.info(f"PUT WR RESULT {hex(result)}")
                if addr == 11:
                    write_result = 0
                    for i in range(0,8):
                        if self.sck_start == 1 and self.sck_edge == 2:
                            await FallingEdge(self.dut.sck)
                        elif self.sck_start == 0 and self.sck_edge == 2:
                            await RisingEdge(self.dut.sck)
                        elif self.sck_start == 1 and self.sck_edge == 0:
                            await RisingEdge(self.dut.sck)
                        else:
                            await FallingEdge(self.dut.sck)
                        """uvm_root().logger.info(f"I: {i} MOSI: {get_int(self.dut.copi)}")"""
                        write_result = write_result + get_int(self.dut.copi)*(2**i)
                    for i in range(0, 100):
                        await RisingEdge(self.dut.clk_test)
                    final_result = self.reverse_bits(write_result,8)
                    self.result_mon_queue.put_nowait(final_result)
                    uvm_root().logger.info(f"PUT WR DATA RESULT {hex(final_result)}")
            if rstb == 1:
                await FallingEdge(self.dut.clk_test)
                result = get_int(self.dut.rdata)
                self.result_mon_queue.put_nowait(result)
                uvm_root().logger.info(f"PUT RD RESULT {hex(result)}")

    async def reset(self):
        await FallingEdge(self.dut.clk_test)
        self.dut.rst.value = 1
        self.dut.addr.value = 0
        self.dut.wdata.value = 0
        self.dut.rstb.value = 0
        self.dut.wstb.value = 0
        self.dut.cipo.value = 0
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
                    uvm_root().logger.info(f"WRITE OP START addr: {hex(addr)} data: {hex(data)}")
                    self.dut.wstb.value = 1
                    self.dut.addr.value = addr
                    self.dut.wdata.value = data
                    data_wr_cipo = bin(data)[2:]
                    data_wr_rd = (8 - len(data_wr_cipo)) * '0' + data_wr_cipo
                    self.data_cipo = int(data_wr_rd,2)
                    binary_cipo = bin(self.data_cipo)[2:]
                    uvm_root().logger.info(f"DATA EXTEND: {data_wr_rd} DATA MISO: {self.data_cipo } BINARY MISO: {binary_cipo}")
                    await FallingEdge(self.dut.clk_test)
                    self.dut.wstb.value = 0
                    await RisingEdge(self.dut.clk_test)

                    for bit_cipo in data_wr_rd:
                        self.dut.cipo.value = int(bit_cipo)
                        """uvm_root().logger.info(f"DATA MISO BIT: {int(bit_cipo)}")"""
                        await RisingEdge(self.dut.clk_test)
                        await RisingEdge(self.dut.clk_test)

                    """uvm_root().logger.info(f"WRITE OP END addr: {hex(addr)} data: {hex(data)}")"""
                elif op == Ops.RD:
                    uvm_root().logger.info(f"READ OP START addr: {hex(addr)}")
                    self.dut.rstb.value = 1
                    self.dut.addr.value = addr
                    await FallingEdge(self.dut.clk_test)
                    self.dut.rstb.value = 0
                    """uvm_root().logger.info(f"READ OP END addr: {hex(addr)}")"""
                else:
                     uvm_root().logger.error(f"NOT VALID OP!!!")
            except QueueEmpty:
                """uvm_root().logger.info(f"QUEUE EMPTY")"""
                pass

        uvm_root().logger.info(f"FINISH BFM DRIVER")
    async def clkdiv_assert_bfm(self):
        while True:
            await RisingEdge(self.dut.clk_test)
            wstb = get_int(self.dut.wstb)
            if wstb == 1:
                await FallingEdge(self.dut.clk_test)
                addr = get_int(self.dut.addr)
                if addr == 11:
                    await RisingEdge(self.dut.sck)
                    clk_div_measr = 0
                    while self.dut.sck == 1:
                        await RisingEdge(self.dut.clk_test)
                        clk_div_measr = clk_div_measr + 1
                    uvm_root().logger.info(f"CLK DIVIDER MEASURED: {clk_div_measr}")
                    assert self.clk_div == (clk_div_measr-2), f"CLK DIV {self.clk_div} NOT EQUAL TO CLK DIV MEASURED {clk_div_measr-2}"

    async def width_assert_bfm(self):
        while True:
            await RisingEdge(self.dut.clk_test)
            wstb = get_int(self.dut.wstb)
            if wstb == 1:
                await FallingEdge(self.dut.clk_test)
                addr = get_int(self.dut.addr)
                if addr == 11:
                    width_measer = 0
                    while self.width_en == 1:
                        await RisingEdge(self.dut.sck)
                        width_measer = width_measer + 1
                    uvm_root().logger.info(f"!!!! WIDTH OF SPI MEASURED: {width_measer} !!!!")
                    if self.clk_div == 0:
                        assert self.width_num == (
                            width_measer-1), f"WIDTH {self.width_num} NOT EQUAL TO WIDTH MEASURED {width_measer-1}"

    def start_bfm(self):
        cocotb.start_soon(self.driver_bfm())
        cocotb.start_soon(self.cmd_mon_bfm())
        cocotb.start_soon(self.result_mon_bfm())
        cocotb.start_soon(self.clkdiv_assert_bfm())
        cocotb.start_soon(self.width_assert_bfm())