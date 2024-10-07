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

    spiflash_model flash("flash", top.p_flash____clk__o, top.p_flash____csn__o,
        top.p_flash____d__o, top.p_flash____d__oe, top.p_flash____d__i);

    uart_model uart_0("uart_0", top.p_uart__0____tx__o, top.p_uart__0____rx__i);
#if 0
    uart_model uart_1("uart_1", top.p_uart__1____tx__o, top.p_uart__1____rx__i);

    std::array<gpio_pin, 8> gpio_0_pins = {
        gpio_pin(top.p_gpio__0____0____i, top.p_gpio__0____0____o, top.p_gpio__0____0____oe),
        gpio_pin(top.p_gpio__0____1____i, top.p_gpio__0____1____o, top.p_gpio__0____1____oe),
        gpio_pin(top.p_gpio__0____2____i, top.p_gpio__0____2____o, top.p_gpio__0____2____oe),
        gpio_pin(top.p_gpio__0____3____i, top.p_gpio__0____3____o, top.p_gpio__0____3____oe),
        gpio_pin(top.p_gpio__0____4____i, top.p_gpio__0____4____o, top.p_gpio__0____4____oe),
        gpio_pin(top.p_gpio__0____5____i, top.p_gpio__0____5____o, top.p_gpio__0____5____oe),
        gpio_pin(top.p_gpio__0____6____i, top.p_gpio__0____6____o, top.p_gpio__0____6____oe),
        gpio_pin(top.p_gpio__0____7____i, top.p_gpio__0____7____o, top.p_gpio__0____7____oe)
    };
    std::array<gpio_pin, 8> gpio_1_pins = {
        gpio_pin(top.p_gpio__1____0____i, top.p_gpio__1____0____o, top.p_gpio__1____0____oe),
        gpio_pin(top.p_gpio__1____1____i, top.p_gpio__1____1____o, top.p_gpio__1____1____oe),
        gpio_pin(top.p_gpio__1____2____i, top.p_gpio__1____2____o, top.p_gpio__1____2____oe),
        gpio_pin(top.p_gpio__1____3____i, top.p_gpio__1____3____o, top.p_gpio__1____3____oe),
        gpio_pin(top.p_gpio__1____4____i, top.p_gpio__1____4____o, top.p_gpio__1____4____oe),
        gpio_pin(top.p_gpio__1____5____i, top.p_gpio__1____5____o, top.p_gpio__1____5____oe),
        gpio_pin(top.p_gpio__1____6____i, top.p_gpio__1____6____o, top.p_gpio__1____6____oe),
        gpio_pin(top.p_gpio__1____7____i, top.p_gpio__1____7____o, top.p_gpio__1____7____oe)
    };
    gpio_model<8> gpio_0("gpio_0", gpio_0_pins);
    gpio_model<8> gpio_1("gpio_1", gpio_1_pins);

    spi_model spi_0("spi_0", top.p_user__spi__0____sck__o, top.p_user__spi__0____csn__o, top.p_user__spi__0____mosi__o, top.p_user__spi__0____miso__i);
    spi_model spi_1("spi_1", top.p_user__spi__1____sck__o, top.p_user__spi__1____csn__o, top.p_user__spi__1____mosi__o, top.p_user__spi__1____miso__i);
    spi_model spi_2("spi_2", top.p_user__spi__2____sck__o, top.p_user__spi__2____csn__o, top.p_user__spi__2____mosi__o, top.p_user__spi__2____miso__i);

    i2c_model i2c_0("i2c_0", top.p_i2c__0____sda__oe, top.p_i2c__0____sda__i, top.p_i2c__0____scl__oe, top.p_i2c__0____scl__i);
    i2c_model i2c_1("i2c_1", top.p_i2c__1____sda__oe, top.p_i2c__1____sda__i, top.p_i2c__1____scl__oe, top.p_i2c__1____scl__i);
#endif

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
        uart_0.step(timestamp);
#if 0
        uart_1.step(timestamp);

        gpio_0.step(timestamp);
        gpio_1.step(timestamp);

        spi_0.step(timestamp);
        spi_1.step(timestamp);
        spi_2.step(timestamp);

        i2c_0.step(timestamp);
        i2c_1.step(timestamp);
#endif

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
