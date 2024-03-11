CWD=$(shell pwd)
SIM=verilator
VERILOG_SOURCES=$(wildcard $(CWD)/verilog/*.v)
MODULE := testbench
TOPLEVEL = top

COMPILE_ARGS += -Wno-fatal -Wno-BLKANDNBLK

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns
include $(shell pdm run cocotb-config --makefiles)/Makefile.sim
