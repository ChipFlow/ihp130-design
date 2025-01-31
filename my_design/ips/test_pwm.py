from amaranth import *
from amaranth.sim import Simulator, Tick

from pwm import PWMPeripheral, PWMPins
import unittest

class TestPwmPeripheral(unittest.TestCase):
        
    REG_NUMR        = 0x00
    REG_DENOM       = 0x04
    REG_CONF        = 0x08
    REG_STOP_INT    = 0x0C
    REG_STATUS      = 0x10

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

    def test_pwm_o(self):
        dut = PWMPeripheral(name="dut", pins=PWMPins())
        def testbench():
            yield from self._write_reg(dut, self.REG_NUMR, 0x1F, 4)
            yield from self._write_reg(dut, self.REG_DENOM, 0xFF, 4)
            yield from self._write_reg(dut, self.REG_CONF, 0x03, 4)
            self.assertEqual((yield dut.pins.pwm.o), 1) # assert 32 cycles of logic '1'; 3 cycles go into writing conf register
            for i in range(29): yield Tick()
            self.assertEqual((yield dut.pins.pwm.o), 1)
            yield Tick()
            self.assertEqual((yield dut.pins.pwm.o), 0) # assert 224 cylces of logic '0'
            for i in range(223): yield Tick()
            self.assertEqual((yield dut.pins.pwm.o), 0)
            yield Tick()
            self.assertEqual((yield dut.pins.pwm.o), 1) # assert start of the next pulse
            for i in range(1000): yield Tick()
        sim = Simulator(dut)
        sim.add_clock(2e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd("pwm_o_test.vcd", "pwm_o_test.gtkw"):
            sim.run()

    def test_conf(self):
        dut = PWMPeripheral(name="dut", pins=PWMPins())
        def testbench():
            yield from self._write_reg(dut, self.REG_NUMR, 0x1F, 4)
            yield from self._write_reg(dut, self.REG_DENOM, 0xFF, 4)
            yield from self._write_reg(dut, self.REG_CONF, 0x0, 4)
            self.assertEqual((yield dut.pins.pwm.o), 0) # assert pwm_o to remain '0', when not enabled
            for i in range(1000): yield Tick()
        sim = Simulator(dut)
        sim.add_clock(2e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd("pwm_conf_test.vcd", "pwm_conf_test.gtkw"):
            sim.run()

    def test_dir(self):
        dut = PWMPeripheral(name="dut", pins=PWMPins())
        def testbench():
            yield from self._write_reg(dut, self.REG_NUMR, 0x1F, 4)
            yield from self._write_reg(dut, self.REG_DENOM, 0xFF, 4)
            yield from self._write_reg(dut, self.REG_CONF, 0x03, 4)
            self.assertEqual((yield dut.pins.dir.o), 1) # assert direction to be '1'
            for i in range(10): yield Tick()
            yield from self._write_reg(dut, self.REG_CONF, 0x01, 4)
            self.assertEqual((yield dut.pins.dir.o), 0) # assert direction to be '0'
        sim = Simulator(dut)
        sim.add_clock(2e-6)
        sim.add_testbench(testbench)
        with sim.write_vcd("pwm_dir_test.vcd", "pwm_dir_test.gtkw"):
            sim.run()

if __name__ == "__main__":
    unittest.main()

