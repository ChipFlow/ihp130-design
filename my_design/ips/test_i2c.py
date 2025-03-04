from amaranth import *
from amaranth.sim import Simulator, Tick

from my_design.ips.i2c import I2CPeripheral
import unittest

class _I2CHarness(Elaboratable):
    def __init__(self):
        self.i2c = I2CPeripheral()
        self.sda = Signal()
        self.scl = Signal()
        self.sda_i = Signal(init=1)
        self.scl_i = Signal(init=1)
    def elaborate(self, platform):
        m = Module()
        m.submodules.i2c = self.i2c
        # Simulate the open-drain I2C bus
        m.d.comb += [
            self.sda.eq(~self.i2c.i2c_pins.sda.oe & self.sda_i),
            self.scl.eq(~self.i2c.i2c_pins.scl.oe & self.scl_i),

            self.i2c.i2c_pins.sda.i.eq(self.sda),
            self.i2c.i2c_pins.scl.i.eq(self.scl),
        ]
        return m

class TestI2CPeripheral(unittest.TestCase):

    REG_DIVIDER   = 0x00
    REG_ACTION    = 0x04
    REG_SEND_DATA = 0x08
    REG_RECEIVE_DATA = 0x0C
    REG_STATUS = 0x10

    def _write_reg(self, dut, reg, value, width=4):
        for i in range(width):
            yield dut.bus.addr.eq(reg + i)
            yield dut.bus.w_data.eq((value >> (8 * i)) & 0xFF)
            yield dut.bus.w_stb.eq(1)
            yield Tick()
        yield dut.bus.w_stb.eq(0)

    def _check_reg(self, dut, reg, value, width=4):
        result = 0
        for i in range(width):
            yield dut.bus.addr.eq(reg + i)
            yield dut.bus.r_stb.eq(1)
            yield Tick()
            result |= (yield dut.bus.r_data) << (8 * i)
        yield dut.bus.r_stb.eq(0)
        self.assertEqual(result, value)

    def test_start_stop(self):
        """Test I2C start and stop conditions"""
        dut = _I2CHarness()
        def testbench():
            yield from self._write_reg(dut.i2c, self.REG_DIVIDER, 1, 4)
            yield Tick()
            yield from self._write_reg(dut.i2c, self.REG_ACTION, 1<<1, 1) # START
            yield Tick()
            yield from self._check_reg(dut.i2c, self.REG_STATUS, 1, 1) # busy
            self.assertEqual((yield dut.sda), 1)
            self.assertEqual((yield dut.scl), 1)
            yield Tick()
            self.assertEqual((yield dut.sda), 0)
            self.assertEqual((yield dut.scl), 1)
            yield Tick()
            yield from self._check_reg(dut.i2c, self.REG_STATUS, 0, 1) # not busy
            yield from self._write_reg(dut.i2c, self.REG_ACTION, 1<<2, 1) # STOP
            for i in range(3): yield Tick()
            self.assertEqual((yield dut.sda), 1)
            self.assertEqual((yield dut.scl), 1)
            yield Tick()
            yield from self._check_reg(dut.i2c, self.REG_STATUS, 0, 1) # not busy

        sim = Simulator(dut)
        sim.add_clock(1e-5)
        sim.add_testbench(testbench)
        with sim.write_vcd("i2c_start_test.vcd", "i2c_start_test.gtkw"):
            sim.run()

    def test_write(self):
        dut = _I2CHarness()
        def testbench():
            yield from self._write_reg(dut.i2c, self.REG_DIVIDER, 1, 4)
            yield Tick()
            yield from self._write_reg(dut.i2c, self.REG_ACTION, 1<<1, 1) # START
            for i in range(10): yield Tick() # wait for START to be completed
            for data in (0xAB, 0x63):
                yield from self._write_reg(dut.i2c, self.REG_SEND_DATA, data, 1) # write
                for i in range(3): yield Tick()
                for bit in reversed(range(-1, 8)):
                    self.assertEqual((yield dut.scl), 0)
                    for i in range(4): yield Tick()
                    if bit == -1: # ack
                        yield (dut.sda_i.eq(0))
                    else:
                        self.assertEqual((yield dut.sda), (data >> bit) & 0x1)
                    for i in range(2): yield Tick()
                    self.assertEqual((yield dut.scl), 1)
                    for i in range(6): yield Tick()
                yield (dut.sda_i.eq(1)) # reset bus
                for i in range(20): yield Tick()
                yield from self._check_reg(dut.i2c, self.REG_STATUS, 2, 1) # not busy, acked
        sim = Simulator(dut)
        sim.add_clock(1e-5)
        sim.add_testbench(testbench)
        with sim.write_vcd("i2c_write_test.vcd", "i2c_write_test.gtkw"):
            sim.run()

    def test_read(self):
        dut = _I2CHarness()
        data = 0xA3
        def testbench():
            yield from self._write_reg(dut.i2c, self.REG_DIVIDER, 1, 4)
            yield Tick()
            yield from self._write_reg(dut.i2c, self.REG_ACTION, 1<<1, 1) # START
            for i in range(10): yield Tick() # wait for START to be completed
            yield from self._write_reg(dut.i2c, self.REG_ACTION, 1<<3, 1) # READ, ACK
            for i in range(3): yield Tick()
            for bit in reversed(range(-1, 8)):
                self.assertEqual((yield dut.scl), 0)
                for i in range(4): yield Tick()
                if bit == -1: # ack
                    self.assertEqual((yield dut.sda), 0)
                else:
                    yield (dut.sda_i.eq((data >> bit) & 0x1))
                for i in range(2): yield Tick()
                self.assertEqual((yield dut.scl), 1)
                for i in range(6): yield Tick()
                if bit == 0:
                    yield (dut.sda_i.eq(1)) # reset bus

            for i in range(20): yield Tick()
            yield from self._check_reg(dut.i2c, self.REG_STATUS, 0, 1) # not busy
            yield from self._check_reg(dut.i2c, self.REG_RECEIVE_DATA, data, 1) # data
        sim = Simulator(dut)
        sim.add_clock(1e-5)
        sim.add_testbench(testbench)
        with sim.write_vcd("i2c_read_test.vcd", "i2c_read_test.gtkw"):
            sim.run()

if __name__ == "__main__":
    unittest.main()

