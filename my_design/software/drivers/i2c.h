#include <stdint.h>
#ifndef I2C_H
#define I2C_H
typedef struct {
	uint32_t divider;
	uint32_t action;
	uint32_t send_data;
	uint32_t receive_data;
	uint32_t status;
} i2c_regs_t;

#endif
