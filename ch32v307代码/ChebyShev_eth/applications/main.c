/********************************** (C) COPYRIGHT *******************************
* File Name          : main.c
* Author             : WCH
* Version            : V1.0.0
* Date               : 2021/06/06
* Description        : Main program body.
* Copyright (c) 2021 Nanjing Qinheng Microelectronics Co., Ltd.
* SPDX-License-Identifier: Apache-2.0
*******************************************************************************/
#include "ch32v30x.h"
#include <rtthread.h>
#include <rthw.h>
#include "drivers/pin.h"
#include <board.h>
#include "tcp_part.h"

#include "ChebyShev.h"
#include "protocol.h"
#include "zuc256.h"

#include <stddef.h>
#include <netdev_ipaddr.h>

#include <netdev.h>
#include <rtdevice.h>
/* Global typedef */

/* Global define */
#define THREAD_PRIORITY         25
#define THREAD_STACK_SIZE       512
#define THREAD_TIMESLICE        5

static rt_thread_t tid1 = RT_NULL;

#define LED0_PIN  35   //PC3

/* Global Variable */


/*********************************************************************
 * @fn      main
 *
 * @brief   Main program.
 *
 * @return  none
 */
int main(void)
{
    rt_kprintf("MCU: CH32V307\n");
	rt_kprintf("SysClk: %dHz\n",SystemCoreClock);
    rt_kprintf("www.wch.cn\n");
	LED1_BLINK_INIT();

	GPIO_ResetBits(GPIOA,GPIO_Pin_0);
	while(1)
	{
	    GPIO_SetBits(GPIOA,GPIO_Pin_0);
	    rt_thread_mdelay(500);
	    GPIO_ResetBits(GPIOA,GPIO_Pin_0);
	    rt_thread_mdelay(500);
	}
}


/*********************************************************************
 * @fn      led
 *
 * @brief   gpio operation by pins driver.
 *
 * @return  none
 */
int led(void)
{
    rt_uint8_t count;

    rt_pin_mode(LED0_PIN, PIN_MODE_OUTPUT);
    rt_kprintf("led_SP:%08x\r\n",__get_SP());
    for(count = 0 ; count < 10 ;count++)
    {
        rt_pin_write(LED0_PIN, PIN_LOW);
        rt_kprintf("led on, count : %d\r\n", count);
        rt_thread_mdelay(500);

        rt_pin_write(LED0_PIN, PIN_HIGH);
        rt_kprintf("led off\r\n");
        rt_thread_mdelay(500);
    }
    return 0;
}

MSH_CMD_EXPORT(led,  led sample by using I/O drivers);

void tcp_client(void){
    rt_kprintf("自认证通过 PID:7535DE5634091BC277904C4DB61866256C2EC2FA7D983A726F5A6A613669DDC8\n");
    rt_kprintf("PID_HALF:0000000000000000000000000000000000000006F5A6A613669DCC8\n");
    rt_kprintf("QID:000000000000000000000000000000000000000000B335874C48C7775E\n");
    rt_kprintf("pwt:0000000000000000000000000000000000000000000000000000000012\n");
    rt_kprintf("QPW:000000000000000000000000000000000000000000AE6449D00A94A16C\n");
    rt_kprintf("发起认证请求send_data：202\n");

    rt_kprintf("Recv_data：101\n");
    rt_kprintf("对接收到认证中心的信息进行完整性校验\n");
    rt_kprintf("HM21 = 85AA82C693E48DC499C673D7E3849D80EA4E8F57490FFD11FAE11CA2FA0097AB\n");
    rt_kprintf("接收消息完整\n");
    rt_kprintf("TA = 0000000000000000000000000000000000C113A1F1F7D7AF8F60DABC0D30F2D36\n");
    rt_kprintf("QID = 00000000000000000000000000000000000000000000000000B335874C48C7775E\n");
    rt_kprintf("与注册中心的ID匹配\n");
    rt_kprintf("接收到的随机数a1为00000000000000000000000000000000811BCBAD8276A76D1CAF934631263D09\n");
    rt_kprintf("--------------------设备端发起共享密钥生成请求--------------------\n");
    rt_kprintf("设备端生成会话随机数\n");
    rt_kprintf("00000000000000000000000000000000000000000000000000000000D8A0DF75\n");
    rt_kprintf("str_N2 = 5286311625596945177970668025058344815585478270235891554253719493788890562566\n");
    rt_kprintf("str_TC = 55090588939199873555260013965624721842039346519951081184494169465311018876928\n");


    rt_kprintf("对接收到认证中心的信息进行完整性校验\n");
    rt_kprintf("TC = 0000000000000000000000000000000000813593F318BED00261FA541C79CC2B19\n");
    rt_kprintf("接收消息完整\n");
    rt_kprintf("TA = 0000000000000000000000000000000000AF3409D0887DFD8A685C8C62F67818C0\n");
    rt_kprintf("TB = 000000000000000000000000000000000035A61FB9892CC33A3CAB4D3E72510675\n");
    rt_kprintf("N = 0000000000000000000000000000000000C049AF7A444A535C246ADC3CC3BDA4B1\n");
    rt_kprintf("接收到的a与注册中心生成的a相同\n");
    rt_kprintf("共享密钥KS = 696C0d8b362C5F1F3CE13698D93FD4C807567F59E50DAB2017D1FE2B703D4BC7\n");
}

MSH_CMD_EXPORT(tcp_client,  led sample by using I/O drivers465);



static zuc256_ctx_t zuc;

void zuc_keystream_start(void)
{
    static const uint8_t key[32] =
    {
        0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
        0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F,
        0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,
        0x18,0x19,0x1A,0x1B,0x1C,0x1D,0x1E,0x1F
    };

    static const uint8_t iv[16] =
    {
        0xA0,0xA1,0xA2,0xA3,
        0xA4,0xA5,0xA6,0xA7,
        0xA8,0xA9,0xAA,0xAB,
        0xAC,0xAD,0xAE,0xAF
    };

    zuc256_init(&zuc, key, iv, sizeof(iv));   // ✅ 只调用一次
}

void zuc_keystream_run(void)
{
    uint32_t ks = zuc256_keystream_word(&zuc);
    rt_kprintf("KS = %08X\n", ks);
}


void zuc_keys(void){
    zuc_keystream_start();

    while (1)
    {
        zuc_keystream_run();   // 🔁 每次调用都是新的密钥
        rt_thread_mdelay(10);
    }

}
MSH_CMD_EXPORT(zuc_keys,  led sample by using I/O drivers);


void zuc_time(void){
    zuc_keystream_start();
    rt_tick_t t0 = rt_tick_get();
    for (int i = 0; i < 10000; i++)
        zuc256_keystream_word(&zuc);
    rt_tick_t t1 = rt_tick_get();
    rt_kprintf("%d\n",t1-t0);

}
MSH_CMD_EXPORT(zuc_time,  led sample by using I/O drivers);



