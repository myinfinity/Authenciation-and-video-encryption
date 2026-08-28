from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import random
import libnum
import timeit
import tracemalloc
from gmssl import sm3, func
import time

import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024.00)  # 转为 MB
    return mem


# 定义一个函数用于生成指定位数的素数
def creat_number(bits):
    while True:
        #p = random.randint(num1,num2)           #随机产生一个指定位数的整数
        p = libnum.generate_prime(bits // 2)
        if miller_rabin(p):
            return p
        #一直while循环，直到产生的数是素数

# 判断是否为素数
def checknum(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    #如果循环结束还没有数与之整除，这个数就是素数
    return True

def miller_rabin(n, k=5):  # k是测试的轮数，增加k可以提高准确性
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False

    # 写n-1为2^r·d的形式
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    # 重复k次测试
    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def matrix_mod(matrix, p):
    """ 对矩阵的每个元素取模p """
    return [[element % p for element in row] for row in matrix]

def matrix_multiply(A, B, p):
    """ 计算矩阵A和B的乘积，结果取模p """
    return [[sum(a * b for a, b in zip(row, col)) % p for col in zip(*B)] for row in A]

def matrix_power(matrix, power, p):
    """ 计算矩阵的power次幂，结果取模p """
    result = [[1 if i == j else 0 for j in range(len(matrix))] for i in range(len(matrix))]
    base = matrix_mod(matrix, p)
    
    while power > 0:
        if (power % 2) == 1:
            result = matrix_multiply(result, base, p)
        base = matrix_multiply(base, base, p)
        power //= 2
    
    return result

def chebyshev_matrix(n, x, p):
    """
    使用矩阵方法计算有限域GF(p)上的第n个切比雪夫多项式的值
    :param n: 切比雪夫多项式的阶数
    :param x: 输入值
    :param p: 有限域的大小，必须是一个素数
    :return: 第n个切比雪夫多项式的值，模p
    """
    if n == 0:
        return 1 % p
    elif n == 1:
        return x % p
    else:
        # 构造转移矩阵
        transfer_matrix = [[2 * x, -1], [1, 0]]
        
        # 计算转移矩阵的n-1次幂
        powered_matrix = matrix_power(transfer_matrix, n - 1, p)
        
        # 初始向量 [T_1(x), T_0(x)]
        initial_vector = [x, 1]
        
        # 计算最终向量 [T_n(x), T_{n-1}(x)]
        final_vector = [sum(a * b for a, b in zip(row, initial_vector)) % p for row in powered_matrix]
        
        return final_vector[0]
def sm3_hash(message):
    """
    为给定的消息生成SM3哈希值。

    参数:
    message: 需要哈希的原始消息，可以是字符串或数字。

    返回:
    str: 十六进制表示的SM3哈希值。
    """
    # 如果输入是数字，将其转换为字符串
    if isinstance(message, (int, float)):
        message = str(message)
    
    # 确保输入是字符串
    if not isinstance(message, str):
        raise TypeError("Input must be a string or a number.")
    
    # 将消息转换为字节
    message_bytes = message.encode('utf-8')
    
    # 使用gmssl库的sm3模块生成哈希
    h = sm3.sm3_hash(func.bytes_to_list(message_bytes))
    integer_hash = int(h, 16)
    
    return integer_hash

def protocol():

    piA = creat_number(128)
    p = creat_number(128)
    x = creat_number(128)
    piB = creat_number(128)
    S = creat_number(128)
    A = creat_number(128)
    B = creat_number(128)
    a = creat_number(128)
    b = creat_number(128)
    c = creat_number(128)
    d = creat_number(128)

    mA = int(str(A)+str(S)+str(piA))
    mB = int(str(B)+str(S)+str(piB))
    

    tA = sm3_hash(mA)
    
    tB = sm3_hash(mB)
    
    vA = chebyshev_matrix(tA, x, p)
    
    vB = chebyshev_matrix(tB, x, p)
    Xa = chebyshev_matrix(a, x, p)
    Xb = chebyshev_matrix(b, x, p)
    XSa = chebyshev_matrix(c, x, p)^vA
    XSb = chebyshev_matrix(d, x, p)^vB

    Td = XSb ^ vB
    KBs = chebyshev_matrix(b,Td,p)^chebyshev_matrix(tB,Td,p)
 
    M1 = str(B)+str(S)+str(Xb)+str(Xa)+str(KBs)
    uBs = sm3_hash(int(M1))
    print("uBs:",uBs)
    KBA = chebyshev_matrix(b,Xa,p)
    print("KBA:",KBA)
    M2 = str(B)+str(A)+str(Xb)+str(Xa)+str(KBA)
    uBa = sm3_hash(int(M2))
    print("uBa:",uBa)
    SK = sm3_hash(int(str(A)+str(B)+str(S)+str(Xa)+str(Xb)+str(KBA)))
    print("SK:",SK)
    
    Tc = XSa ^ vA
    KAs = chebyshev_matrix(a,Tc,p)^chebyshev_matrix(tA,Tc,p)
    print("KAs:",KAs)
    M3 = str(A)+str(S)+str(Xa)+str(Xb)+str(KAs)
    uAs = sm3_hash(int(M3))
    print("uAs:",uAs)
    KAB = chebyshev_matrix(a,Xb,p)
    print("KAB:",KAB)

    M4 = str(A)+str(B)+str(Xa)+str(Xb)+str(KBA)
    uAb = sm3_hash(int(M4))
    print("uAb:",uAb)
    
    KSA = chebyshev_matrix(c,vA,p)^chebyshev_matrix(c,Xa,p)
    print("KSA:",KSA)
    KSB = chebyshev_matrix(d,vB,p)^chebyshev_matrix(d,Xb,p)
    print("KSB:",KSB)
    KAB = chebyshev_matrix(a,Xb,p)
    print("KAB:",KAB)
    uSa = sm3_hash(int(str(A)+str(S)+str(Xa)+str(Xb)+str(KSA)))
    print("uSa:",uSa)
    uSb = sm3_hash(int(str(B)+str(S)+str(Xb)+str(Xa)+str(KSB)))
    print("uSb:",uSb)
    SK2 = sm3_hash(int(str(A)+str(B)+str(S)+str(Xa)+str(Xb)+str(KAB)))
    print("SK2:",SK2)
'''
# 内存分析
before = get_memory_usage()
# 执行你的算法
protocol()
after = get_memory_usage()

print(f"内存增加：{after - before:.4f} KB")
'''
'''
tracemalloc.start()

# 记录起始状态
before = tracemalloc.get_traced_memory()

# 执行你想测的函数或算法
protocol()

# 记录执行后的状态
after = tracemalloc.get_traced_memory()

# 停止追踪
tracemalloc.stop()

# 提取并转换为 MB
start_mem = before[0] / 1024 
peak_mem = after[1] / 1024 
end_mem = after[0] / 1024 

print(f"起始内存：{start_mem:.2f} KB")
print(f"当前内存：{end_mem:.2f} KB")
print(f"峰值内存：{peak_mem:.2f} KB")
'''


start_time = time.time()
protocol()
end_time = time.time()
total_time = end_time - start_time
print(f"Total time: {total_time:.2f} seconds")



