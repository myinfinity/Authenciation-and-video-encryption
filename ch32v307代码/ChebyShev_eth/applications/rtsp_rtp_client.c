/*
 * RTSP + RTP HEVC client + I-frame encryption + UDP forward
 * Platform: RT-Thread / CH32V307
 */

#include <rtthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "zuc256.h"     /* 已验证的 ZUC-256 实现 */

/* ================== 配置 ================== */

#define RTSP_SERVER_IP     "10.25.9.28"
#define RTSP_SERVER_PORT   5543
#define RTSP_URL           "rtsp://10.25.9.28:5543/live"

#define RTP_PORT           5008
#define RTCP_PORT          5009

#define FORWARD_IP         "10.25.9.21"
#define FORWARD_PORT       6000

#define RTP_BUF_SIZE       1600
#define RTP_HEADER_LEN     12
#define SKIP_PAYLOAD_PREFIX 64

/* HEVC I 帧类型 */
#define HEVC_IDR_W_RADL    19
#define HEVC_IDR_N_LP      20
#define HEVC_CRA_NUT       21

/* ========================================= */

/* socket */
static int rtsp_sock = -1;
static int rtp_recv_sock = -1;
static int rtp_send_sock = -1;

/* RTSP state */
static char session_id[64];
static int cseq = 1;

/* 会话密钥（示例） */
static uint8_t g_session_key[32] = {
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11,
    0x11,0x11,0x11,0x11,0x11,0x11,0x11,0x11
};

/* ===== 时延统计 ===== */
static uint64_t g_enc_delay_sum_tick = 0;
static uint32_t g_enc_pkt_cnt = 0;

/* ================== 工具函数 ================== */

static int tcp_connect(const char *ip, int port)
{
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return -1;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port);
    addr.sin_addr.s_addr = inet_addr(ip);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0)
    {
        closesocket(sock);
        return -1;
    }
    return sock;
}

static int udp_bind(int port)
{
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) return -1;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0)
    {
        closesocket(sock);
        return -1;
    }
    return sock;
}

/* ================== RTSP 通信 ================== */

static void rtsp_send(const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    rt_vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    send(rtsp_sock, buf, strlen(buf), 0);
    rt_kprintf("[RTSP] >>>\n%s", buf);
}

static int rtsp_recv(char *buf, int size)
{
    int n = recv(rtsp_sock, buf, size - 1, 0);
    if (n > 0)
    {
        buf[n] = 0;
        rt_kprintf("[RTSP] <<<\n%s", buf);
    }
    return n;
}

/* ================== RTSP 会话 ================== */

static int rtsp_handshake(void)
{
    char buf[1024];

    rtsp_sock = tcp_connect(RTSP_SERVER_IP, RTSP_SERVER_PORT);
    if (rtsp_sock < 0)
    {
        rt_kprintf("RTSP connect failed\n");
        return -1;
    }

    rtsp_send(
        "DESCRIBE %s RTSP/1.0\r\n"
        "CSeq: %d\r\n"
        "Accept: application/sdp\r\n\r\n",
        RTSP_URL, cseq++);
    rtsp_recv(buf, sizeof(buf));

    rtsp_send(
        "SETUP %s/trackID=1 RTSP/1.0\r\n"
        "CSeq: %d\r\n"
        "Transport: RTP/AVP;unicast;client_port=%d-%d\r\n\r\n",
        RTSP_URL, cseq++, RTP_PORT, RTCP_PORT);
    rtsp_recv(buf, sizeof(buf));

    char *p = strstr(buf, "Session:");
    sscanf(p, "Session: %63[^;\r\n]", session_id);
    rt_kprintf("[RTSP] Session = %s\n", session_id);

    rtsp_send(
        "PLAY %s RTSP/1.0\r\n"
        "CSeq: %d\r\n"
        "Session: %s\r\n"
        "Range: npt=0.000-\r\n\r\n",
        RTSP_URL, cseq++, session_id);
    rtsp_recv(buf, sizeof(buf));

    return 0;
}

/* ================== RTP Header 解析 ================== */

static int rtp_header_len(const uint8_t *rtp, int len)
{
    if (len < 12) return -1;

    uint8_t cc = rtp[0] & 0x0F;
    uint8_t x  = (rtp[0] >> 4) & 0x01;
    int hdr_len = 12 + cc * 4;

    if (x)
    {
        uint16_t ext_len = (rtp[hdr_len + 2] << 8) | rtp[hdr_len + 3];
        hdr_len += 4 + ext_len * 4;
    }
    return hdr_len;
}

/* ================== I 帧加密（含时延） ================== */

static void process_rtp_packet(uint8_t *rtp, int len)
{
    rt_tick_t tick_start = rt_tick_get();

    int hdr_len = rtp_header_len(rtp, len);
    if (hdr_len < 0 || len <= hdr_len + 2)
        return;

    uint8_t *payload = rtp + hdr_len;
    int payload_len  = len - hdr_len;
    uint8_t nal_type = (payload[0] >> 1) & 0x3F;

    /* Single NALU */
    if (nal_type != 49)
    {

        if (nal_type != HEVC_IDR_W_RADL &&
            nal_type != HEVC_IDR_N_LP &&
            nal_type != HEVC_CRA_NUT)
            return;

        if (payload_len <= 2 + SKIP_PAYLOAD_PREFIX)
            return;

        uint8_t *enc = payload + 2 + SKIP_PAYLOAD_PREFIX;
        int enc_len  = payload_len - 2 - SKIP_PAYLOAD_PREFIX;

        uint8_t iv[16] = {0};
        memcpy(iv, payload + 2, 16);

        zuc256_ctx_t zuc;
        zuc256_init(&zuc, g_session_key, iv, 16);
        zuc256_xor_inplace(&zuc, enc, enc_len);

        rt_tick_t tick_end = rt_tick_get();
        g_enc_delay_sum_tick += (tick_end - tick_start);
        g_enc_pkt_cnt++;

        rt_kprintf("[ENC] I-frame(single) type=%u delay=%lu us\n",
                   nal_type,
                   (tick_end - tick_start) * 1000000 / RT_TICK_PER_SECOND);
        return;
    }

    /* FU-A */
    if (payload_len < 3)
        return;

    uint8_t fu_header = payload[2];
    uint8_t start = fu_header & 0x80;
    uint8_t orig_type = fu_header & 0x3F;

    if (orig_type != HEVC_IDR_W_RADL &&
        orig_type != HEVC_IDR_N_LP &&
        orig_type != HEVC_CRA_NUT)
        return;

    uint8_t *frag = payload + 3;
    int frag_len  = payload_len - 3;

    static int skip_remain = 0;
    if (start)
        skip_remain = SKIP_PAYLOAD_PREFIX;

    if (skip_remain > 0)
    {
        int skip = (frag_len < skip_remain) ? frag_len : skip_remain;
        frag += skip;
        frag_len -= skip;
        skip_remain -= skip;
    }

    if (frag_len <= 0)
        return;

    uint8_t iv[16] = {0};
    memcpy(iv, payload + 3, 16);

    zuc256_ctx_t zuc;
    zuc256_init(&zuc, g_session_key, iv, 16);
    zuc256_xor_inplace(&zuc, frag, frag_len);

    if (start)
    {
        rt_tick_t tick_end = rt_tick_get();
        g_enc_delay_sum_tick += (tick_end - tick_start);
        g_enc_pkt_cnt++;

        rt_kprintf("[ENC] I-frame(FU-A) type=%u delay=%lu us\n",
                   orig_type,
                   (tick_end - tick_start) * 1000000 / RT_TICK_PER_SECOND);
    }
}

/* ================== RTP 接收 + 转发 ================== */

static void rtp_recv_forward_loop(void)
{
    uint8_t buf[RTP_BUF_SIZE];
    struct sockaddr_in fwd_addr;

    memset(&fwd_addr, 0, sizeof(fwd_addr));
    fwd_addr.sin_family = AF_INET;
    fwd_addr.sin_port   = htons(FORWARD_PORT);
    fwd_addr.sin_addr.s_addr = inet_addr(FORWARD_IP);

    rt_kprintf("[RTP] listen %d, forward to %s:%d\n",
               RTP_PORT, FORWARD_IP, FORWARD_PORT);

    uint32_t cnt = 0;

    while (1)
    {
        int n = recvfrom(rtp_recv_sock, buf, sizeof(buf), 0, RT_NULL, RT_NULL);
        if (n <= 0) continue;

        uint16_t seq = (buf[2] << 8) | buf[3];
        uint32_t ts  = (buf[4] << 24) | (buf[5] << 16) |
                       (buf[6] << 8) | buf[7];

        process_rtp_packet(buf, n);

        sendto(rtp_send_sock, buf, n, 0,
               (struct sockaddr *)&fwd_addr, sizeof(fwd_addr));

        cnt++;
        if ((cnt % 100) == 0)
        {
            rt_kprintf("[RTP] fwd pkt=%lu seq=%u ts=%u len=%d\n",
                       cnt, seq, ts, n);

            if (g_enc_pkt_cnt > 0)
            {
                uint32_t avg_us =
                    (g_enc_delay_sum_tick * 1000000) /
                    (RT_TICK_PER_SECOND * g_enc_pkt_cnt);

                rt_kprintf("[ENC] avg encrypt delay = %lu us (%lu I-frames)\n",
                           avg_us, g_enc_pkt_cnt);
            }
        }
    }
}

/* ================== 线程入口 ================== */

static void rtsp_rtp_thread(void *param)
{
    if (rtsp_handshake() != 0)
        return;

    rtp_recv_sock = udp_bind(RTP_PORT);
    rtp_send_sock = socket(AF_INET, SOCK_DGRAM, 0);

    rtp_recv_forward_loop();
}

int rtsp_rtp_start(int argc, char **argv)
{
    rt_thread_t tid = rt_thread_create(
        "rtsp_rtp",
        rtsp_rtp_thread,
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
MSH_CMD_EXPORT(rtsp_rtp_start, RTSP RTP receive + I-frame encrypt + forward);
