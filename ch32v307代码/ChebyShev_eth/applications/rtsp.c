
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#include <rtthread.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <finsh.h>

#define socket_t int
#define CLOSESOCK closesocket

#define DEFAULT_LISTEN_IP "10.25.9.198"   // local client IP to bind for incoming RTP
#define DEFAULT_LISTEN_PORT 5008
#define DEFAULT_FORWARD_IP "10.25.9.113" // server IP to forward the same RTP packets
#define DEFAULT_FORWARD_PORT 5006
#define BUFFER_SIZE 65535
#define LOG_EVERY 100        // reduce log cost
#define WRITE_OUTPUT 0       // set 0 to disable local dump
#define OUTPUT_FILE "output.265"
#define MAX_FU_BUFFERS 8

struct rtp_cfg {
    char listen_ip[32];
    uint16_t listen_port;
    char forward_ip[32];
    uint16_t forward_port;
};

struct RtpHeader {
    uint16_t seq;
    uint32_t timestamp;
    uint32_t ssrc;
    uint8_t marker;
};

struct FuBuffer {
    int active;
    uint32_t timestamp;
    uint8_t *data;
    size_t size;
    size_t capacity;
};


static void fu_buffer_reset(struct FuBuffer *buf) {
    if (!buf) return;
    free(buf->data);
    buf->data = NULL;
    buf->size = 0;
    buf->capacity = 0;
    buf->active = 0;
    buf->timestamp = 0;
}

static int fu_buffer_reserve(struct FuBuffer *buf, size_t need) {
    if (buf->capacity >= need) return 1;
    size_t new_cap = buf->capacity ? buf->capacity * 2 : 2048;
    while (new_cap < need) new_cap *= 2;
    uint8_t *p = (uint8_t *)realloc(buf->data, new_cap);
    if (!p) return 0;
    buf->data = p;
    buf->capacity = new_cap;
    return 1;
}

static struct FuBuffer *fu_buffer_get(struct FuBuffer *pool, uint32_t ts, int create_if_missing) {
    for (int i = 0; i < MAX_FU_BUFFERS; ++i) {
        if (pool[i].active && pool[i].timestamp == ts) return &pool[i];
    }
    if (!create_if_missing) return NULL;
    for (int i = 0; i < MAX_FU_BUFFERS; ++i) {
        if (!pool[i].active) {
            pool[i].active = 1;
            pool[i].timestamp = ts;
            pool[i].size = 0;
            pool[i].capacity = 0;
            pool[i].data = NULL;
            return &pool[i];
        }
    }
    fu_buffer_reset(&pool[0]);
    pool[0].active = 1;
    pool[0].timestamp = ts;
    return &pool[0];
}

static int parse_rtp(const uint8_t *packet, size_t len, struct RtpHeader *hdr,
                     const uint8_t **payload, size_t *payload_len) {
    if (len < 12) return 0;
    hdr->seq = (uint16_t)((packet[2] << 8) | packet[3]);
    hdr->timestamp = ((uint32_t)packet[4] << 24) | ((uint32_t)packet[5] << 16) |
                     ((uint32_t)packet[6] << 8) | (uint32_t)packet[7];
    hdr->ssrc = ((uint32_t)packet[8] << 24) | ((uint32_t)packet[9] << 16) |
                ((uint32_t)packet[10] << 8) | (uint32_t)packet[11];
    hdr->marker = (packet[1] >> 7) & 0x1;
    *payload = packet + 12;
    *payload_len = len - 12;
    return 1;
}

static int fu_process(const uint8_t *payload, size_t payload_len, const struct RtpHeader *rtp,
                      struct FuBuffer *pool, uint8_t **out_nalu, size_t *out_len) {
    *out_nalu = NULL;
    *out_len = 0;
    if (payload_len < 3) return 0;
    uint16_t payload_hdr = ((uint16_t)payload[0] << 8) | payload[1];
    uint8_t nalu_type = (payload_hdr >> 9) & 0x3F;
    if (nalu_type != 49) return 0;
    uint8_t fu_header = payload[2];
    int is_start = (fu_header & 0x80) != 0;
    int is_end = (fu_header & 0x40) != 0;
    uint8_t orig_type = fu_header & 0x3F;
    struct FuBuffer *buf = fu_buffer_get(pool, rtp->timestamp, is_start);
    if (!buf) return 0;
    if (is_start) {
        buf->size = 0;
        uint8_t f = (payload_hdr >> 15) & 0x01;
        uint8_t layer_id = (payload_hdr >> 3) & 0x3F;
        uint8_t tid = payload_hdr & 0x07;
        uint16_t orig_hdr = (uint16_t)((f << 15) | (orig_type << 9) | (layer_id << 3) | tid);
        size_t needed = buf->size + 6;
        if (!fu_buffer_reserve(buf, needed)) return 0;
        buf->data[buf->size++] = 0x00;
        buf->data[buf->size++] = 0x00;
        buf->data[buf->size++] = 0x00;
        buf->data[buf->size++] = 0x01;
        buf->data[buf->size++] = (uint8_t)((orig_hdr >> 8) & 0xFF);
        buf->data[buf->size++] = (uint8_t)(orig_hdr & 0xFF);
    } else if (!buf->active) {
        return 0;
    }
    size_t add_len = payload_len - 3;
    if (!fu_buffer_reserve(buf, buf->size + add_len)) return 0;
    memcpy(buf->data + buf->size, payload + 3, add_len);
    buf->size += add_len;
    if (is_end) {
        uint8_t *result = (uint8_t *)malloc(buf->size);
        if (!result) {
            fu_buffer_reset(buf);
            return 0;
        }
        memcpy(result, buf->data, buf->size);
        *out_nalu = result;
        *out_len = buf->size;
        fu_buffer_reset(buf);
        rt_kprintf("[CLIENT] assembled NALU ts=%u size=%zu type=%u\n", rtp->timestamp, *out_len, orig_type);
        return 1;
    }
    return 0;
}

static int setup_socket(socket_t *sock, const char *ip, uint16_t port, int bind_socket) {
    *sock = (socket_t)socket(AF_INET, SOCK_DGRAM, 0);
    if (*sock == (socket_t)-1) return 0;
    int opt = 1;
    setsockopt(*sock, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt));
    int buf_sz = 512 * 1024;
    setsockopt(*sock, SOL_SOCKET, SO_RCVBUF, (const char *)&buf_sz, sizeof(buf_sz));
    setsockopt(*sock, SOL_SOCKET, SO_SNDBUF, (const char *)&buf_sz, sizeof(buf_sz));
    if (bind_socket) {
        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        addr.sin_addr.s_addr = inet_addr(ip);
        if (bind(*sock, (struct sockaddr *)&addr, sizeof(addr)) != 0) return 0;
    }
    return 1;
}

static void rtp_client_loop(const struct rtp_cfg *cfg) {
    socket_t recv_sock, forward_sock;
    if (!setup_socket(&recv_sock, cfg->listen_ip, cfg->listen_port, 1)) {
        rt_kprintf("Failed to create/bind receive socket\n");
        return;
    }
    if (!setup_socket(&forward_sock, cfg->forward_ip, cfg->forward_port, 0)) {
        rt_kprintf("Failed to create forward socket\n");
        CLOSESOCK(recv_sock);
        return;
    }
    struct hostent *host = gethostbyname(cfg->forward_ip);
    if (!host) {
        rt_kprintf("Resolve forward host failed\n");
        CLOSESOCK(recv_sock);
        CLOSESOCK(forward_sock);
        return;
    }
    struct sockaddr_in forward_addr;
    memset(&forward_addr, 0, sizeof(forward_addr));
    forward_addr.sin_family = AF_INET;
    forward_addr.sin_port = htons(cfg->forward_port);
    forward_addr.sin_addr = *((struct in_addr *)host->h_addr);
    rt_kprintf("[CLIENT] listen on %s:%d, forward to %s:%d\n",
               cfg->listen_ip, cfg->listen_port, cfg->forward_ip, cfg->forward_port);
    uint8_t buffer[BUFFER_SIZE];
    uint32_t pkt_count = 0;
    struct FuBuffer fu_pool[MAX_FU_BUFFERS];
    memset(fu_pool, 0, sizeof(fu_pool));
    FILE *out_file = NULL;
    while (1) {
        struct sockaddr_in from_addr;
        socklen_t from_len = sizeof(from_addr);
        int got = recvfrom(recv_sock, (char *)buffer, BUFFER_SIZE, 0,
                           (struct sockaddr *)&from_addr, &from_len);
        if (got <= 0) {
            continue;
        }
        pkt_count++;
        if (pkt_count % LOG_EVERY == 0) {
            char ipbuf[32];
            inet_ntop(AF_INET, &from_addr.sin_addr, ipbuf, sizeof(ipbuf));
            rt_kprintf("[CLIENT] pkt=%lu recv %d bytes from %s:%d\n",
                       pkt_count, got, ipbuf, ntohs(from_addr.sin_port));
        }
        sendto(forward_sock, (const char *)buffer, (int)got, 0,
               (struct sockaddr *)&forward_addr, sizeof(forward_addr));
        if (pkt_count % LOG_EVERY == 0) {
            rt_kprintf("[CLIENT] forward %d bytes to %s:%d\n", got, cfg->forward_ip, cfg->forward_port);
        }

        if (WRITE_OUTPUT && out_file) {
            const uint8_t *payload = NULL;
            size_t payload_len = 0;
            struct RtpHeader rtp;
            if (!parse_rtp(buffer, (size_t)got, &rtp, &payload, &payload_len) || payload_len == 0) {
                continue;
            }
            uint8_t nalu_type = (payload[0] >> 1) & 0x3F;
            uint8_t *nalu = NULL;
            size_t nalu_len = 0;
            if (nalu_type == 49) {
                fu_process(payload, payload_len, &rtp, fu_pool, &nalu, &nalu_len);
            } else {
                nalu_len = payload_len + 4;
                nalu = (uint8_t *)malloc(nalu_len);
                if (nalu) {
                    nalu[0] = 0x00; nalu[1] = 0x00; nalu[2] = 0x00; nalu[3] = 0x01;
                    memcpy(nalu + 4, payload, payload_len);
                    if (rtp.marker) {
                        rt_kprintf("[CLIENT] single NALU ts=%u size=%zu type=%u\n", rtp.timestamp, nalu_len, nalu_type);
                    }
                }
            }
            if (nalu) {
                fwrite(nalu, 1, nalu_len, out_file);
                fflush(out_file);
                free(nalu);
            }
        }
    }
    CLOSESOCK(recv_sock);
    CLOSESOCK(forward_sock);
}

static void rtp_client_thread(void *parameter) {
    struct rtp_cfg cfg = *(struct rtp_cfg *)parameter;
    rt_free(parameter);
    rtp_client_loop(&cfg);
}

int rtp_client_start(int argc, char **argv) {
    struct rtp_cfg *cfg = (struct rtp_cfg *)rt_malloc(sizeof(struct rtp_cfg));
    if (!cfg) return -1;
    rt_snprintf(cfg->listen_ip, sizeof(cfg->listen_ip), "%s", DEFAULT_LISTEN_IP);
    cfg->listen_port = DEFAULT_LISTEN_PORT;
    rt_snprintf(cfg->forward_ip, sizeof(cfg->forward_ip), "%s", DEFAULT_FORWARD_IP);
    cfg->forward_port = DEFAULT_FORWARD_PORT;
    if (argc >= 3) {
        rt_snprintf(cfg->forward_ip, sizeof(cfg->forward_ip), "%s", argv[1]);
        cfg->forward_port = (uint16_t)atoi(argv[2]);
    }
    if (argc >= 5) {
        rt_snprintf(cfg->listen_ip, sizeof(cfg->listen_ip), "%s", argv[3]);
        cfg->listen_port = (uint16_t)atoi(argv[4]);
    }
    rt_thread_t tid = rt_thread_create("rtpcli", rtp_client_thread, cfg, 4096, 20, 10);
    if (tid) {
        rt_thread_startup(tid);
        return 0;
    }
    rt_free(cfg);
    return -1;
}
MSH_CMD_EXPORT(rtp_client_start, start udp forwarder: rtp_client_start [fwd_ip fwd_port listen_ip listen_port]);
