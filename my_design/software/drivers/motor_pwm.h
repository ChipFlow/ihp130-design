/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef MOTOR_PWM_H
#define MOTOR_PWM_H

#include <stdint.h>

typedef struct {
    uint32_t numr;
    uint32_t denom;
    uint32_t conf;
    uint32_t stop_int;
    uint32_t status;
} motor_pwm_regs_t;

#endif

