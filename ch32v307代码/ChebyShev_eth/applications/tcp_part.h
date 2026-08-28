/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-25     Hello       the first version
 */
#ifndef APPLICATIONS_TCP_PART_H_
#define APPLICATIONS_TCP_PART_H_
#include <rtthread.h>
#include <sys/socket.h> /* 使用BSD socket，需要包含socket.h头文件 */
#include <netdb.h>
#include <string.h>
#include <finsh.h>
#include <inttypes.h>
#include <ctype.h>
#include "protocol.h"
#define BUFSZ   2048
static char str_QA[65],str_QPW[65],str_QID[65];
static char str_N21[65],str_QID3[65],str_TC[65],str_HM3[65];




#endif /* APPLICATIONS_TCP_PART_H_ */
