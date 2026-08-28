/*
 * Copyright (c) 2006-2021, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * Change Logs:
 * Date           Author       Notes
 * 2025-06-23     Hello       the first version
 */
#include "protocol.h"

void sm3_to_uint256(const unsigned char output[32], uint256_t *result)
{
    for (int i = 0; i < 8; i++) {
        (*result)[i] = ((uint32_t)output[i * 4] << 24) |
                    ((uint32_t)output[i * 4 + 1] << 16) |
                    ((uint32_t)output[i * 4 + 2] << 8) |
                    ((uint32_t)output[i * 4 + 3]);
    }
}

// 将 int 转为 uint256_t，只在最低位赋值，高位填 0 或符号扩展
void int_to_uint256(uint256_t dest, int value) {
    // 清空所有元素
    for (int i = 0; i < 8; i++) {
        dest[i] = 0;
    }

    // 将 value 放在最低位
    dest[0] = (uint32_t)value;
}

void uint256_to_decstr(uint256_t *value, char *out_str, size_t maxlen) {
    // 拷贝到 uint8_t 数组（大端）
    for (int i = 0; i < 8; i++) {
        bytes[i*4 + 0] = ((*value)[i] >> 24) & 0xFF;
        bytes[i*4 + 1] = ((*value)[i] >> 16) & 0xFF;
        bytes[i*4 + 2] = ((*value)[i] >> 8) & 0xFF;
        bytes[i*4 + 3] = (*value)[i] & 0xFF;
    }

    // 模拟大整数除法转十进制（最简洁方案）
    memcpy(tp, bytes, 32);

    int result_pos = 79;
    result[result_pos--] = '\0';

    while (1) {
        int carry = 0;
        int is_zero = 1;
        for (int i = 0; i < 32; i++) {
            int val = (carry << 8) + tp[i];
            tp[i] = val / 10;
            carry = val % 10;
            if (tp[i] != 0) is_zero = 0;
        }
        result[result_pos--] = '0' + carry;
        if (is_zero) break;
    }

    strncpy(out_str, &result[result_pos + 1], maxlen - 1);
    out_str[maxlen - 1] = '\0';
}

void ull_to_uint256(uint256_t result, ull value) {
    // 先清零所有位
    for (int i = 0; i < 8; i++) {
        result[i] = 0;
    }

    // 将低32位和高32位填入前两个元素
    result[0] = (uint32_t)(value & 0xFFFFFFFFULL);         // 低32位
    result[1] = (uint32_t)((value >> 32) & 0xFFFFFFFFULL);  // 高32位
}


bool uint256_equal(const uint256_t a, const uint256_t b) {
    for (int i = 0; i < 8; i++) {
        if (a[i] != b[i]) {
            return false;
        }
    }
    return true;
}


void uint256_copy(uint256_t dest, const uint256_t src) {
    for (int i = 0; i < 8; i++) {
        dest[i] = src[i];
    }
}


void uint256_zero(uint256_t a) {
    for (int i = 0; i < 8; i++) {
        a[i] = 0;
    }
}

// a + b mod mod
void uint256_addmod(uint256_t result, const uint256_t a, const uint256_t b, const uint256_t mod) {
    uint64_t carry = 0;
    uint256_t sum;

    // a + b
    for (int i = 0; i < 8; ++i) {
        uint64_t temp = (uint64_t)a[i] + b[i] + carry;
        sum[i] = (uint32_t)temp;
        carry = temp >> 32;
    }

    // sum >= mod ?
    int ge = 0;
    for (int i = 7; i >= 0; --i) {
        if (sum[i] > mod[i]) {
            ge = 1;
            break;
        } else if (sum[i] < mod[i]) {
            ge = 0;
            break;
        }
    }

    // result = (sum >= mod) ? sum - mod : sum
    if (ge) {
        uint64_t borrow = 0;
        for (int i = 0; i < 8; ++i) {
            uint64_t temp = (uint64_t)sum[i] - mod[i] - borrow;
            result[i] = (uint32_t)temp;
            borrow = (temp >> 63) & 1; // borrow if temp < 0
        }
    } else {
        for (int i = 0; i < 8; ++i)
            result[i] = sum[i];
    }
}

// result = (a * b) % mod
void uint256_mulmod(uint256_t result, const uint256_t a, const uint256_t b, const uint256_t mod) {
    uint64_t product[16] = {0};
    uint256_t modcopy;
    set_uint256(&modcopy,  0x00000000, 0x00000000, 0x00000000, 0x00000000,
            0x00000000, 0x00000000, 0x00000000, 0x00000000);
    // Multiply a * b into 512-bit product
    for (int i = 0; i < 8; ++i) {
        uint64_t carry = 0;
        for (int j = 0; j < 8; ++j) {
            uint64_t temp = (uint64_t)a[i] * b[j] + product[i + j] + carry;
            product[i + j] = (uint32_t)temp;
            carry = temp >> 32;
        }
        product[i + 8] = carry;
    }

    // Now reduce 512-bit product mod 256-bit mod
    // Barrett reduction or simple long division
    // Here, we use simple shift-subtract division (slow but portable)


    for (int i = 0; i < 8; ++i)
        modcopy[i] = mod[i];
    // Convert product to uint32_t[16] style
    uint32_t prod[16];
    for (int i = 0; i < 16; ++i) prod[i] = (uint32_t)product[i];

    // Simple division algorithm (binary long division)
    uint256_t rem = {0};

    for (int i = 511; i >= 0; --i) {
        // Shift rem left by 1
        uint32_t carry = 0;
        for (int j = 0; j < 8; ++j) {
            uint64_t tmp = ((uint64_t)rem[j] << 1) | carry;
            rem[j] = (uint32_t)tmp;
            carry = tmp >> 32;
        }

        // Bring down next bit from product
        int bit_index = i % 32;
        int word_index = i / 32;
        uint32_t bit = (prod[word_index] >> bit_index) & 1;
        rem[0] |= bit;

        // if rem >= mod then rem -= mod
        int ge = 0;
        for (int j = 7; j >= 0; --j) {
            if (rem[j] > mod[j]) {
                ge = 1;
                break;
            } else if (rem[j] < mod[j]) {
                ge = 0;
                break;
            }
        }

        if (ge) {
            uint64_t borrow = 0;
            for (int j = 0; j < 8; ++j) {
                uint64_t temp = (uint64_t)rem[j] - mod[j] - borrow;
                rem[j] = (uint32_t)temp;
                borrow = (temp >> 63) & 1;
            }
        }
    }

    // result = rem
    for (int i = 0; i < 8; ++i) result[i] = rem[i];
}


int rt_request(int argc, char**argv){
    //初始化用户信息
    rt_kprintf("device original information\n");
    client.userid = strtol(argv[1], NULL, 10);
    client.password = strtol(argv[2], NULL, 10);
    client.bio = strtol(argv[3], NULL, 10);
    rt_kprintf("User ID:%d\n",client.userid);
    rt_kprintf("password：%d\n",client.password);
    rt_kprintf("biological information：%d\n",client.bio);

    return 0;
}
MSH_CMD_EXPORT(rt_request, rt_request <id pass bio>);

void request_send(char* send_data,int sock){
    rt_kprintf("id:%d",client.userid);
    snprintf(id_str, sizeof(id_str), " %d", client.userid);
    snprintf(Bio_str, sizeof(Bio_str), " %d", client.bio);
    snprintf(pw_str,sizeof(pw_str)," %d",client.password);
    strcat(send_data, id_str);
    strcat(send_data,pw_str);
    strcat(send_data,Bio_str);
    send(sock, send_data, strlen(send_data), 0);
}

int hex_to_uint256(const char *hex_str, uint256_t result) {
    // 1. 验证输入字符串
    size_t len = strlen(hex_str);
    if (len != 64) {
        return -1; // 长度错误
    }

    // 2. 验证所有字符都是有效的十六进制字符
    for (size_t i = 0; i < len; i++) {
        if (!isxdigit((unsigned char)hex_str[i])) {
            return -2; // 无效字符
        }
    }

    // 3. 将字符串分成8个部分（每个部分8个字符）
    for (int i = 0; i < 8; i++) {
        // 提取8个字符的子串
        char segment[9];
        strncpy(segment, hex_str + i * 8, 8);
        segment[8] = '\0';

        // 4. 将子串转换为 uint32_t
        char *endptr;
        uint32_t value = (uint32_t)strtoul(segment, &endptr, 16);

        // 5. 检查转换是否成功
        if (*endptr != '\0') {
            return -3; // 转换失败
        }

        // 6. 存储结果（注意字节序）
        result[7 - i] = value;
    }

    return 0;
}

void register_proc(char* second,char* third,char* forth,char* fifth,char* sixth,char* seventh,char* eighth){
    hex_to_uint256(second,A);
    hex_to_uint256(third,d);
    hex_to_uint256(forth,N);
    hex_to_uint256(fifth,x);
    hex_to_uint256(sixth,pk);
    hex_to_uint256(seventh,L);
    hex_to_uint256(eighth,N1);
    memcpy(client.A, A, sizeof(uint256_t));
    memcpy(client.d,d,sizeof(uint256_t));
    memcpy(client.N,N,sizeof(uint256_t));
    memcpy(client.x,x,sizeof(uint256_t));
    memcpy(client.pk,pk,sizeof(uint256_t));
    memcpy(client.L,L,sizeof(uint256_t));
    memcpy(client.N1,N1,sizeof(uint256_t));
    /*
    rt_kprintf("接收到的信息为：\n");
    rt_kprintf("A:");
    print_uint256(client.A);
    rt_kprintf("d:");
    print_uint256(client.d);
    rt_kprintf("N:");
    print_uint256(client.N);
    rt_kprintf("x:");
    print_uint256(client.x);
    rt_kprintf("pk:");
    print_uint256(client.pk);
    rt_kprintf("L:");
    print_uint256(client.L);
    rt_kprintf("N1:");
    print_uint256(client.N1);*/
}

void auth_pre(Auth_Param *auth_param){
    //1.计算PID
    id = client.userid;
    pw = client.password;
    Bio = client.bio;
    rt_kprintf("calculate PID parameters...\n");
    // 转为十进制字符串
    snprintf(id_str, sizeof(id_str), "%d", id);
    snprintf(Bio_str, sizeof(Bio_str), "%d", Bio);
    uint256_to_decstr(&(client.L), L_str, sizeof(L_str));
    rt_kprintf("L_str:%s\n",L_str);

    snprintf(concat_str, sizeof(concat_str), "%s%s%s", id_str, L_str, Bio_str);
    strcpy(temp,concat_str);
    temp[sizeof(temp) - 1] = '\0';
    //rt_kprintf("%s\n",temp);

    byte_len = 0;
    /*
    while (temp[0] != '\0') {
        carry = 0;
        next_len = 0;
        for (i = 0; temp[i]; i++) {
            digit = carry * 10 + (temp[i] - '0');
            q = digit / 256;
            carry = digit % 256;
            if (next_len > 0 || q > 0) {
                next[next_len++] = '0' + q;
            }
        }
        big_int_bytes[byte_len++] = carry;
        strcpy(temp,next);
    }*/
    char* ptr = temp;
    while (*ptr) {
        carry = 0;
        char* out_ptr = next;
        for (char* p = ptr; *p ; p++) {
            digit = carry * 10 + (*p - '0');
            if (out_ptr < next + 255) {
                *out_ptr++ = '0' + (digit / 256);
            }
            carry = digit % 256;
        }
        *out_ptr = '\0';
        // 存储结果字节
        if (byte_len < sizeof(big_int_bytes)) {
            big_int_bytes[byte_len++] = carry;
        }
        // 跳过前导零
        ptr = next;
        while (*ptr == '0') ptr++;
        if (!*ptr) break;
    }


    //rt_kprintf("%s\n",temp);
    // 反转字节顺序以获得大端格式
    for (i = 0; i < byte_len / 2; i++) {
        tmp = big_int_bytes[i];
        big_int_bytes[i] = big_int_bytes[byte_len - 1 - i];
        big_int_bytes[byte_len - 1 - i] = tmp;
    }

    // 哈希并转为 uint256_t
    gm_sm3(big_int_bytes, byte_len, hash);
    sm3_to_uint256(hash, &PID);

    //2.计算A
    rt_kprintf("Calculate parameter A and verify device identity.\n");
    snprintf(input_str, sizeof(input_str), "%d%d%d", id, pw, Bio);

    gm_sm3((const unsigned char*)input_str, strlen(input_str), hash);

    for (int i = 0; i < 8; i++) {
        temp2 = ((rt_uint32_t)hash[i * 4] << 24) |
            ((rt_uint32_t)hash[i * 4 + 1] << 16) |
            ((rt_uint32_t)hash[i * 4 + 2] << 8) |
            ((rt_uint32_t)hash[i * 4 + 3]);
        A[i] = temp2 ^ client.L[i];
    }
    rt_kprintf("A = ");
    print_uint256(A);
    //3.自认证A
    if (uint256_equal(A, client.A)) {
        rt_kprintf("self-authentication passed!\n");
    }
    else {
        rt_kprintf("self-authentication failed!\n");
        return;
    }
    //4.保存PID与QID
    //rt_kprintf("PID:");
    //print_uint256(PID);
    //rt_kprintf("\n");
    uint256_copy(client.PID, PID);
    set_uint256(&PID_half, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000);
    for(int i = 0;i < 2;i++){
        PID_half[i] = PID[i];
    }
    //rt_kprintf("PID_HALF:");
    //print_uint256(PID_half);
    //chebyshev_Tn(client->d, PID, client->N1, QID, temp1);
    //只算一半的PID
    rt_kprintf("encrypt PID、PW、A parameters\n");
    chebyshev_Tn(&(client.d), &PID_half, &client.N1, &QID, &temp1);
    rt_kprintf("QID = ");
    print_uint256(QID);
    uint256_copy(client.QID, QID);

    //5.计算QA和QPW
    int_to_uint256(pwt, pw);
    //rt_kprintf("pwt = ");
    //print_uint256(pwt);
    chebyshev_Tn(&(client.d), &pwt, &(client.N1), &QPW, &temp1);
    rt_kprintf("QPW = ");
    print_uint256(QPW);
    //chebyshev_Tn(client->d, A, client->N1, QA, temp1);
    //只算一般的A
    set_uint256(&A_half, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000);
    for (int i = 0;i < 2;i++) {
        A_half[i] = A[i];
    }
    chebyshev_Tn(&(client.d), &A_half, &(client.N1), &QA, &temp1);
    rt_kprintf("QA = ");
    print_uint256(QA);

    rt_kprintf("initiate an authentication request...\n");

    //返回QA、QID和QPW
    uint256_copy(auth_param->QA, QA);
    uint256_copy(auth_param->QID, QID);
    uint256_copy(auth_param->QPW, QPW);
    //假设遭到参数篡改攻击
    //set_uint256(&auth_param->QA, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
    //        0x00000000, 0x00000000, 0x00000000, 0x00000000);
}

void Sharedkey_Gen(char * recv_data,Share_Param* share_param) {
    rt_kprintf("Verify the integrity of the information received from the authentication center...\n");
    //解析得到参数QID1、N1、HM2
    sscanf(recv_data, "%s %s %s %s",first,str_QID1,str_M1,str_HM21);
    hex_to_uint256(str_QID1, QID1);
    hex_to_uint256(str_M1, M1);
    hex_to_uint256(str_HM21, HM2);

    //1.校验HM2
    for (int i = 0; i < 8; i++) {
        concat[i * 4 + 0] = (QID1[i] >> 24) & 0xFF;
        concat[i * 4 + 1] = (QID1[i] >> 16) & 0xFF;
        concat[i * 4 + 2] = (QID1[i] >> 8) & 0xFF;
        concat[i * 4 + 3] = QID1[i] & 0xFF;
    }
    for (int i = 0; i < 8; i++) {
        concat[32 + i * 4 + 0] = (M1[i] >> 24) & 0xFF;
        concat[32 + i * 4 + 1] = (M1[i] >> 16) & 0xFF;
        concat[32 + i * 4 + 2] = (M1[i] >> 8) & 0xFF;
        concat[32 + i * 4 + 3] = M1[i] & 0xFF;
    }
    gm_sm3(concat, 64, output);
    sm3_to_uint256(output, &HM21);
    rt_kprintf("HM21 = ");
    print_uint256(HM21);
    if (uint256_equal(HM21, HM2)) {
        rt_kprintf("received message complete!\n");
    }
    //2.验证QID是否与保存的一致
    rt_kprintf("Verify if the QID is consistent with the saved one.\n");
    set_uint256(&A_half, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000);
    for (int i = 0;i < 2;i++) {
        A_half[i] = client.A[i];
    }
    chebyshev_Tn(&A_half, &(client.pk), &(client.N), &TA, &temp1);
    //rt_kprintf("TA = ");
    //print_uint256(TA);
    uint256_copy(client.TA, TA);
    for (int i = 0; i < 8; i++) {
        QID2[i] = QID1[i] ^ TA[i];
    }
    rt_kprintf("QID = ");
    print_uint256(QID2);
    set_uint256(&Client_QID, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
        0x00000000, 0x00000000, 0x00000000, 0x00000000);
    for (int i = 0;i < 2;i++) {
        Client_QID[i] = client.QID[i];
    }

    if (uint256_equal(QID2, Client_QID)) {
        rt_kprintf("Match the ID with the registration center!\n");
    }

    //3.解密会话随机数a1
    for (int i = 0; i < 8; i++) {
        a1[i] = M1[i] ^ TA[i];
    }
    rt_kprintf("The received random number a1 ：");
    print_uint256(a1);
    uint256_copy(client.a1, a1);
    //uint256_copy(client->TA, Ta);
    //4.设备端产生会话随机数,并加密
    rt_kprintf("---------------The device initiates a shared key parameter verification request.------------------\n");
    temp3 = creat_number(32);
    rt_kprintf("The device generates a session random number.\n");
    ull_to_uint256(b, temp3);
    print_uint256(b);
    uint256_copy(client.b, b);

    for (int i = 0; i < 8; i++) {
        N2[i] = b[i] ^ TA[i];
    }
    big_add(a1, b, c);
    //5.加密参数a1,b,c
    chebyshev_Tn(&c, &(client.pk), &(client.N), &TC, &temp1);
    chebyshev_Tn(&a1, &(client.pk), &(client.N), &TA1, &temp1);
    chebyshev_Tn(&b, &(client.pk), &(client.N), &TB, &temp1);

    uint256_copy(client.TA1, TA1);
    uint256_copy(client.TB, TB);

    uint256_to_decstr(&N2, str_N2, sizeof(str_N2));
    uint256_to_decstr(&TC, str_TC1, sizeof(str_TC1));
    uint256_to_decstr(&QID2, str_QID2, sizeof(str_QID2));
    rt_kprintf("Generate encryption parameters N2 and TC.\n");
    rt_kprintf("str_N2:%s\n",str_N2);
    rt_kprintf("str_TC:%s\n",str_TC1);
    //rt_kprintf("str_QID2:%s\n",str_QID2);

    snprintf(concat1, sizeof(concat1), "%s%s%s", str_N2, str_TC1, str_QID2);

    gm_sm3((const unsigned char*)concat1, (unsigned int)strlen(concat1), output_hash);
    sm3_to_uint256(output_hash, &HM3);
    uint256_copy(share_param->HM3, HM3);
    uint256_copy(share_param->N2, N2);
    uint256_copy(share_param->QID, QID2);
    uint256_copy(share_param->TC, TC);
}

void Sharedkey_Gen2(char *recv_data){
    //解析数据包
    rt_kprintf("Verify the integrity of the information received from the authentication center...\n");
    sscanf(recv_data, "%s %s %s %s",first,strr_TC,strr_QID3,strr_HM5);
    hex_to_uint256(strr_TC, TC1);
    hex_to_uint256(strr_QID3, QID3);
    hex_to_uint256(strr_HM5, HM5);
    rt_kprintf("TC:");
    print_uint256(TC1);

    //1.验证消息完整性
    for (int i = 0; i < 8; i++) {
        concat[i * 4 + 0] = (TC1[i] >> 24) & 0xFF;
        concat[i * 4 + 1] = (TC1[i] >> 16) & 0xFF;
        concat[i * 4 + 2] = (TC1[i] >> 8) & 0xFF;
        concat[i * 4 + 3] = TC1[i] & 0xFF;
    }
    for (int i = 0; i < 8; i++) {
        concat[32 + i * 4 + 0] = (QID3[i] >> 24) & 0xFF;
        concat[32 + i * 4 + 1] = (QID3[i] >> 16) & 0xFF;
        concat[32 + i * 4 + 2] = (QID3[i] >> 8) & 0xFF;
        concat[32 + i * 4 + 3] = QID3[i] & 0xFF;
    }
    gm_sm3(concat, 64, output);
    sm3_to_uint256(output,&HM51);
    if(uint256_equal(HM51, HM5)){
        rt_kprintf("The received information is intact!\n");
    }

    rt_kprintf("Generate random number verification parameters...\n");
    chebyshev_Tn(&(client.a1), &(client.pk), &(client.N), &TA1, &temp1);
    rt_kprintf("TA:");
    print_uint256(TA1);
    uint256_copy(TB1, client.TB);
    rt_kprintf("TB:");
    print_uint256(TB1);
    uint256_copy(N, client.N);
    rt_kprintf("N:");
    print_uint256(N);

    // ta2 = TA * TA % N
   uint256_mulmod(ta2, TA1, TA1, N);

   // tb2 = TB * TB % N
   uint256_mulmod(tb2, TB1, TB1, N);

   // tc12 = TC1 * TC1 % N
   uint256_mulmod(tc12, TC1, TC1, N);

   // left = (ta2 + tb2 + tc12) % N
   uint256_addmod(tmp1, ta2, tb2, N);
   uint256_addmod(left, tmp1, tc12, N);

   // tmp1 = TA * TB % N
   uint256_mulmod(tmp1, TA1, TB1, N);

   // tmp2 = tmp1 * TC1 % N
   uint256_mulmod(tmp2, tmp1, TC1, N);

   // tmp1 = tmp2 * 2 % N
   uint256_t two = { 2 };  // 256位常数2
   uint256_mulmod(tmp1, tmp2, two, N);

   // right = (tmp1 + 1) % N
   uint256_t one = { 1 };
   uint256_addmod(right, tmp1, one, N);

    if(uint256_equal(left, right)){
        rt_kprintf("The received 'a' is the same as the 'a' generated by the registration center!\n");
    }
    uint256_copy(TTA, client.TA);

    //3.计算共享密钥
    uint256_to_decstr(&(client.a1),sa,sizeof(sa));
    uint256_to_decstr(&(client.b),sb, sizeof(sb));
    uint256_to_decstr(&TTA,sAA, sizeof(sAA));

    // 拼接为字符串
    snprintf(concat2, sizeof(concat2), "%s%s%s", sa, sb, sAA);

    // 计算哈希
    gm_sm3((rt_uint8_t *)concat2, strlen(concat2), KS);
    rt_kprintf("Generate shared key KS = ");
    for (int i = 0; i < 32; i++) {
        rt_kprintf("%02x", KS[i]);
    }
}




