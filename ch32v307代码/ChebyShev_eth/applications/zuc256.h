/*
 * ZUC-256 stream cipher (key = 32 bytes, IV = 16 or 25 bytes)
 * Lightweight C implementation for RT-Thread + CH32V307.
 */
#ifndef APPLICATIONS_ZUC256_H_
#define APPLICATIONS_ZUC256_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ZUC256_KEY_BYTES      32
#define ZUC256_IV_BYTES_MIN   16
#define ZUC256_IV_BYTES_MAX   25

typedef struct
{
    uint32_t s[16];
    uint32_t R1;
    uint32_t R2;
    uint8_t  key[ZUC256_KEY_BYTES];
    uint8_t  iv[ZUC256_IV_BYTES_MAX];
    uint8_t  iv_len;
} zuc256_ctx_t;

/* return 0 on success, -1 on invalid params */
int zuc256_init(zuc256_ctx_t *ctx, const uint8_t *key, const uint8_t *iv, size_t iv_len);

uint32_t zuc256_keystream_word(zuc256_ctx_t *ctx);
void zuc256_keystream(zuc256_ctx_t *ctx, uint8_t *out, size_t len);

/* XOR keystream with input -> output (can be in-place) */
void zuc256_crypt(zuc256_ctx_t *ctx, const uint8_t *in, uint8_t *out, size_t len);
void zuc256_xor_inplace(zuc256_ctx_t *ctx, uint8_t *buf, size_t len);
int zuc256_demo(int argc, char **argv);

#ifdef __cplusplus
}
#endif

#endif /* APPLICATIONS_ZUC256_H_ */
