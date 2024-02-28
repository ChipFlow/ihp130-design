#undef NDEBUG

#include <cxxrtl/cxxrtl.h>
#include "build/sim/sim_soc.h"
#include "models.h"


#include <fstream>
#include <filesystem>

using namespace cxxrtl_design;

int main(int argc, char **argv) {
    cxxrtl_design::p_sim__top top;

    spiflash_model flash("flash", top.p_flash____clk__o, top.p_flash____csn__o,
        top.p_flash____d__o, top.p_flash____d__oe, top.p_flash____d__i);

    uart_model uart_0("uart_0", top.p_uart__0____tx__o, top.p_uart__0____rx__i);
    uart_model uart_1("uart_1", top.p_uart__1____tx__o, top.p_uart__1____rx__i);

    gpio_model gpio_0("gpio_0", top.p_gpio__0____o, top.p_gpio__0____oe, top.p_gpio__0____i);
    gpio_model gpio_1("gpio_1", top.p_gpio__1____o, top.p_gpio__1____oe, top.p_gpio__1____i);

    flash.load_data("../software/software.bin", 0x00100000U);

    open_event_log("events.json");

    top.step();
    unsigned timestamp = 0;
    auto tick = [&]() {
        flash.step(timestamp);
        uart_0.step(timestamp);
        uart_1.step(timestamp);

        gpio_0.step(timestamp);
        gpio_1.step(timestamp);

        top.p_clk.set(false);
        top.step();
        ++timestamp;

        top.p_clk.set(true);
        top.step();
        ++timestamp;
    };
    top.p_rst.set(true);
    tick();
    top.p_rst.set(false);

    for (int i = 0; i < 2000000; i++) {
        tick();
    }
    close_event_log();
    return 0;
}
