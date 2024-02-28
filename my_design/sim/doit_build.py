import os
import sys
from pathlib import Path
import shutil

import yowasp_yosys
import chipflow_lib.config
from doit.action import CmdAction


DESIGN_DIR = os.path.dirname(__file__) + "/.."
YOSYS_CXXRTL_DIR = os.path.abspath(
    os.path.dirname(yowasp_yosys.__file__)) + "/share/include/backends/cxxrtl/runtime"
BUILD_DIR = "./build/sim"
CXX = f"{sys.executable} -m ziglang c++"
CXXFLAGS = f"-O3 -g -std=c++17 -Wno-array-bounds -Wno-shift-count-overflow"
RTL_CXXFLGAGS = "-O1 -std=c++17 -fbracket-depth=1024"

def task_build_sim_soc_c_files():
    return {
        "actions": [f"cd {BUILD_DIR} && pdm run yowasp-yosys sim_soc.ys"],
        "targets": [f"{BUILD_DIR}/sim_soc.cc", f"{BUILD_DIR}/sim_soc.h"],
        "file_dep": [f"{BUILD_DIR}/sim_soc.ys", f"{BUILD_DIR}/sim_soc.il"],
    }


def task_build_sim_soc_objects():
    def get_build_cmd():
        cmd = f"{CXX} -I . -I {YOSYS_CXXRTL_DIR} {RTL_CXXFLGAGS} "
        cmd += f"-o {BUILD_DIR}/sim_soc.o -c {BUILD_DIR}/sim_soc.cc"

        return cmd

    return {
        "actions": [CmdAction(get_build_cmd)],
        "targets": [f"{BUILD_DIR}/sim_soc.o"],
        "file_dep": [f"{BUILD_DIR}/sim_soc.cc", f"{BUILD_DIR}/sim_soc.h"],
    }


def task_gather_sim_project_files():
    src_files = []
    target_files = []
    sources = ["main", "models"]

    for source in sources:
        src_files.append(f"{DESIGN_DIR}/sim/{source}.cc")
        target_files.append(f"{BUILD_DIR}/{source}.cc")
        if os.path.exists(f"{DESIGN_DIR}/sim/{source}.h"):
            src_files.append(f"{DESIGN_DIR}/sim/{source}.h")
            target_files.append(f"{BUILD_DIR}/{source}.h")

    def do_copy():
        # Ensure dir exists
        Path(f"{BUILD_DIR}").mkdir(parents=True, exist_ok=True)

        for i in range(len(src_files)):
            shutil.copyfile(src_files[i - 1], target_files[i - 1])

    return {
        "actions": [do_copy],
        "file_dep": src_files,
        "targets": target_files,
    }


def task_build_sim_objects():
    sources = ["main", "models"]

    for source in sources:
        obj_file = f"{BUILD_DIR}/{source}.o"
        yield {
            "name": obj_file,
            "actions": [f"{CXX} -I .  -I {BUILD_DIR} -I {YOSYS_CXXRTL_DIR} {CXXFLAGS} -o {obj_file} -c {BUILD_DIR}/{source}.cc"],
            "targets": [obj_file],
            "file_dep": [f"{BUILD_DIR}/{source}.cc", f"{BUILD_DIR}/sim_soc.h"],
        }


def task_build_sim():
    exe = ".exe" if os.name == "nt" else ""

    def get_build_cmd():
        return f"{CXX} -o {BUILD_DIR}/sim_soc{exe} {BUILD_DIR}/sim_soc.o {BUILD_DIR}/main.o {BUILD_DIR}/models.o"

    return {
        "actions": [CmdAction(get_build_cmd)],
        "targets": [f"{BUILD_DIR}/sim_soc{exe}"],
        "file_dep": [f"{BUILD_DIR}/sim_soc.o", f"{BUILD_DIR}/main.o", f"{BUILD_DIR}/models.o"],
    }
