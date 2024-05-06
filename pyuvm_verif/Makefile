CWD=$(shell pwd)
SIM=verilator
VERILOG_SOURCES=$(wildcard $(CWD)/verilog/*.v) $(wildcard $(CWD)/../build/export/ips/*.v)
.PHONY: print_vars

ifeq ($(ARG),SPI)
    MODULE := testbench_spi
    TOPLEVEL = spi_wrap
else ifeq ($(ARG),FLASH)
    print_vars:
		@echo "TODO PERIPHERAL $(ARG)"
endif

COMPILE_ARGS += -Wno-fatal -Wno-BLKANDNBLK --timing --trace
EXTRA_ARGS += --trace --trace-structs

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns
include $(shell pdm run cocotb-config --makefiles)/Makefile.sim
