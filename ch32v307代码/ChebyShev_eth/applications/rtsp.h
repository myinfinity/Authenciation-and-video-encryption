/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-12-11     Hello       the first version
 */
#ifndef APPLICATIONS_RTSP_H_
#define APPLICATIONS_RTSP_H_
#include <rtthread.h>
#include <stdint.h>
#include <string.h>

#include <sys/socket.h>     /* RT-Thread SAL: BSD socket API */
#include <netinet/in.h>
#include <arpa/inet.h>

#define LISTEN_IP        "0.0.0.0"
#define LISTEN_PORT      5004

#define FORWARD_IP       "192.168.1.116"   /* 改成你的 server IP */
#define FORWARD_PORT     5005             /* 改成 server 回传线程端口 */

#define BUF_SIZE         1600             /* RTP 常见 MTU 下足够；需要更大可调 */
#define THREAD_STACK     4096
#define THREAD_PRIO      18
#define THREAD_TICK      10

/* HEVC I 帧相关 NALU type：19/20=IDR, 21=CRA（按需增减） */
#define HEVC_NAL_IDR_W_RADL  19
#define HEVC_NAL_IDR_N_LP    20
#define HEVC_NAL_CRA_NUT     21
#define HEVC_NAL_FU          49


typedef struct
{
    uint16_t seq;
    uint32_t ts;
    uint32_t ssrc;
    uint8_t  marker;
    uint8_t  pt;
    uint8_t  cc;
    uint8_t  x;
    uint8_t  p;
    uint16_t hdr_len;   /* RTP header + CSRC + EXT 的总长度 */
} rtp_header_t;

int rtp_forward_client_start(void);




#endif /* APPLICATIONS_RTSP_H_ */
