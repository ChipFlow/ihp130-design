from amaranth import *
from amaranth.sim import Simulator, Tick

from pdm import PDMPeripheral
import unittest

class TestPdmPeripheral(unittest.TestCase):

    REG_OUTVAL = 0x00
    REG_CONF = 0x04


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

    def test_pdm_ao(self):
        dut = PDMPeripheral(bitwidth=10)
        def testbench():
            yield from self._write_reg(dut, self.REG_OUTVAL, 0xFF, 4)
            yield Tick()
            yield from self._write_reg(dut, self.REG_CONF, 0x1, 1)
            for i in range(6): yield Tick()
            self.assertEqual((yield dut.pdm.o), 1) # assert two cycles of logic '1' (4us)
            yield Tick()
            self.assertEqual((yield dut.pdm.o), 1)
            yield Tick()
            self.assertEqual((yield dut.pdm.o), 0) # assert 6 cycles of logic '0' (12us)
            for i in range(5): yield Tick()
            self.assertEqual((yield dut.pdm.o), 0)
            yield Tick()
            self.assertEqual((yield dut.pdm.o), 1) # assert start of the next pulse
            for i in range(50): yield Tick()
        sim = Simulator(dut)
        sim.add_clock(2e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd("pdm_ao_test.vcd", "pdm_ao_test.gtkw"):
            sim.run()

    def test_conf(self):
        dut = PDMPeripheral(bitwidth=10)
        def testbench():
            yield from self._write_reg(dut, self.REG_OUTVAL, 0xFF, 4)
            yield Tick()
            yield from self._write_reg(dut, self.REG_CONF, 0x1, 1)
            for i in range(6): yield Tick()
            self.assertEqual((yield dut.pdm.o), 1)
            yield from self._write_reg(dut, self.REG_CONF, 0x0, 1)
            yield Tick()
            self.assertEqual((yield dut.pdm.o), 0)
            for i in range(50): yield Tick()
        sim = Simulator(dut)
        sim.add_clock(2e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd("pdm_conf_test.vcd", "pdm_conf_test.gtkw"):
            sim.run()

if __name__ == "__main__":
    unittest.main()

