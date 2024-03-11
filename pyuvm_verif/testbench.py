from cocotb.triggers import Join, Combine
from pyuvm import *
import random
import cocotb
import pyuvm

class SocEnv(uvm_env):
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        ConfigDB().set(None, "*", "SEQR", self.seqr)

@pyuvm.test()
class SocTest(uvm_test):
    def build_phase(self):
        self.env = SocEnv("env", self)

    def end_of_elaboration_phase(self):
        # TODO: create a test
        pass

    async def run_phase(self):
        # TODO: create a test
        pass
