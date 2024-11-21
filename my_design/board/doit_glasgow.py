import importlib.resources

from doit.tools import run_once


TOOLS_DIR = importlib.resources.files("my_design") / "tools"


def task_build_bitstream():
    return {
        "actions": [
	        "pdm run chipflow board build-bitstream",
        ],
        "targets": [
            "build/board/top.bin",
        ],
        "uptodate": [
            run_once,
        ],
    }


def task_load_bitstream():
    return {
        "actions": [
            f"pdm run python {TOOLS_DIR}/glasgow_load.py build/board/top.bin",
        ],
        "file_dep": [
            "build/board/top.bin",
        ],
        "uptodate": [
            False,
        ],
    }


def task_flash_software():
    return {
        "actions": [
	        "pdm run glasgow run memory-25x -V 3.3 --pins-cs 7 --pin-sck 6 --pins-io 5,4,8,9 erase-program -S 4096 -P 64 0x100000 -f zephyr.bin",
	        "pdm run glasgow run memory-25x -V 3.3 --pins-cs 7 --pin-sck 6 --pins-io 5,4,8,9 verify 0x100000 -f zephyr.bin",
        ],
    }
