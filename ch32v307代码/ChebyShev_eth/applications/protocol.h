/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#ifndef APPLICATIONS_PROTOCOL_H_
#define APPLICATIONS_PROTOCOL_H_
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "Prime_number.h"
#include "tcp_part.h"
#include "ChebyShev.h"
#include "SM3.h"
/*static 变量*/


typedef struct {
    int userid;
    int password;
    int bio;
    uint256_t A;
    uint256_t d;
    uint256_t N;
    uint256_t x;
    uint256_t pk;
    uint256_t L;
    uint256_t N1;
    uint256_t PID;
    uint256_t QID;
    uint256_t a1;
    uint256_t b;
    uint256_t TA;
    uint256_t TB;
    uint256_t TA1;
    uint256_t TTA;
} Client;

typedef struct{
    uint256_t QA;
    uint256_t QPW;
    uint256_t QID;
} Auth_Param;

typedef struct{
    uint256_t N2;
    uint256_t TC;
    uint256_t QID;
    uint256_t HM3;
} Share_Param;

/*uint256_to_decstr*/
static rt_uint8_t bytes[32];
static char result[80];
static rt_uint8_t tp[32];

/*save used*/
static Client client;
static uint256_t A,d,N,x,pk,L,N1;

/*auth pre used*/
static char id_str[16], pw_str[16], Bio_str[16],L_str[80];
static uint256_t PID,A,QID,temp1,QPW,QA,pwt;
static char input_str[128];
static char concat_str[128];
static unsigned char big_int_bytes[128];
static unsigned char hash[32];
static char temp[128];
static char next[128];
static uint256_t A_half;
static rt_uint32_t temp2;
static uint256_t PID_half;
static int id,pw,Bio,byte_len,carry,next_len,digit,carry,q,i;
static unsigned char tmp;


/*Share Key Gen*/
static char first[20],str_QID1[80], str_M1[80], str_HM21[80];
static uint256_t QID1, M1,HM2;
static rt_uint8_t output[32];
static unsigned char output_hash[32];
static rt_uint8_t concat[64];
static uint256_t HM21,HM3,QID2,TA,a1,b,N2,c,TC,TA1,Ta,TB;
static ull temp3;
static uint256_t Client_QID;
static char str_N2[80], str_TC1[80], str_QID2[80];
static char concat1[256];

/*Share Key Gen2*/
static uint256_t TC1,QID3, HM5;
static char strr_TC[80], strr_QID3[80], strr_HM5[80];
static uint256_t HM51;
static uint256_t ta2, tb2, tc12,left, right,tmp1, tmp2,TTA,N,TA1,TB1;
static char sa[80], sb[80], sAA[80];
static char concat2[256];
static rt_uint8_t KS[32];


int rt_request(int argc, char**argv);
void register_proc(char* second,char* third,char* forth,char* fifth,char* sixth,char* seventh,char* eighth);
void auth_pre(Auth_Param *auth_param);
void Sharedkey_Gen(char* buffer,Share_Param* share_param);
void Sharedkey_Gen2(char *recv_data);
void request_send(char * data,int socket);


#endif /* APPLICATIONS_PROTOCOL_H_ */
