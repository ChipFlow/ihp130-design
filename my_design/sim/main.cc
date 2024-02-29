#undef NDEBUG

#include <cxxrtl/cxxrtl.h>
#include <cxxrtl/cxxrtl_server.h>
#include "sim_soc.h"
#include "models.h"

#include <fstream>
#include <filesystem>

using namespace cxxrtl::time_literals;
using namespace cxxrtl_design;

template <class Design>
struct design_runner {
    std::unique_ptr<Design> design;
    std::unique_ptr<cxxrtl::agent<cxxrtl::tcp_link, Design>> agent;

    design_runner() {
        if (getenv("DEBUG")) {
            agent = std::make_unique<cxxrtl::agent<cxxrtl::tcp_link, Design>>(cxxrtl::spool("spool.bin"));
            std::cerr << "Connect your CXXRTL debugger to " << agent->get_link_uri() << std::endl;
        } else {
            design = std::make_unique<Design>();
        }
    }

    Design &get_toplevel() {
        if (design != nullptr)
            return *design;
        if (agent != nullptr)
            return agent->get_toplevel();
        assert(false);
    }

    size_t step(const cxxrtl::time &dt) {
        if (design != nullptr)
            return design->step();
        if (agent != nullptr) {
            size_t deltas = agent->step();
            agent->advance(dt);
            return deltas;
        }
        assert(false);
    }
};

int main(int argc, char **argv) {
    design_runner<p_sim__top> runner;
    p_sim__top &top = runner.get_toplevel();

    spiflash_model flash("flash", top.p_flash____clk__o, top.p_flash____csn__o,
        top.p_flash____d__o, top.p_flash____d__oe, top.p_flash____d__i);

    uart_model uart_0("uart_0", top.p_uart__0____tx__o, top.p_uart__0____rx__i);
    uart_model uart_1("uart_1", top.p_uart__1____tx__o, top.p_uart__1____rx__i);

    gpio_model gpio_0("gpio_0", top.p_gpio__0____o, top.p_gpio__0____oe, top.p_gpio__0____i);
    gpio_model gpio_1("gpio_1", top.p_gpio__1____o, top.p_gpio__1____oe, top.p_gpio__1____i);

    open_event_log("events.json");

    unsigned timestamp = 0;
    auto tick = [&]() {
        flash.step(timestamp);
        uart_0.step(timestamp);
        uart_1.step(timestamp);

        gpio_0.step(timestamp);
        gpio_1.step(timestamp);

        top.p_clk.set(false);
        runner.step(1_us);
        ++timestamp;

        top.p_clk.set(true);
        runner.step(1_us);
        ++timestamp;
    };

    flash.load_data("../software/software.bin", 0x00100000U);
    runner.step(1_us);

    top.p_rst.set(true);
    tick();

    top.p_rst.set(false);
    for (int i = 0; i < 2000000; i++)
        tick();

    close_event_log();
    return 0;
}
