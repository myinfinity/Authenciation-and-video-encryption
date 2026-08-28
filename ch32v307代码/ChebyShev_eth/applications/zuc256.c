/*
 * ZUC-256 stream cipher (key = 32 bytes, IV = 16 or 25 bytes)
 * Portable C implementation for RT-Thread + CH32V307.
 */
#include "zuc256.h"
#include <rtthread.h>
#include <string.h>

#define P31 0x7FFFFFFF

static const uint8_t d2[16] =
{
    0x64, 0x43, 0x7B, 0x2A, 0x11, 0x05, 0x51, 0x42,
    0x1A, 0x31, 0x18, 0x66, 0x14, 0x2E, 0x01, 0x5C
};

static const uint8_t d3[16] =
{
    0x22, 0x2F, 0x24, 0x2A, 0x6D, 0x40, 0x40, 0x40,
    0x40, 0x40, 0x40, 0x40, 0x40, 0x52, 0x10, 0x30
};

static const uint8_t s0[256] =
{
0x3E,0x72,0x5B,0x47,0xCA,0xE0,0x00,0x33,0x04,0xD1,0x54,0x98,0x09,0xB9,0x6D,0xCB,
0x8F,0xEA,0x20,0xAB,0x6A,0x41,0x7C,0x11,0xCF,0x7E,0xC7,0x7B,0x73,0xBC,0x5C,0x6F,
0x45,0x2E,0x33,0x67,0x24,0x4F,0x6B,0x48,0x8A,0x0F,0x5F,0xF7,0x1A,0xA2,0xF3,0x91,
0xEB,0x2D,0x0E,0x8B,0xA9,0x0C,0x86,0x1B,0xAE,0xC4,0x10,0x6C,0xF0,0x0A,0x5A,0xE9,
0x3D,0x46,0x8E,0xB4,0xE5,0x37,0xE7,0x0B,0xE8,0x2F,0x2B,0xA7,0x3B,0xD4,0x9D,0xFC,
0x7D,0x3F,0x29,0xB7,0x99,0x2C,0x9A,0xE3,0x9E,0xC6,0x5D,0x34,0x1C,0x9B,0xAF,0x1E,
0x3A,0x77,0x70,0xF1,0x39,0xAC,0xD0,0x1D,0x5E,0x62,0xCE,0x1F,0x8C,0xB3,0xE1,0xA5,
0x27,0x4B,0x2A,0xFD,0xDB,0x15,0xA4,0x4E,0x95,0xA0,0x14,0xF5,0x4A,0x61,0x83,0x38,
0x6E,0xD7,0x84,0x4D,0x1B,0x7F,0xC2,0xDC,0xEF,0x8D,0xAD,0xD8,0x26,0xB0,0xD6,0x93,
0x60,0x88,0xA8,0xBA,0xC5,0x21,0x9C,0xBD,0x92,0x16,0xF9,0xA6,0xFB,0xC1,0x0D,0x56,
0x44,0x85,0x57,0x12,0xC3,0xC9,0x90,0xEF,0x58,0x6F,0x4C,0x43,0xB6,0xD9,0x68,0x82,
0x30,0x52,0x71,0x5C,0x9F,0x36,0x64,0xA1,0x94,0xEA,0x13,0x2D,0x22,0xAD,0x97,0xB1,
0x79,0xF2,0x17,0x63,0xB8,0xD5,0x89,0x4C,0x59,0x23,0x25,0x66,0x08,0xD2,0x35,0xF8,
0x19,0x01,0x46,0x87,0xA3,0x55,0x96,0x69,0x42,0x0F,0xE2,0xCB,0x32,0x78,0xA9,0x7A,
0x6A,0xA4,0xFB,0xFB,0xE4,0x2C,0xC8,0xD3,0x80,0x05,0xC0,0x31,0xB5,0xF4,0x40,0x0D,
0x75,0x14,0xC7,0xD1,0xB2,0xF6,0x65,0x03,0xB9,0x09,0x7E,0x02,0x11,0x6D,0xA0,0x2E
};

static const uint8_t s1[256] =
{
0x55,0xC2,0x63,0x71,0x3B,0xC8,0x47,0x86,0x9F,0x3C,0xDA,0x5B,0x29,0xAA,0xFD,0x77,
0x8C,0xC5,0x94,0x0C,0xA6,0x1A,0x13,0x00,0xE3,0xA8,0x16,0x72,0x40,0xF9,0xF8,0x42,
0x44,0x26,0x68,0x96,0x81,0xD9,0x45,0x3E,0x10,0x76,0xC6,0xA7,0x8B,0x39,0x43,0xE1,
0x3A,0xB5,0x56,0x2A,0xC0,0x6D,0xB3,0x05,0x22,0x66,0xBF,0xDC,0x0B,0xFA,0x62,0x48,
0x24,0x91,0x8A,0x4B,0x9A,0x86,0xE7,0x1F,0x6B,0xD6,0xE6,0x18,0x30,0x0D,0xAB,0xF1,
0xA2,0x8D,0x6F,0x98,0x0A,0x7B,0x0E,0xC1,0xEF,0xDE,0xDB,0x1D,0xA4,0x9D,0x2F,0x5F,
0xB4,0xAF,0xEC,0x07,0xE2,0x67,0xF0,0xF6,0x4F,0x2B,0xBD,0xB8,0x4E,0x93,0x92,0x1B,
0x37,0xB0,0x28,0x60,0x64,0x15,0xCD,0xC3,0xF4,0x9C,0x36,0x1C,0xA5,0xD0,0x5A,0x7F,
0xDB,0x21,0x50,0xCF,0x04,0x88,0x6A,0x8E,0x9B,0xB6,0x20,0x14,0xE0,0x4A,0x6C,0x5D,
0x46,0x34,0x2D,0x49,0x7C,0x3D,0x85,0xA7,0x99,0x0F,0xF2,0x33,0x59,0x82,0x3F,0xE4,
0xC9,0xC7,0x97,0xA9,0xEC,0x3E,0x01,0xDD,0xC4,0x41,0x31,0x5C,0x7A,0x78,0x95,0x6E,
0x27,0xAB,0x35,0x52,0x17,0xBE,0x02,0x4C,0x6F,0xE8,0xA1,0xBD,0x12,0x0B,0xC5,0xCE,
0xE9,0x7D,0x1E,0xA3,0x08,0xB1,0x65,0x32,0xB7,0xF3,0xF5,0xC0,0x87,0xFE,0x89,0x25,
0x5E,0xC8,0x2C,0x51,0x4D,0xF7,0x61,0x54,0xAE,0x9E,0x11,0xD8,0x3B,0x73,0xD5,0xA0,
0x5B,0xD1,0xE5,0xF8,0x6D,0x43,0x03,0x96,0x38,0x4B,0x44,0x29,0x19,0xCA,0xB2,0xB9,
0x84,0x71,0x8F,0x53,0x2A,0x9F,0x57,0x0C,0xA6,0x16,0x75,0x40,0x2E,0xAD,0x09,0xD4
};

static inline uint32_t rol32(uint32_t x, uint8_t n)
{
    return (x << n) | (x >> (32 - n));
}

static inline uint32_t add31(uint32_t a, uint32_t b)
{
    uint32_t x = a + b;
    x = x + (x >> 31);
    x &= P31;
    return x;
}

static inline uint32_t mul31(uint32_t a, uint8_t n)
{
    return ((a << n) | (a >> (31 - n))) & P31;
}

static inline uint32_t L1(uint32_t x)
{
    return x ^ rol32(x, 2) ^ rol32(x, 10) ^ rol32(x, 18) ^ rol32(x, 24);
}

static inline uint32_t L2(uint32_t x)
{
    return x ^ rol32(x, 8) ^ rol32(x, 14) ^ rol32(x, 22) ^ rol32(x, 30);
}

static inline uint32_t S_func(uint32_t x)
{
    uint8_t b0 = s1[x & 0xFF];
    uint8_t b1 = s0[(x >> 8) & 0xFF];
    uint8_t b2 = s1[(x >> 16) & 0xFF];
    uint8_t b3 = s0[(x >> 24) & 0xFF];
    return ((uint32_t)b0) | ((uint32_t)b1 << 8) | ((uint32_t)b2 << 16) | ((uint32_t)b3 << 24);
}

static inline uint32_t load2(uint8_t a, uint8_t b, uint8_t c, uint8_t d)
{
    return ((uint32_t)a << 23 | ((uint32_t)(b & 0x7F) << 16) | ((uint32_t)c << 8) | (uint32_t)d) & P31;
}

static void bit_reorg(const zuc256_ctx_t *ctx, uint32_t *x0, uint32_t *x1, uint32_t *x2, uint32_t *x3)
{
    const uint32_t *s = ctx->s;
    *x0 = ((s[15] << 1) & 0xFFFF0000) | (s[14] & 0xFFFF);
    *x1 = ((s[11] << 16) & 0xFFFF0000) | ((s[9] >> 15) & 0xFFFF);
    *x2 = ((s[7] << 16) & 0xFFFF0000) | ((s[5] >> 15) & 0xFFFF);
    *x3 = ((s[2] << 16) & 0xFFFF0000) | ((s[0] >> 15) & 0xFFFF);
}

static uint32_t F_func(zuc256_ctx_t *ctx, uint32_t x0, uint32_t x1, uint32_t x2)
{
    uint32_t w  = (x0 ^ ctx->R1) + ctx->R2;
    uint32_t w1 = ctx->R1 + x1;
    uint32_t w2 = ctx->R2 ^ x2;

    uint32_t tmp = ((w1 << 16) | (w2 >> 16));
    tmp = L1(tmp);
    ctx->R1 = S_func(tmp);

    uint32_t tmp2 = ((w2 << 16) | (w1 >> 16));
    tmp2 = L2(tmp2);
    ctx->R2 = S_func(tmp2);

    return w;
}

static void lfsr_init(zuc256_ctx_t *ctx, uint32_t u)
{
    uint32_t *s = ctx->s;
    uint32_t s0  = s[0];
    uint32_t s16 = add31(s0, mul31(s0, 8));
    s16 = add31(s16, mul31(s[4], 20));
    s16 = add31(s16, mul31(s[10], 21));
    s16 = add31(s16, mul31(s[13], 17));
    s16 = add31(s16, mul31(s[15], 15));
    s16 = add31(s16, u);
    memmove(s, s + 1, 15 * sizeof(uint32_t));
    s[15] = s16;
}

static void lfsr_work(zuc256_ctx_t *ctx)
{
    uint32_t *s = ctx->s;
    uint32_t s0  = s[0];
    uint32_t s16 = add31(s0, mul31(s0, 8));
    s16 = add31(s16, mul31(s[4], 20));
    s16 = add31(s16, mul31(s[10], 21));
    s16 = add31(s16, mul31(s[13], 17));
    s16 = add31(s16, mul31(s[15], 15));
    memmove(s, s + 1, 15 * sizeof(uint32_t));
    s[15] = s16;
}

static void zuc256_init_state(zuc256_ctx_t *ctx, const uint8_t *key, const uint8_t *iv, size_t iv_len)
{
    const uint8_t *D = (iv_len == 16) ? d2 : d3;

    if (iv_len == 16)
    {
        ctx->s[0]  = load2(key[0],  D[0],  key[16], key[24]);
        ctx->s[1]  = load2(key[1],  D[1],  key[17], key[25]);
        ctx->s[2]  = load2(key[2],  D[2],  key[18], key[26]);
        ctx->s[3]  = load2(key[3],  D[3],  key[19], key[27]);
        ctx->s[4]  = load2(key[4],  D[4],  key[20], key[28]);
        ctx->s[5]  = load2(key[5],  D[5],  key[21], key[29]);
        ctx->s[6]  = load2(key[6],  D[6],  key[22], key[30]);
        ctx->s[7]  = load2(key[7],  D[7],  iv[0],   iv[8]);
        ctx->s[8]  = load2(key[8],  D[8],  iv[1],   iv[9]);
        ctx->s[9]  = load2(key[9],  D[9],  iv[2],   iv[10]);
        ctx->s[10] = load2(key[10], D[10], iv[3],   iv[11]);
        ctx->s[11] = load2(key[11], D[11], iv[4],   iv[12]);
        ctx->s[12] = load2(key[12], D[12], iv[5],   iv[13]);
        ctx->s[13] = load2(key[13], D[13], iv[6],   iv[14]);
        ctx->s[14] = load2(key[14], D[14], iv[7],   iv[15]);
        ctx->s[15] = load2(key[15], D[15], key[23], key[31]);
    }
    else
    {
        /* 184-bit IV (25 bytes) */
        #define OR_D_IV(d_const, small_iv) ((uint8_t)((d_const) | ((small_iv) & 0x3F)))
        ctx->s[0]  = load2(key[0],  D[0],  key[21], key[16]);
        ctx->s[1]  = load2(key[1],  D[1],  key[22], key[17]);
        ctx->s[2]  = load2(key[2],  D[2],  key[23], key[18]);
        ctx->s[3]  = load2(key[3],  D[3],  key[24], key[19]);
        ctx->s[4]  = load2(key[4],  D[4],  key[25], key[20]);
        ctx->s[5]  = load2(iv[0],   OR_D_IV(D[5],  iv[17]), key[5],  key[26]);
        ctx->s[6]  = load2(iv[1],   OR_D_IV(D[6],  iv[18]), key[6],  key[27]);
        ctx->s[7]  = load2(iv[10],  OR_D_IV(D[7],  iv[19]), key[7],  iv[2]);
        ctx->s[8]  = load2(key[8],  OR_D_IV(D[8],  iv[20]), iv[3],   iv[11]);
        ctx->s[9]  = load2(key[9],  OR_D_IV(D[9],  iv[21]), iv[12],  iv[4]);
        ctx->s[10] = load2(iv[5],   OR_D_IV(D[10], iv[22]), key[10], key[28]);
        ctx->s[11] = load2(key[11], OR_D_IV(D[11], iv[23]), iv[6],   iv[13]);
        ctx->s[12] = load2(key[12], OR_D_IV(D[12], iv[24]), iv[7],   iv[14]);
        ctx->s[13] = load2(key[13], D[13], iv[5], iv[8]);
        uint8_t k31_hi = (key[31] >> 4) & 0x0F;
        uint8_t k31_lo = key[31] & 0x0F;
        ctx->s[14] = load2(key[14], (uint8_t)(D[14] | k31_hi), iv[16], iv[9]);
        ctx->s[15] = load2(key[15], (uint8_t)(D[15] | k31_lo), key[30], key[29]);
        #undef OR_D_IV
    }

    ctx->R1 = 0;
    ctx->R2 = 0;

    for (int i = 0; i < 32; ++i)
    {
        uint32_t x0, x1, x2, x3;
        bit_reorg(ctx, &x0, &x1, &x2, &x3);
        uint32_t w = F_func(ctx, x0, x1, x2);
        w = (w >> 1) & P31;
        lfsr_init(ctx, w);
    }

    {
        uint32_t x0, x1, x2, x3;
        bit_reorg(ctx, &x0, &x1, &x2, &x3);
        (void)F_func(ctx, x0, x1, x2);
        lfsr_work(ctx);
    }
}

int zuc256_init(zuc256_ctx_t *ctx, const uint8_t *key, const uint8_t *iv, size_t iv_len)
{
    if (!ctx || !key || !iv)
        return -1;
    if (iv_len != ZUC256_IV_BYTES_MIN && iv_len != ZUC256_IV_BYTES_MAX) return -1;

    memcpy(ctx->key, key, ZUC256_KEY_BYTES);
    memcpy(ctx->iv, iv, iv_len);
    ctx->iv_len = (uint8_t)iv_len;
    zuc256_init_state(ctx, ctx->key, ctx->iv, iv_len);
    return 0;
}

uint32_t zuc256_keystream_word(zuc256_ctx_t *ctx)
{
    uint32_t x0, x1, x2, x3;
    bit_reorg(ctx, &x0, &x1, &x2, &x3);
    uint32_t w = F_func(ctx, x0, x1, x2);
    uint32_t z = w ^ x3;
    lfsr_work(ctx);
    return z;
}

void zuc256_keystream(zuc256_ctx_t *ctx, uint8_t *out, size_t len)
{
    size_t produced = 0;
    while (produced < len)
    {
        uint32_t w = zuc256_keystream_word(ctx);
        uint8_t tmp[4];
        tmp[0] = (uint8_t)(w >> 24);
        tmp[1] = (uint8_t)(w >> 16);
        tmp[2] = (uint8_t)(w >> 8);
        tmp[3] = (uint8_t)(w);
        size_t chunk = (len - produced) > 4 ? 4 : (len - produced);
        memcpy(out + produced, tmp, chunk);
        produced += chunk;
    }
}

void zuc256_crypt(zuc256_ctx_t *ctx, const uint8_t *in, uint8_t *out, size_t len)
{
    size_t produced = 0;
    while (produced < len)
    {
        uint32_t w = zuc256_keystream_word(ctx);
        uint8_t ks[4];
        ks[0] = (uint8_t)(w >> 24);
        ks[1] = (uint8_t)(w >> 16);
        ks[2] = (uint8_t)(w >> 8);
        ks[3] = (uint8_t)(w);
        for (size_t i = 0; i < 4 && produced < len; ++i)
        {
            out[produced] = in[produced] ^ ks[i];
            produced++;
        }
    }
}

void zuc256_xor_inplace(zuc256_ctx_t *ctx, uint8_t *buf, size_t len)
{
    zuc256_crypt(ctx, buf, buf, len);
}

static void zuc_dump_hex(const char *label, const uint8_t *buf, size_t len)
{
    rt_kprintf("%s:", label);
    for (size_t i = 0; i < len; ++i)
    {
        if ((i % 16) == 0) rt_kprintf("\n ");
        rt_kprintf("%02X ", buf[i]);
    }
    rt_kprintf("\n");
}

/* Simple RT-Thread msh demo: encrypt + decrypt a small buffer */
int zuc256_demo(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    static const uint8_t key[ZUC256_KEY_BYTES] =
    {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
        0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
        0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F
    };

    static const uint8_t iv[ZUC256_IV_BYTES_MIN] =
    {
        0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF
    };

    static const uint8_t plaintext[] = "Hello ZUC-256 stream cipher!";
    const size_t data_len = sizeof(plaintext) - 1; /* skip trailing '\0' */
    uint8_t ciphertext[sizeof(plaintext) - 1];
    uint8_t decrypted[sizeof(plaintext)];

    zuc256_ctx_t ctx;
    if (zuc256_init(&ctx, key, iv, sizeof(iv)) != 0)
    {
        rt_kprintf("zuc256 init failed\n");
        return -RT_ERROR;
    }

    zuc256_crypt(&ctx, plaintext, ciphertext, data_len);

    /* re-init to reset keystream before decrypting */
    if (zuc256_init(&ctx, key, iv, sizeof(iv)) != 0)
    {
        rt_kprintf("zuc256 re-init failed\n");
        return -RT_ERROR;
    }
    zuc256_crypt(&ctx, ciphertext, decrypted, data_len);
    decrypted[data_len] = '\0';

    rt_kprintf("zuc256 demo:\n");
    rt_kprintf("Plaintext: %s\n", plaintext);
    zuc_dump_hex("Key", key, sizeof(key));
    zuc_dump_hex("IV", iv, sizeof(iv));
    zuc_dump_hex("Ciphertext", ciphertext, data_len);
    zuc_dump_hex("Decrypted", decrypted, data_len);
    rt_kprintf("Decrypted text: %s\n", decrypted);

    return RT_EOK;
}
MSH_CMD_EXPORT(zuc256_demo, zuc256 demo encrypt/decrypt);
