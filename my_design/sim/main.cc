#undef NDEBUG

#include <cxxrtl/cxxrtl.h>
#include <cxxrtl/cxxrtl_server.h>
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
    uart_model uart_1("uart_1", top.p_uart__1____tx__o, top.p_uart__1____rx__i);

    gpio_model gpio_0("gpio_0", top.p_gpio__0____o, top.p_gpio__0____oe, top.p_gpio__0____i);
    gpio_model gpio_1("gpio_1", top.p_gpio__1____o, top.p_gpio__1____oe, top.p_gpio__1____i);

    spi_model spi_0("spi_0", top.p_user__spi__0____sck__o, top.p_user__spi__0____csn__o, top.p_user__spi__0____mosi__o, top.p_user__spi__0____miso__i);
    spi_model spi_1("spi_1", top.p_user__spi__1____sck__o, top.p_user__spi__1____csn__o, top.p_user__spi__1____mosi__o, top.p_user__spi__1____miso__i);
    spi_model spi_2("spi_2", top.p_user__spi__2____sck__o, top.p_user__spi__2____csn__o, top.p_user__spi__2____mosi__o, top.p_user__spi__2____miso__i);

    cxxrtl::agent agent(cxxrtl::spool("spool.bin"), top);
    if (getenv("DEBUG")) // can also be done when a condition is violated, etc
        std::cerr << "Waiting for debugger on " << agent.start_debugging() << std::endl;

    open_event_log("events.json");
    open_input_commands("../../my_design/tests/input.json");

    unsigned timestamp = 0;
    auto tick = [&]() {
        // agent.print(stringf("timestamp %d\n", timestamp), CXXRTL_LOCATION);

        flash.step(timestamp);
        uart_0.step(timestamp);
        uart_1.step(timestamp);

        gpio_0.step(timestamp);
        gpio_1.step(timestamp);

        spi_0.step(timestamp);
        spi_1.step(timestamp);
        spi_2.step(timestamp);

        top.p_clk.set(false);
        agent.step();
        agent.advance(1_us);
        ++timestamp;

        top.p_clk.set(true);
        agent.step();
        agent.advance(1_us);
        ++timestamp;

        // if (timestamp == 10)
        //     agent.breakpoint(CXXRTL_LOCATION);
    };

    flash.load_data("../software/software.bin", 0x00100000U);
    agent.step();
    agent.advance(1_us);

    top.p_rst.set(true);
    tick();

    top.p_rst.set(false);
    for (int i = 0; i < 2000000; i++)
        tick();

    close_event_log();
    return 0;
}
