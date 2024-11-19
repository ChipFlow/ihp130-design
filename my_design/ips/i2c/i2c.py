from amaranth import *
from amaranth.lib import io, wiring
from amaranth.lib.wiring import In, Out, connect, flipped
from amaranth.lib.cdc import FFSynchronizer

from amaranth_soc import csr
from .glasgow_i2c import I2CInitiator


__all__ = ["I2CPeripheral"]


class I2CPeripheral(wiring.Component):
    class Divider(csr.Register, access="rw"):
        """I2C SCK clock divider, 1 = divide by 4"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.RW, 12))

    class Action(csr.Register, access="w"):
        """
        reset: reset the core, e.g. in case of a bus lockup
        start: write 1 to trigger I2C start
        stop: write 1 to trigger I2C stop
        read_ack: write 1 to trigger I2C read and ACK
        read_nack: write 1 to trigger I2C read and NACK
        """
        reset:     csr.Field(csr.action.W, 1)
        start:     csr.Field(csr.action.W, 1)
        stop:      csr.Field(csr.action.W, 1)
        read_ack:  csr.Field(csr.action.W, 1)
        read_nack: csr.Field(csr.action.W, 1)

    class SendData(csr.Register, access="w"):
        """writes the given data onto the I2C bus when written to"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.W, 8))

    class RecvData(csr.Register, access="r"):
        """data received from the last read"""
        def __init__(self):
            super().__init__(csr.Field(csr.action.R, 8))

    class Status(csr.Register, access="r"):
        busy: csr.Field(csr.action.R, 1)
        ack:  csr.Field(csr.action.R, 1)

    """
    A minimal I2C controller wrapping the Glasgow core
    """
    def __init__(self, ports):
        assert len(ports.scl) == 1 and ports.scl.direction == io.Direction.Bidir
        assert len(ports.sda) == 1 and ports.sda.direction == io.Direction.Bidir

        self._ports = ports

        regs = csr.Builder(addr_width=5, data_width=8)

        self._divider   = regs.add("divider",   self.Divider(),  offset=0x00)
        self._action    = regs.add("action",    self.Action(),   offset=0x04)
        self._send_data = regs.add("send_data", self.SendData(), offset=0x08)
        self._recv_data = regs.add("recv_data", self.RecvData(), offset=0x0C)
        self._status    = regs.add("status",    self.Status(),   offset=0x10)

        self._bridge = csr.Bridge(regs.as_memory_map())

        super().__init__({
            "csr_bus": In(csr.Signature(addr_width=regs.addr_width, data_width=regs.data_width)),
        })
        self.csr_bus.memory_map = self._bridge.bus.memory_map

    def elaborate(self, platform):
        m = Module()

        m.submodules.bridge = self._bridge

        connect(m, flipped(self.csr_bus), self._bridge.bus)

        i2c_reset = Signal()

        m.submodules.i2c = i2c = ResetInserter(i2c_reset)(I2CInitiator(self._ports))

        m.d.comb += [
            i2c.period_cyc.eq(self._divider.f.data),

            i2c_reset.eq(self._action.f.reset.w_data & self._action.f.reset.w_stb),
            i2c.start.eq(self._action.f.start.w_data & self._action.f.start.w_stb),
            i2c.stop .eq(self._action.f.stop .w_data & self._action.f.stop .w_stb),
            i2c.read .eq((self._action.f.read_ack .w_data & self._action.f.read_ack .w_stb) | \
                         (self._action.f.read_nack.w_data & self._action.f.read_nack.w_stb)),
            i2c.ack_i.eq(self._action.f.read_ack.w_data & self._action.f.read_ack.w_stb),

            i2c.data_i.eq(self._send_data.f.w_data),
            i2c.write .eq(self._send_data.f.w_stb),

            self._recv_data.f.r_data.eq(i2c.data_o),

            self._status.f.busy.r_data.eq(i2c.busy),
            self._status.f.ack .r_data.eq(i2c.ack_o),
        ]

        return m

if __name__ == '__main__':
    from amaranth.back import verilog
    from pathlib import Path
    i2c = I2CPeripheral(name="i2c")
    Path("build/export/ips").mkdir(parents=True, exist_ok=True)
    with open("build/export/ips/i2c.v", "w") as f:
        f.write(verilog.convert(i2c, name="i2c_peripheral"))
