#include <cxxrtl/cxxrtl.h>
#include <stdlib.h>
#include <stdio.h>
#include <fstream>
#include <stdarg.h>
#include "models.h"

namespace cxxrtl_design {

// Helper functions

std::string vstringf(const char *fmt, va_list ap)
{
    std::string string;
    char *str = NULL;

#if defined(_WIN32) || defined(__CYGWIN__)
    int sz = 64 + strlen(fmt), rc;
    while (1) {
        va_list apc;
        va_copy(apc, ap);
        str = (char *)realloc(str, sz);
        rc = vsnprintf(str, sz, fmt, apc);
        va_end(apc);
        if (rc >= 0 && rc < sz)
            break;
        sz *= 2;
    }
#else
    if (vasprintf(&str, fmt, ap) < 0)
        str = NULL;
#endif

    if (str != NULL) {
        string = str;
        free(str);
    }

    return string;
}

std::string stringf(const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    std::string result = vstringf(format, ap);
    va_end(ap);
    return result;
}

// Event logging

static std::ofstream event_log;

void open_event_log(const std::string &filename) {
    event_log.open(filename);
    if (!event_log) {
        throw std::runtime_error("failed to open event log for writing!");
    }
    event_log << "{" << std::endl;
    event_log << "\"events\": [" << std::endl;

}
void log_event(unsigned timestamp, const std::string &peripheral, const std::string &event_type, const std::string &payload) {
    static bool had_event = false;
    if (had_event)
        event_log << "," << std::endl;
    event_log << stringf("{ \"timestamp\": %u, \"peripheral\": \"%s\", \"event\": \"%s\", \"payload\": %s }",
        timestamp, peripheral.c_str(), event_type.c_str(), payload.c_str());
    had_event = true;
}
void close_event_log() {
    event_log << std::endl << "]" << std::endl;
    event_log << "}" << std::endl;
}

// SPI flash
void spiflash_model::load_data(const std::string &filename, unsigned offset) {
    std::ifstream in(filename, std::ifstream::binary);
    if (offset >= data.size()) {
        throw std::out_of_range("flash: offset beyond end");
    }
    if (!in) {
        throw std::runtime_error("flash: failed to read input file: " + filename);
    }
    in.read(reinterpret_cast<char*>(data.data() + offset), (data.size() - offset));
}
void spiflash_model::step(unsigned timestamp) {
    auto process_byte = [&]() {
        s.out_buffer = 0;
        if (s.byte_count == 0) {
            s.addr = 0;
            s.data_width = 1;
            s.command = s.curr_byte;
            if (s.command == 0xab) {
                // power up
            } else if (s.command == 0x03 || s.command == 0x9f || s.command == 0xff
                || s.command == 0x35 || s.command == 0x31 || s.command == 0x50
                || s.command == 0x05 || s.command == 0x01 || s.command == 0x06) {
                // nothing to do
            } else if (s.command == 0xeb) {
                s.data_width = 4;
            } else {
                throw std::runtime_error(stringf("flash: unknown command %02x", s.command));
            }
        } else {
            if (s.command == 0x03) {
                // Single read
                if (s.byte_count <= 3) {
                    s.addr |= (uint32_t(s.curr_byte) << ((3 - s.byte_count) * 8));
                }
                if (s.byte_count >= 3) {
                    s.out_buffer = data.at(s.addr);
                    s.addr = (s.addr + 1) & 0x00FFFFFF;
                }
            } else if (s.command == 0xeb) {
                // Quad read
                if (s.byte_count <= 3) {
                    s.addr |= (uint32_t(s.curr_byte) << ((3 - s.byte_count) * 8));
                }
                if (s.byte_count >= 6) { // 1 mode, 2 dummy clocks
                    // read 4 bytes
                    s.out_buffer = data.at(s.addr);
                    s.addr = (s.addr + 1) & 0x00FFFFFF;
                }
            }
        }
        if (s.command == 0x9f) {
            // Read ID
            static const std::array<uint8_t, 4> flash_id{0xCA, 0x7C, 0xA7, 0xFF};
            s.out_buffer = flash_id.at(s.byte_count % int(flash_id.size()));
        }
    };

    if (csn && !s.last_csn) {
        s.bit_count = 0;
        s.byte_count = 0;
        s.data_width = 1;
    } else if (clk && !s.last_clk && !csn) {
        if (s.data_width == 4)
            s.curr_byte = (s.curr_byte << 4U) | (d_o.get<uint32_t>() & 0xF);
        else
            s.curr_byte = (s.curr_byte << 1U) | d_o.bit(0);
        s.out_buffer = s.out_buffer << unsigned(s.data_width);
        s.bit_count += s.data_width;
        if (s.bit_count == 8) {
            process_byte();
            ++s.byte_count;
            s.bit_count = 0;
        }
    } else if (!clk && s.last_clk && !csn) {
        if (s.data_width == 4) {
            d_i.set((s.out_buffer >> 4U) & 0xFU);
        } else {
            d_i.set(((s.out_buffer >> 7U) & 0x1U) << 1U);
        }
    }
    s.last_clk = bool(clk);
    s.last_csn = bool(csn);
}

// UART

void uart_model::step(unsigned timestamp) {
    if (s.counter == 0) {
        if (s.tx_last && !tx) { // start bit
            s.counter = 1;
        }
    } else {
        ++s.counter;
        if (s.counter > (baud_div / 2) && ((s.counter - (baud_div / 2)) % baud_div) == 0) {
            int bit = ((s.counter - (baud_div / 2)) / baud_div);
            if (bit >= 1 && bit <= 8) {
                // update shift register
                s.sr = (tx ? 0x80U : 0x00U) | (s.sr >> 1U);
            }
            if (bit == 8) {
                // print to console
                log_event(timestamp, name, "tx", stringf("%u", s.sr));
                if (name == "uart_0")
                    fprintf(stderr, "%c", char(s.sr));
            }
            if (bit == 9) {
                // end
                s.counter = 0;
            }
        }
    }
    s.tx_last = bool(tx);
    rx.set(1); // idle
}

// GPIO

void gpio_model::step(unsigned timestamp) {
    uint32_t o_value = o.get<uint32_t>();
    uint32_t oe_value = oe.get<uint32_t>();
    if (o_value != s.o_last || oe_value != s.oe_last) {
        std::string formatted_value = "\"";
        for (int i = width - 1; i >= 0; i--) {
            if (oe_value & (1U << unsigned(i)))
                formatted_value += (o_value & (1U << unsigned(i))) ? '1' : '0';
            else
                formatted_value += 'Z';
        }
        formatted_value += '"';
        log_event(timestamp, name, "change", formatted_value);
    }
    s.o_last = o_value;
    s.oe_last = oe_value;
}


}
