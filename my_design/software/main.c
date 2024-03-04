#include <stdint.h>
#include "generated/soc.h"

char uart_getch_block(volatile uart_regs_t *uart) {
	while (!uart->rx_avail)
		;
	return uart->rx_data;
}

uint32_t spi_xfer(volatile spi_regs_t *spi, uint32_t data, uint32_t width) {
	spi->config = ((width - 1) << 3) | 0x06; // CS=1, SCK_EDGE=1, SCK_IDLE=0
	spi->send_data = data << (32U - width);
	while (!(spi->status & 0x1)) // wait for rx full
		;
	spi->config = ((width - 1) << 3) | 0x02; // CS=0, SCK_EDGE=1, SCK_IDLE=0
	return spi->receive_data; 
}

void main() {
	puts("🐱: nyaa~!\r\n");

	puts("Flash ID: ");
	puthex(spiflash_read_id(SPIFLASH));
	puts("\r\n");

	puts("Entering QSPI mode\r\n");
	spiflash_set_qspi_flag(SPIFLASH);
	spiflash_set_quad_mode(SPIFLASH);

	puts("Initialised!\r\n");

	puts("SoC type: ");
	puthex(SOC_ID->type);
	// This would make the golden reference output change every commit
	// puts(" ");
	// puthex(SOC_ID->version);
	puts("\r\n");

	GPIO_1->oe = 0xF0;
	GPIO_1->out = 0x50;
	GPIO_1->out = 0xA0;
	GPIO_1->oe = 0x00;

	uart_puts(UART_1, "ABCD");

	puts("GPIO: ");
	puthex(GPIO_1->in);
	puts(" ");
	puthex(GPIO_1->in);
	puts("\n");

	puts("UART1: ");
	putc(uart_getch_block(UART_1));
	puts(" ");
	putc(uart_getch_block(UART_1));
	puts("\n");


	puts("SPI: ");

	USER_SPI_0->divider = 2;

	// test 8 bit transfer
	puthex(spi_xfer(USER_SPI_0, 0x5A, 8));
	puts(" ");
	// test an odd 21 bit transfer 
	puthex(spi_xfer(USER_SPI_0, 0x123456, 21));
	puts("\n");

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
