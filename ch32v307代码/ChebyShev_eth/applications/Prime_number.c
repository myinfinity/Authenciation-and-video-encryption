/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#include "Prime_number.h"

typedef unsigned long long ull;

// 基本素性检查（试除法）
int checknum(ull n) {
    if (n < 2) return 0;
    for (ull i = 2; i * i <= n; i++) {
        if (n % i == 0)
            return 0;
    }
    return 1;
}

// 计算 (base^exp) % mod 使用快速幂
ull mod_pow(ull base, ull exp, ull mod) {
    ull result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1)
            result = (result * base) % mod;
        base = (base * base) % mod;
        exp >>= 1;
    }
    return result;
}

// Miller-Rabin 测试
int miller_rabin(ull n, int k) {
    if (n <= 1) return 0;
    if (n == 2 || n == 3) return 1;
    if (n % 2 == 0) return 0;

    ull r = 0, d = n - 1;
    while ((d % 2) == 0) {
        d /= 2;
        r++;
    }

    for (int i = 0; i < k; i++) {
        ull a = 2 + rand() % (n - 3);
        ull x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1)
            continue;

        int continueLoop = 0;
        for (ull j = 0; j < r - 1; j++) {
            x = mod_pow(x, 2, n);
            if (x == n - 1) {
                continueLoop = 1;
                break;
            }
        }
        if (!continueLoop)
            return 0;
    }
    return 1;
}

// 随机生成指定位数的奇数
ull generate_odd_number(int bits) {
    ull min = 1ULL << (bits - 1);
    ull max = (1ULL << bits) - 1;
    ull candidate;

    do {
        candidate = ((ull)rand() << 32 | rand()) & max;
        candidate |= min;  // 确保位数正确
        candidate |= 1;    // 确保是奇数
    } while (candidate < min || candidate > max);

    return candidate;
}

// 生成素数
ull creat_number(int bits) {
    ull p;
    while (1) {
        p = generate_odd_number(bits);
        if (miller_rabin(p, 5))  // 5 次测试
            return p;
    }
}
