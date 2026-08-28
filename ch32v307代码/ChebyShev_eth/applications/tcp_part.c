/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */

#include "tcp_part.h"
static rt_tick_t tick;
static char send_data[1024]; /* 发送用到的数据 */
static char first[20],second[80],third[80],forth[80],fifth[80],sixth[80],seventh[80],eighth[80];
static Auth_Param auth_param;
static Share_Param share_param;
static rt_tick_t tick1,tick2,tick3,tick4,tick5,tick6;

void save_parameter(char *recv_data){
    sscanf(recv_data, "%s %s %s %s %s %s %s %s",first,second,third,forth,fifth,sixth,seventh,eighth);
    /*
    printf("%s\n",first);
    printf("%s\n",second);
    printf("%s\n",third);
    printf("%s\n",forth);
    printf("%s\n",fifth);
    printf("%s\n",sixth);
    printf("%s\n",seventh);
    printf("%s\n",eighth);
     * */

    register_proc(second,third,forth,fifth,sixth,seventh,eighth);
    //tick = rt_tick_get();
    //rt_kprintf("tick:%d",tick);
}

int uint256_to_hex(const uint256_t value, char* output, size_t output_size) {
    // 确保缓冲区足够大
    if (output_size < 65) return -1;

    // 将每个32位部分转换为8位十六进制
    for (int i = 7; i >= 0; i--) {
        // 使用 PRIX32 宏正确格式化
        snprintf(output + (7 - i) * 8, 9, "%08" PRIX32, value[i]);
    }

    output[64] = '\0'; // 确保终止
    return 0;
}

void tcpclient(/*int argc, char **argv*/)
{
    int ret;
    char *recv_data;
    struct hostent *host;
    int sock, bytes_received;
    struct sockaddr_in server_addr;
    const char *url;
    int port;
    /*
    if (argc < 3)
    {
        rt_kprintf("Usage: tcpclient URL PORT\n");
        rt_kprintf("Like: tcpclient 192.168.1.122 12345\n");
        return ;
    }*/
    //url = argv[1];
    url = "10.25.9.25";
    //port = strtoul(argv[2], 0, 10);
    port = strtoul("12345", 0, 10);
    /* 通过函数入口参数url获得host地址（如果是域名，会做域名解析） */
    host = gethostbyname(url);
    /* 分配用于存放接收数据的缓冲 */
    recv_data = rt_malloc(BUFSZ);
    if (recv_data == RT_NULL)
    {
        rt_kprintf("No memory\n");
        return;
    }
    /* 创建一个socket，类型是SOCKET_STREAM，TCP类型 */
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) == -1)
    {
        /* 创建socket失败 */
        rt_kprintf("Socket error\n");
        /* 释放接收缓冲 */
        rt_free(recv_data);
        return;
    }
    /* 初始化预连接的服务端地址 */
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    server_addr.sin_addr = *((struct in_addr *)host->h_addr);
    rt_memset(&(server_addr.sin_zero), 0, sizeof(server_addr.sin_zero));
    /* 连接到服务端 */
    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(struct sockaddr)) == -1)
    {
        /* 连接失败 */
        rt_kprintf("Connect fail!\n");
        closesocket(sock);
        /*释放接收缓冲 */
        rt_free(recv_data);
        return;
    }
    strcpy(send_data, "201");  // 直接覆盖写入
    request_send(send_data,sock);

    while (1)
    {
        /* 从sock连接中接收最大BUFSZ - 1字节数据 */
        bytes_received = recv(sock, recv_data, BUFSZ - 1, 0);
        if (bytes_received < 0)
        {
            /* 接收失败，关闭这个连接 */
            closesocket(sock);
            rt_kprintf("\nreceived error,close the socket.\r\n");
            /* 释放接收缓冲 */
            rt_free(recv_data);
            break;
        }
        else if (bytes_received == 0)
        {
            /* 默认 recv 为阻塞模式，此时收到0认为连接出错，关闭这个连接 */
            closesocket(sock);
            rt_kprintf("\nreceived error,close the socket.\r\n");
            /* 释放接收缓冲 */
            rt_free(recv_data);
            break;
        }
        /* 有接收到数据，把末端清零 */
        recv_data[bytes_received] = '\0';
        if (strncmp(recv_data, "q", 1) == 0 || strncmp(recv_data, "Q", 1) == 0)
        {
            /* 如果是首字母是q或Q，关闭这个连接 */
            closesocket(sock);
            rt_kprintf("\n got a 'q' or 'Q',close the socket.\r\n");
            /* 释放接收缓冲 */
            rt_free(recv_data);
            break;
        }
        else
        {
            //消息分类处理
            sscanf(recv_data, "%s",first);
            char* endptr;
            int situation = strtol(first, &endptr, 10);

            switch (situation) {
            case 101:
                //tick1 = rt_tick_get();
                //rt_kprintf("tick1 = %d\n",tick1);
                save_parameter(recv_data);
                rt_kprintf("\n---------The terminal device sends a registration request to the authentication center.---------\n");
                auth_pre(&auth_param);
                memset(send_data,0,sizeof(send_data));
                strcat(send_data, "202 ");
                uint256_to_hex(auth_param.QA, str_QA, sizeof(str_QA));
                uint256_to_hex(auth_param.QID, str_QID, sizeof(str_QID));
                uint256_to_hex(auth_param.QPW, str_QPW, sizeof(str_QPW));
                strcat(send_data,str_QA);
                strcat(send_data," ");
                strcat(send_data,str_QPW);
                strcat(send_data," ");
                strcat(send_data,str_QID);
                //rt_kprintf("send_data:%s",send_data);
                //tick2 = rt_tick_get();
                //rt_kprintf("tick2:%d",tick2);
                break;
            case 102:
                tick3 = rt_tick_get();
                //rt_kprintf("tick3:%d",tick3);
                rt_kprintf("------------------------------------shared key generation phase------------------------------------\n");
                Sharedkey_Gen(recv_data,&share_param);
                memset(send_data,0,sizeof(send_data));
                strcat(send_data, "203 ");
                uint256_to_hex(share_param.N2, str_N21, sizeof(str_N21));
                uint256_to_hex(share_param.QID, str_QID3, sizeof(str_QID3));
                uint256_to_hex(share_param.TC, str_TC1, sizeof(str_TC1));
                uint256_to_hex(share_param.HM3, str_HM3, sizeof(str_HM3));
                strcat(send_data,str_N21);
                strcat(send_data," ");
                strcat(send_data,str_QID3);
                strcat(send_data," ");
                strcat(send_data,str_TC1);
                strcat(send_data," ");
                strcat(send_data,str_HM3);
                tick4 = rt_tick_get();
                //rt_kprintf("tick4:%d",tick4);
                break;
            case 103:
                tick5 = rt_tick_get();
                //rt_kprintf("tick5:%d",tick5);
                rt_kprintf("------------------------------------shared key generation phase2------------------------------------\n");
                Sharedkey_Gen2(recv_data);
                tick6 = rt_tick_get();
                //rt_kprintf("tick6:%d",tick6);
                while(1){}
                break;
            default:
                printf("请求无法解析类型！");
                break;
            }

            /* 在控制终端显示收到的数据 */
            rt_kprintf("\nReceived data = %s ", recv_data);

        }
        /* 发送数据到sock连接 */
        ret = send(sock, send_data, strlen(send_data), 0);
        if (ret < 0)
        {
            /* 接收失败，关闭这个连接 */
            closesocket(sock);
            rt_kprintf("\nsend error,close the socket.\r\n");
            rt_free(recv_data);
            break;
        }
        else if (ret == 0)
        {
            /* 打印send函数返回值为0的警告信息 */
            rt_kprintf("\n Send warning,send function return 0.\r\n");
        }
    }
    return;
}
MSH_CMD_EXPORT(tcpclient, a tcp client sample);
