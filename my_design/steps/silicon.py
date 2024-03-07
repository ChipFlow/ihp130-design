from chipflow_lib.steps.silicon import SiliconStep
from ._chipflow_top import ChipflowTop

class MySiliconStep(SiliconStep):
    def prepare(self):
        return self.platform.build(ChipflowTop(), name="testchip_top")

