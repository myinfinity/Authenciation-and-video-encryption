/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#ifndef APPLICATIONS_CHEBYSHEV_H_
#define APPLICATIONS_CHEBYSHEV_H_

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <rtthread.h>

typedef rt_uint32_t uint256_t[8];
typedef rt_uint32_t uint512_t[16];

// 2×2 矩阵结构，每元素为 256 位整数
typedef struct {
    uint256_t a[2][2];
} Matrix2x2;

void set_uint256(uint256_t *x,
        rt_uint32_t limb7, rt_uint32_t limb6, rt_uint32_t limb5, rt_uint32_t limb4,
        rt_uint32_t limb3, rt_uint32_t limb2, rt_uint32_t limb1, rt_uint32_t limb0);
void print_uint256(const uint256_t a);
rt_uint32_t big_add(const uint256_t a, const uint256_t b, uint256_t res);
void chebyshev_Tn(const uint256_t *n, const uint256_t *x, const uint256_t *p,uint256_t* Tn, uint256_t* Tn_minus_1);

#endif /* APPLICATIONS_CHEBYSHEV_H_ */
