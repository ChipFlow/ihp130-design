#include <stdint.h>
#ifndef SPI_H
#define SPI_H
typedef struct {
	uint32_t config;
	uint32_t divider;
	uint32_t send_data;
	uint32_t receive_data;
	uint32_t status;
} spi_regs_t;

#endif
