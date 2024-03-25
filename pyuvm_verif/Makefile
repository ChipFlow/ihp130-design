CWD=$(shell pwd)
SIM=verilator
VERILOG_SOURCES=$(wildcard $(CWD)/verilog/*.v)
MODULE := testbench_spi
TOPLEVEL = spi_wrap

COMPILE_ARGS += -Wno-fatal -Wno-BLKANDNBLK --timing --trace
EXTRA_ARGS += --trace --trace-structs

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns
include $(shell pdm run cocotb-config --makefiles)/Makefile.sim
