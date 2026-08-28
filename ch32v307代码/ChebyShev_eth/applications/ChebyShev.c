/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#include "ChebyShev.h"
static rt_uint32_t m;
static rt_uint64_t carry;
static rt_uint64_t sum;
static rt_uint64_t borrow;
static rt_uint64_t ai,bi;
static rt_uint64_t temp;
static rt_uint64_t t;
static uint512_t rem;
static uint512_t shifted;
static uint512_t t0, t1;
static uint256_t r0, r1;
static rt_uint32_t carry3;
static uint256_t one= { 0 };
static Matrix2x2 base;
static uint256_t e;
static Matrix2x2 tmp,tmp2;

// 构造转移矩阵 M
static Matrix2x2 M;
// M[0][0] = 2*x mod p
static uint256_t two_x = { 0 };
static rt_uint64_t carry4 = 0;
static rt_uint64_t t;
static uint256_t tmp256;
static uint256_t exp;

static Matrix2x2 Mpow;


rt_uint32_t clz32(rt_uint32_t x) {
    if (x == 0) return 32;
    m = 0;
    if ((x & 0xFFFF0000) == 0) { m += 16; x <<= 16; }
    if ((x & 0xFF000000) == 0) { m += 8;  x <<= 8; }
    if ((x & 0xF0000000) == 0) { m += 4;  x <<= 4; }
    if ((x & 0xC0000000) == 0) { m += 2;  x <<= 2; }
    if ((x & 0x80000000) == 0) { m += 1; }
    return m;
}


// 比较两个 256 位整数：返回 1 如果 a>b，0 等号，-1 如果 a<b。
int big_cmp(const uint256_t a, const uint256_t b) {
    for (int i = 7; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

// 256 位加法：res = a + b，无模（需手动处理进位）。返回进位（0 或 1）。
rt_uint32_t big_add(const uint256_t a, const uint256_t b, uint256_t res) {
    carry = 0;
    for (int i = 0; i < 8; i++) {
        sum = (rt_uint64_t)a[i] + b[i] + carry;
        res[i] = (rt_uint32_t)sum;
        carry = sum >> 32;
    }
    return (rt_uint32_t)carry;
}

// 256 位减法：res = a - b（假设 a >= b）。返回借位（0 或 1）。
rt_uint32_t big_sub(const uint256_t a, const uint256_t b, uint256_t res) {
    borrow = 0;
    for (int i = 0; i < 8; i++) {
        ai = a[i];
        bi = b[i] + borrow;
        if (ai >= bi) {
            res[i] = (rt_uint32_t)(ai - bi);
            borrow = 0;
        }
        else {
            res[i] = (rt_uint32_t)(((rt_uint64_t)1 << 32) + ai - bi);
            borrow = 1;
        }
    }
    return (rt_uint32_t)borrow;
}

// 256 位右移 1 位：res = a >> 1（用于指数右移）。
void big_shr1(const uint256_t a, uint256_t res) {
    carry = 0;
    for (int i = 7; i >= 0; i--) {
        temp = ((rt_uint64_t)carry << 32) | a[i];
        res[i] = (rt_uint32_t)(temp >> 1);
        carry = (rt_uint32_t)(temp & 1);
    }
}

// 512 位乘法：res = a * b（256 位 × 256 位）。学校本算法，时间复杂度 O(n²)。
void big_mul(const uint256_t a, const uint256_t b, uint512_t res) {
    // 初始化结果为 0
    for (int i = 0; i < 16; i++) res[i] = 0;
    // 逐字相乘累加
    for (int i = 0; i < 8; i++) {
        carry = 0;
        for (int j = 0; j < 8; j++) {
            t = (rt_uint64_t)a[i] * b[j] + res[i + j] + carry;
            res[i + j] = (rt_uint32_t)t;
            carry = t >> 32;
        }
        res[i + 8] = (rt_uint32_t)carry;
    }
}

// 512 位减法：res = a - b（假设 a >= b）。返回借位。
uint32_t big_sub512(const uint512_t a, const uint512_t b, uint512_t res) {
    borrow = 0;
    for (int i = 0; i < 16; i++) {
        ai = a[i];
        bi = b[i] + borrow;
        if (ai >= bi) {
            res[i] = (rt_uint32_t)(ai - bi);
            borrow = 0;
        }
        else {
            res[i] = (rt_uint32_t)(((rt_uint64_t)1 << 32) + ai - bi);
            borrow = 1;
        }
    }
    return (rt_uint32_t)borrow;
}

// 比较两个 512 位整数：返回 1 如果 a>b，0 等号，-1 如果 a<b。
int big_cmp512(const uint512_t a, const uint512_t b) {
    for (int i = 15; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

// 将 256 位整数 a 左移 (word_shift*32 + bit_shift) 位，结果放在 512 位 res 中。
void big512_shl(const uint256_t a, int word_shift, int bit_shift, uint512_t res) {
    // 初始化为 0
    for (int i = 0; i < 16; i++) res[i] = 0;
    if (word_shift < 0 || word_shift > 8) return;
    if (bit_shift == 0) {
        // 整字对齐拷贝
        for (int i = 0; i < 8; i++) {
            res[i + word_shift] = a[i];
        }
    }
    else {
        carry = 0;
        for (int i = 0; i < 8; i++) {
            temp = ((rt_uint64_t)a[i] << bit_shift) | carry;
            res[i + word_shift] = (rt_uint32_t)temp;
            carry = temp >> 32;
        }
        if (word_shift + 8 < 16) {
            res[word_shift + 8] = (rt_uint32_t)carry;
        }
    }
}

// 512 位数 a 模 256 位数 m：将 a 除以 m，返回余数 r（256 位）。
void big_mod(const uint512_t a, const uint256_t m, uint256_t r) {
    // 拷贝 a 到可变数组 rem
    memcpy(rem, a, sizeof(rem));
    // 找到 rem 的最高有效位
    int i;
    for (i = 15; i >= 0; i--) if (rem[i] != 0) break;
    if (i < 0) { // rem 为 0
        memset(r, 0, sizeof(uint256_t));
        return;
    }
    int rem_bit = 32 * i + (31 - clz32(rem[i]));
    // 找到 m 的最高有效位
    int j;
    for (j = 7; j >= 0; j--) if (m[j] != 0) break;
    if (j < 0) { // m 为 0（非法），直接返回 rem 低 256 位
        memcpy(r, rem, 8 * sizeof(rt_uint32_t));
        return;
    }
    int m_bit = 32 * j + (31 - clz32(m[j]));
    if (rem_bit < m_bit) {
        // rem < m，直接返回 rem 低 256 位
        memcpy(r, rem, 8 * sizeof(rt_uint32_t));
        return;
    }
    // 移位-减法长除：当 rem >= m<<shift 时减去之
    while (rem_bit >= m_bit) {
        int shift = rem_bit - m_bit;
        int word_shift = shift / 32, bit_shift = shift % 32;
        big512_shl(m, word_shift, bit_shift, shifted);
        if (big_cmp512(rem, shifted) >= 0) {
            big_sub512(rem, shifted, rem);
            // 更新 rem_bit
            int ii;
            for (ii = 15; ii >= 0; ii--) if (rem[ii] != 0) break;
            if (ii < 0) { // rem 归零
                memset(r, 0, sizeof(uint256_t));
                return;
            }
            rem_bit = 32 * ii + (31 - clz32(rem[ii]));
        }
        else {
            rem_bit--;
        }
    }
    memcpy(r, rem, 8 * sizeof(rt_uint32_t)); // 余数低 256 位
}

// 矩阵乘法 C = A * B （在模 m 下）
void matrix_mul(const Matrix2x2* A, const Matrix2x2* B, const uint256_t m, Matrix2x2* C) {
    // C[0][0] = A00*B00 + A01*B10 (mod m)
    big_mul(A->a[0][0], B->a[0][0], t0);
    big_mod(t0, m, r0);
    big_mul(A->a[0][1], B->a[1][0], t1);
    big_mod(t1, m, r1);
    carry3 = big_add(r0, r1, r0);
    if (carry3 || big_cmp(r0, m) >= 0) big_sub(r0, m, r0);
    memcpy(C->a[0][0], r0, sizeof(r0));
    // C[0][1] = A00*B01 + A01*B11 (mod m)
    big_mul(A->a[0][0], B->a[0][1], t0);
    big_mod(t0, m, r0);
    big_mul(A->a[0][1], B->a[1][1], t1);
    big_mod(t1, m, r1);
    carry3 = big_add(r0, r1, r0);
    if (carry3 || big_cmp(r0, m) >= 0) big_sub(r0, m, r0);
    memcpy(C->a[0][1], r0, sizeof(r0));
    // C[1][0] = A10*B00 + A11*B10 (mod m)
    big_mul(A->a[1][0], B->a[0][0], t0);
    big_mod(t0, m, r0);
    big_mul(A->a[1][1], B->a[1][0], t1);
    big_mod(t1, m, r1);
    carry3 = big_add(r0, r1, r0);
    if (carry3 || big_cmp(r0, m) >= 0) big_sub(r0, m, r0);
    memcpy(C->a[1][0], r0, sizeof(r0));
    // C[1][1] = A10*B01 + A11*B11 (mod m)
    big_mul(A->a[1][0], B->a[0][1], t0);
    big_mod(t0, m, r0);
    big_mul(A->a[1][1], B->a[1][1], t1);
    big_mod(t1, m, r1);
    carry3 = big_add(r0, r1, r0);
    if (carry3 || big_cmp(r0, m) >= 0) big_sub(r0, m, r0);
    memcpy(C->a[1][1], r0, sizeof(r0));
}

// 矩阵幂运算：result = M^exp (mod m)，exp 为 256 位大整数，使用平方-乘法。
void matrix_pow(const Matrix2x2* M, const uint256_t exp, const uint256_t m, Matrix2x2* result) {
    // 初始化 result 为单位阵
    one[0] = 1;
    memset(result->a, 0, sizeof(result->a));
    memcpy(result->a[0][0], one, sizeof(one));
    memcpy(result->a[1][1], one, sizeof(one));
    // 复制底矩阵和指数
    base = *M;
    memcpy(e, exp, sizeof(e));
    // 二进制幂循环
    while (1) {
        if (e[0] & 1) {
            matrix_mul(result, &base, m, &tmp);
            *result = tmp;
        }
        // 检查指数是否为 0
        int is_zero = 1;
        for (int i = 0; i < 8; i++) {
            if (e[i] != 0) { is_zero = 0; break; }
        }
        if (is_zero) break;
        // 指数右移 1
        big_shr1(e, e);
        // 底矩阵自乘
        matrix_mul(&base, &base, m, &tmp2);
        base = tmp2;
    }
}

// 计算 Chebyshev 多项式 T_n(x) mod p，结果放在 Tn, Tn_minus_1 （256 位）。
// 转移矩阵 M = [[2x, -1],[1,0]]，初始向量 [x,1]。
void chebyshev_Tn(const uint256_t *n, const uint256_t *x, const uint256_t *p,
    uint256_t *Tn, uint256_t *Tn_minus_1) {
    // 特殊情况：n = 0
    int is_zero = 1;
    for (int i = 0; i < 8; i++) {
        if ((*n)[i] != 0) { is_zero = 0; break; }
    }
    if (is_zero) {
        memset(*Tn, 0, sizeof(uint256_t));
        memset(*Tn_minus_1, 0, sizeof(uint256_t));
        (*Tn)[0] = 1;  // T0 = 1
        return;
    }
    // n = 1
    int is_one = ((*n)[0] == 1);
    for (int i = 1; i < 8 && is_one; i++) {
        if ((*n)[i] != 0) is_one = 0;
    }
    if (is_one) {
        memcpy(*Tn, *x, sizeof(uint256_t));         // T1 = x
        memset(*Tn_minus_1, 0, sizeof(uint256_t));
        (*Tn_minus_1)[0] = 1;  // T0 = 1
        return;
    }
    // 构造转移矩阵 M
    for (int i = 0; i < 8; i++) {
        t = ((rt_uint64_t)((*x)[i]) << 1) + carry4;
        two_x[i] = (rt_uint32_t)t;
        carry4 = t >> 32;
    }
    if (carry4 || big_cmp(two_x, *p) >= 0) {
        // 若 2x >= p，则减去 p
        big_sub(two_x, *p, two_x);
    }
    memcpy(M.a[0][0], two_x, sizeof(uint256_t));
    // M[0][1] = p - 1 (代表 -1 mod p)
    set_uint256(&one,  0x00000000, 0x00000000, 0x00000000, 0x00000000,
            0x00000000, 0x00000000, 0x00000000, 0x00000000);
    one[0] = 1;
    big_sub(*p, one, tmp256);          // p - 1
    memcpy(M.a[0][1], tmp256, sizeof(uint256_t));
    // M[1][0] = 1, M[1][1] = 0
    memset(M.a[1][0], 0, sizeof(uint256_t)); M.a[1][0][0] = 1;
    memset(M.a[1][1], 0, sizeof(uint256_t));
    // 计算指数 exp = n - 1
    memcpy(exp, *n, sizeof(exp));
    big_sub(exp, one, exp);
    // 矩阵幂
    matrix_pow(&M, exp, *p, &Mpow);
    // 初始向量 v = [x, 1]
    // 结果向量 [Tn, Tn-1] = Mpow * v


    // 计算 Tn = M00*x + M01*1 (mod p)
    big_mul(Mpow.a[0][0], *x, t0);
    big_mod(t0, *p, r0);
    big_mul(Mpow.a[0][1], one, t1);
    big_mod(t1, *p, r1);
    carry4 = big_add(r0, r1, r0);
    if (carry4 || big_cmp(r0, *p) >= 0) big_sub(r0, *p, r0);
    memcpy(*Tn, r0, sizeof(r0));
    // 计算 Tn_minus_1 = M10*x + M11*1 (mod p)
    big_mul(Mpow.a[1][0], *x, t0);
    big_mod(t0, *p, r0);
    big_mul(Mpow.a[1][1], one, t1);
    big_mod(t1, *p, r1);
    carry4 = big_add(r0, r1, r0);
    if (carry4 || big_cmp(r0, *p) >= 0) big_sub(r0, *p, r0);
    memcpy(*Tn_minus_1, r0, sizeof(r0));
}

void print_uint256(const uint256_t a) {
    for (int i = 7; i >= 0; i--) {
        rt_kprintf("%08X", a[i]);
    }
    rt_kprintf("\n");
}

// 初始化 256 位整数为某个 uint64_t 常量（小端）
void set_uint256(uint256_t *x,
    rt_uint32_t limb7, rt_uint32_t limb6, rt_uint32_t limb5, rt_uint32_t limb4,
    rt_uint32_t limb3, rt_uint32_t limb2, rt_uint32_t limb1, rt_uint32_t limb0) {
    (*x)[7] = limb7;
    (*x)[6] = limb6;
    (*x)[5] = limb5;
    (*x)[4] = limb4;
    (*x)[3] = limb3;
    (*x)[2] = limb2;
    (*x)[1] = limb1;
    (*x)[0] = limb0;
}

static uint256_t x, n, p;
static uint256_t Tn, Tn_1;
static rt_thread_t tid1 = RT_NULL;
#define THREAD_PRIORITY         25
#define THREAD_STACK_SIZE       512
#define THREAD_TIMESLICE        5

void cheby_test(void *parameter){
    //rt_uint32_t total,total_1,used,used_1,max_used,max_used_1;
    //rt_memory_info(&total, &used, &max_used);
    set_uint256(&n,0x00000000,0x00000000,0x00000000,0x00000000,
        0x98f104a0,0xbd397d85,0x48cc9cd2,0x782ee4a9);
    // 设置 n = 10
    set_uint256(&x, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0xbdcaf3f5,0xf1cbbf85,0x9ba39225,0x738d42b1);
    // 设置 p = 1000000007（一个常见素数）
    set_uint256(&p, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x959dd95b,0xa0b0ff95,0x63b313db,0xfb224c23);

    // 调用 Chebyshev Tₙ(x) mod p
    chebyshev_Tn(&n, &x, &p, &Tn, &Tn_1);
    //rt_memory_info(&total_1, &used_1, &max_used_1);
    //rt_kprintf("total:%d",total_1-total);
    //rt_kprintf("used:%d",used_1-used);
    //rt_kprintf("max_used:%d",max_used_1-max_used);


    rt_kprintf("Chebyshev T_n(x) mod p where:\n");
    rt_kprintf("x = "); print_uint256(x);
    rt_kprintf("n = "); print_uint256(n);
    rt_kprintf("p = "); print_uint256(p);
    rt_kprintf("Result:\n");
    rt_kprintf("Tn     = "); print_uint256(Tn);
    rt_kprintf("Tn-1   = "); print_uint256(Tn_1);

    return;
}

int rt_test(void){
    rt_uint32_t total,total_1,used,used_1,max_used,max_used_1;
    rt_memory_info(&total, &used, &max_used);
    tid1 = rt_thread_create("thread1",
            cheby_test, RT_NULL, THREAD_STACK_SIZE, THREAD_PRIORITY, THREAD_TIMESLICE);
    /* 如果获得线程控制块，启动这个线程 */
    if (tid1 != RT_NULL)
        rt_thread_startup(tid1);
    chebyshev_Tn(&n, &x, &p, &Tn, &Tn_1);
    rt_memory_info(&total_1, &used_1, &max_used_1);
    rt_kprintf("total:%d",total_1-total);
    rt_kprintf("used:%d",used_1-used);
    rt_kprintf("max_used:%d",max_used_1-max_used);
    return 0;
}
MSH_CMD_EXPORT(rt_test, rt test);
