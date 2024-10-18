#undef NDEBUG

#define TRACE 0

#include <cxxrtl/cxxrtl.h>
#include <cxxrtl/cxxrtl_server.h>
#if TRACE
#include <cxxrtl/cxxrtl_vcd.h>
#endif
#include "sim_soc.h"
#include "models.h"

#include <fstream>
#include <filesystem>

using namespace cxxrtl::time_literals;
using namespace cxxrtl_design;

int main(int argc, char **argv) {
    p_sim__top top;

    spiflash_model flash("flash",
        top.p_qspi__sck____o,
        top.p_qspi__cs____o,
        top.p_qspi__io____o, top.p_qspi__io____oe, top.p_qspi__io____i);

    uart_model uart("uart", top.p_uart__tx____o, top.p_uart__rx____i);

    cxxrtl::agent agent(cxxrtl::spool("spool.bin"), top);
    if (getenv("DEBUG")) // can also be done when a condition is violated, etc
        std::cerr << "Waiting for debugger on " << agent.start_debugging() << std::endl;

    /* open_event_log("events.json"); */
    /* open_input_commands("../../my_design/tests/input.json"); */

#if TRACE
    cxxrtl::vcd_writer vcd;
    std::ofstream vcd_file;
    debug_items debug_items;
    uint64_t cycle = 0;

    vcd_file.open("trace.vcd");
    top.debug_info(&debug_items, /*scopes=*/nullptr, "");
    vcd.timescale(1, "us");
    vcd.add_without_memories(debug_items);
#endif

    unsigned timestamp = 0;
    auto tick = [&]() {
        flash.step(timestamp);
        uart.step(timestamp);

        top.p_clk.set(false);
        agent.step();
        agent.advance(1_us);
        ++timestamp;
#if TRACE
	vcd.sample(2 * cycle);
#endif

        top.p_clk.set(true);
        agent.step();
        agent.advance(1_us);
        ++timestamp;

        if (timestamp % 100000 == 0)
            agent.snapshot();
#if TRACE
	vcd.sample(2 * cycle + 1);
	vcd_file << vcd.buffer;
	vcd.buffer.clear();
	cycle += 1;
#endif
    };

    /* flash.load_data("../software/software.bin", 0x00100000U); */
    flash.load_data("../../zephyr.bin", 0x00100000U);
    agent.step();
    agent.advance(1_us);

    top.p_rst.set(true);
    tick();

    top.p_rst.set(false);
    /* for (int i = 0; i < 2000000; i++) */
    while (1)
        tick();

    /* close_event_log(); */
    return 0;
}
