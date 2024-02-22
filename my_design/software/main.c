#include <stdint.h>

#include "generated/soc.h"

void main() {
	puts("🐱: nyaa~!\r\n");

	puts("SoC type: ");
	puthex(SOC_ID->type);
	puts("\r\n");

	puts("SoC version: ");
	puthex(SOC_ID->version);
	puts("\r\n");

	puts("Flash ID: ");
	puthex(spiflash_read_id(SPIFLASH));
	puts("\r\n");

	puts("Entering QSPI mode\r\n");
	spiflash_set_qspi_flag(SPIFLASH);
	spiflash_set_quad_mode(SPIFLASH);

	puts("Initialised!\r\n");

	while (1) {
		// // Listen for button presses
		// next_buttons = BTN_GPIO->in;
		// if ((next_buttons & 1U) && !(last_buttons & 1U))
		// 	puts("button 1 pressed!\n");
		// if ((next_buttons & 2U) && !(last_buttons & 2U))
		// 	puts("button 2 pressed!\n");
		// last_buttons = next_buttons;
	};
}
