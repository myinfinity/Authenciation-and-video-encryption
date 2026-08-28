/*
 * RTP UDP Receiver (Decrypt Client)
 * Platform: RT-Thread / CH32V307
 *
 * Function:
 *  - Receive RTP packets forwarded by encrypt client
 *  - Decrypt HEVC I-frames (IDR/CRA) using ZUC-256
 *  - Measure decryption latency (tick-based)
 */

#include <rtthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "zuc256.h"   /* 与加密端完全一致的 ZUC-256 实现 */

/* ================= 配置 ================= */

#define LOCAL_RTP_PORT        6000
#define RTP_BUF_SIZE          1600

#define RTP_HEADER_LEN        12
#define SKIP_PAYLOAD_PREFIX  64   /* 必须与加密端一致 */

/* HEVC I 帧 NALU 类型 */
#define HEVC_IDR_W_RADL       19
#define HEVC_IDR_N_LP         20
#define HEVC_CRA_NUT          21

/* ======================================= */

static int rtp_sock = -1;

/* ===== 会话密钥（必须与加密端完全一致）===== */
static uint8_t g_session_key[32] =
{
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11
};

/* ===== 解密时延统计 ===== */
static uint64_t g_dec_delay_sum_tick = 0;
static uint32_t g_dec_frame_cnt      = 0;

/* ================= 工具函数 ================= */

static inline uint8_t hevc_nalu_type(const uint8_t *nalu)
{
    /* HEVC: nal_unit_type = (byte >> 1) & 0x3F */
    return (nalu[0] >> 1) & 0x3F;
}

/* ================= 解密核心 ================= */

static void decrypt_rtp_packet(uint8_t *rtp, int len)
{
    if (len <= RTP_HEADER_LEN + 2)
        return;

    uint8_t *payload = rtp + RTP_HEADER_LEN;
    int payload_len  = len - RTP_HEADER_LEN;

    uint8_t nalu_type = hevc_nalu_type(payload);

    /* 仅对 I 帧执行解密 */
    /*
    if (nalu_type != HEVC_IDR_W_RADL &&
        nalu_type != HEVC_IDR_N_LP   &&
        nalu_type != HEVC_CRA_NUT)
    {
        return;
    }*/

    if (payload_len <= 2 + SKIP_PAYLOAD_PREFIX)
        return;

    uint8_t *dec_start = payload + 2 + SKIP_PAYLOAD_PREFIX;
    int dec_len = payload_len - 2 - SKIP_PAYLOAD_PREFIX;

    /* ===== IV 构造（与加密端保持一致）===== */
    uint8_t iv[16] = {0};
    memcpy(iv, payload + 2, 16);

    /* ===== 解密时延测量开始 ===== */
    rt_tick_t tick_start = rt_tick_get();

    zuc256_ctx_t zuc;
    zuc256_init(&zuc, g_session_key, iv, 16);
    zuc256_xor_inplace(&zuc, dec_start, dec_len);

    rt_tick_t tick_end = rt_tick_get();
    /* ===== 解密时延测量结束 ===== */

    g_dec_delay_sum_tick += (tick_end - tick_start);
    g_dec_frame_cnt++;

    rt_kprintf("[DEC] I-frame decrypted type=%u delay=%lu us\n",
               nalu_type,
               (tick_end - tick_start) * 1000000 / RT_TICK_PER_SECOND);
}

/* ================= RTP 接收循环 ================= */

static void rtp_receive_loop(void)
{
    uint8_t buf[RTP_BUF_SIZE];

    rt_kprintf("[RTP-RECV] listening on UDP port %d\n", LOCAL_RTP_PORT);

    uint32_t pkt_cnt = 0;

    while (1)
    {
        int n = recvfrom(rtp_sock, buf, sizeof(buf), 0,
                         RT_NULL, RT_NULL);
        if (n <= 0)
            continue;

        /* ===== RTP Header 解析（调试用）===== */
        uint8_t  pt  = buf[1] & 0x7F;
        uint16_t seq = (buf[2] << 8) | buf[3];
        uint32_t ts  = (buf[4] << 24) | (buf[5] << 16) |
                       (buf[6] << 8) | buf[7];

        /* ===== I 帧解密 ===== */
        decrypt_rtp_packet(buf, n);

        pkt_cnt++;
        if ((pkt_cnt % 100) == 0)
        {
            rt_kprintf("[RTP] fwd pkt=%lu seq=%u ts=%u len=%d\n",
                       pkt_cnt, seq, ts, n);

            if (g_dec_frame_cnt > 0)
            {
                uint32_t avg_us =
                    (g_dec_delay_sum_tick * 1000000) /
                    (RT_TICK_PER_SECOND * g_dec_frame_cnt);

                rt_kprintf("[DEC] avg decrypt delay = %lu us (%lu I-frames)\n",
                           avg_us, g_dec_frame_cnt);
            }
        }
    }
}

/* ================= 线程入口 ================= */

static void rtp_receiver_thread(void *param)
{


    rtp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (rtp_sock < 0)
    {
        rt_kprintf("RTP socket create failed\n");
        return;
    }

    struct sockaddr_in local;
    memset(&local, 0, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_port   = htons(LOCAL_RTP_PORT);
    local.sin_addr.s_addr = INADDR_ANY;

    if (bind(rtp_sock, (struct sockaddr *)&local, sizeof(local)) < 0)
    {
        rt_kprintf("RTP bind failed\n");
        closesocket(rtp_sock);
        return;
    }

    rtp_receive_loop();
}

/* ================= msh 命令 ================= */

int rtp_receiver_start(int argc, char **argv)
{


    rt_thread_t tid = rt_thread_create(
        "rtp_dec",
        rtp_receiver_thread,
        RT_NULL,
        4096,
        20,
        10);

    if (tid)
    {
        rt_thread_startup(tid);
        return 0;
    }
    return -1;
}
MSH_CMD_EXPORT(rtp_receiver_start, RTP UDP receiver + I-frame decrypt + latency);
