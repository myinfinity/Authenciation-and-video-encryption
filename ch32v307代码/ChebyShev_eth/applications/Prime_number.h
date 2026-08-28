/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#ifndef APPLICATIONS_PRIME_NUMBER_H_
#define APPLICATIONS_PRIME_NUMBER_H_
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

typedef unsigned long long ull;

int checknum(ull n);
ull mod_pow(ull base, ull exp, ull mod);
int miller_rabin(ull n, int k);
ull generate_odd_number(int bits);
ull creat_number(int bits);


#endif /* APPLICATIONS_PRIME_NUMBER_H_ */
