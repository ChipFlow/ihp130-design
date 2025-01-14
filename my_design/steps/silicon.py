from dataclasses import dataclass
from typing import List, Dict

from amaranth import (
        Module,
        Elaboratable,
        Signal,
        ClockDomain,
        ClockSignal,
        ResetSignal
        )

from amaranth.lib import io
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import Component
from chipflow_lib.steps.silicon import SiliconStep

from ..design import MySoC
from ..ips.ports import PortGroup


__all__ = ["MySiliconStep"]

PortMapping = Dict[str, str]


@dataclass
class Feature:
    name: str


@dataclass
class Heartbeat:
    pin: str
    clock_domain: str = "sync"
    counter_size: int = 23
    name: str = "heartbeat"

    def install(self, m, platform):
        # Heartbeat LED (to confirm clock/reset alive)
        heartbeat_ctr = Signal(self.counter_size)
        getattr(m.d, self.clock_domain).__iadd__(heartbeat_ctr.eq(heartbeat_ctr + 1))

        heartbeat_buffer = io.Buffer("o", platform.request(self.pin))
        setattr(m.submodules, "heartbeat_buffer_" + self.pin, heartbeat_buffer)
        m.d.comb += heartbeat_buffer.o.eq(heartbeat_ctr[-1])


@dataclass
class SiliconTop(Elaboratable):
    clocks: Dict[str, str]
    reset: str
    features: List[Feature]
    ports: Dict[str, PortMapping]
    components: Dict[str, [type[Component]]]

    def elaborate(self, platform):
        m = Module()

        for clock, pin in self.clocks.items():
            if clock == '':
                clock = 'sync'
            setattr(m.domains, clock,  ClockDomain(name=clock))
            clk_buffer = io.Buffer("i", platform.request(pin))
            setattr(m.submodules, "clk_buffer_" + clock, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)

        rst_buffer = io.Buffer("i", ~platform.request(self.reset))
        m.submodules.rst_buffer = rst_buffer
        m.submodules.rst_sync = FFSynchronizer(rst_buffer.i, ResetSignal())

        ports = PortGroup()
        for group, mapping in self.ports.items():
            pg = PortGroup()
            setattr(ports, group, pg)
            for port, pin_str in mapping.items():
                pin_names = pin_str.split(',')
                start = platform.request(pin_names[0])
                pins = sum(map(lambda x: platform.request(x), pin_names[1:]), start=start)
                setattr(pg, port, pins)

        for name, cls in self.components.items():
            setattr(m.submodules, name, cls(ports))

        return m

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, obj):
        return id(self) == id(obj)


TOP = SiliconTop(
    clocks={'sync': 'sys_clk'},
    reset="sys_rst_n",
    features=[Heartbeat("heartbeat")],
    ports={
        'qspi': {
            'sck': 'flash_clk',
            'io': 'flash_d0,flash_d1,flash_d2,flash_d3',
            'cs': 'flash_csn',
        },
        'i2c': {
            'scl': 'i2c0_scl',
            'sda': 'i2c0_sda',
        },
        'uart': {
            'rx': 'uart0_rx',
            'tx': 'uart0_tx',
        },
    },
    components={'soc': MySoC}
)

'''
class _ChipflowTop(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        # Clock generation
        m.domains.sync = ClockDomain()

        m.submodules.clk_buffer = clk_buffer = io.Buffer("i", platform.request("sys_clk"))
        m.submodules.rst_buffer = rst_buffer = io.Buffer("i", ~platform.request("sys_rst_n"))

        m.d.comb += ClockSignal().eq(clk_buffer.i)
        m.submodules.rst_sync = FFSynchronizer(rst_buffer.i, ResetSignal())

        # Heartbeat LED (to confirm clock/reset alive)
        heartbeat_ctr = Signal(23)
        m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)

        m.submodules.heartbeat_buffer = heartbeat_buffer = \
                io.Buffer("o", platform.request("heartbeat"))
        m.d.comb += heartbeat_buffer.o.eq(heartbeat_ctr[-1])

        # SoC ports
        ports = PortGroup()

        ports.qspi = PortGroup()
        ports.qspi.sck = platform.request("flash_clk")
        ports.qspi.io = (platform.request("flash_d0") + platform.request("flash_d1") +
                         platform.request("flash_d2") + platform.request("flash_d3"))
        ports.qspi.cs = platform.request("flash_csn")

        ports.i2c = PortGroup()
        ports.i2c.scl = platform.request("i2c0_scl")
        ports.i2c.sda = platform.request("i2c0_sda")

        ports.uart = PortGroup()
        ports.uart.rx = platform.request("uart0_rx")
        ports.uart.tx = platform.request("uart0_tx")

        m.submodules.soc = soc = MySoC(ports)

        return m
'''

class MySiliconStep(SiliconStep):
    def prepare(self):
        return self.platform.build(TOP, name="testchip_top")
