import numpy as np
import hashlib
import random
import math
import libnum
from gmssl import sm3, func
#json文件存储信息
import json
import os
import time
import tracemalloc
from memory_profiler import profile
# -*- encoding: utf-8 -*-
import socket
import sys

json_file_path = 'mydev.json'

def initialize_json_file():
    print(os.path)
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as file:
            json.dump([], file)

#添加数据
def add_device_info(pid, A,d,N,x,pk,L):
    # 读取现有的数据
    print(json_file_path)
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    
    # 创建新的个人数据
    new_person = {
        "pid": pid,
        "A": A,
        "d": d,
        "N": N,
        "x": x,
        "pk": pk,
        "L": L
    }
    
    # 添加到列表
    people.append(new_person)
    
    # 写回文件
    with open(json_file_path, 'w') as file:
        json.dump(people, file, indent=4)

#查询数据
def get_all_people():
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    return people

def get_person_by_name(name):
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    
    for person in people:
        if person['name'] == name:
            return int(person['A']),int(person['Auth'])
    return None

#更新数据
def update_person(name, new_email=None, new_phone=None):
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    
    for person in people:
        if person['name'] == name:
            if new_email:
                person['A'] = new_email
            if new_phone:
                person['Auth'] = new_phone
            break
    
    with open(json_file_path, 'w') as file:
        json.dump(people, file, indent=4)

#删除数据
def delete_person(name):
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    
    # 过滤掉要删除的个人
    people = [person for person in people if person['name'] != name]
    
    with open(json_file_path, 'w') as file:
        json.dump(people, file, indent=4)
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


# 计算扩展欧几里得算法（求逆元）
def extended_gcd(a, b):
    """ 返回gcd(a, b) 以及贝祖等式中的系数x, y"""
    if a == 0:
        return b, 0, 1
    else:
        g, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return g, x, y

def mod_inverse(a, m):
    """ 返回a在模m下的乘法逆元，如果不存在则返回None"""
    g, x, y = extended_gcd(a, m)
    if g != 1:
        # 如果g不等于1，则a与m不互质，没有乘法逆元
        return None
    else:
        # x可能是负数，所以需要将其转换到正数范围内
        return x % m
#参数a:模数，参数b：需求逆元的数，返回值中g是a和b的最大公约数，x - (b // a) * y这个式子的值就是我们所求的逆元

# 切比雪夫混沌映射
def chebyshev_map(x, k):
    return np.cos(k * np.arccos(x))

#拓展至有限域的混沌映射
def chebyshev_polynomial(n, x, p):
    """
    使用递推公式计算有限域GF(p)上的第n个切比雪夫多项式的值
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
        t_n_minus_2 = 1 % p
        t_n_minus_1 = x % p
        for i in range(2, n + 1):
            t_n = (2 * (x % p) * t_n_minus_1 - t_n_minus_2) % p
            t_n_minus_2 = t_n_minus_1
            t_n_minus_1 = t_n
        return t_n
    
   
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


# 拓展至非有限域的混沌映射
def matrix_multiply1(A, B):
    """ 计算矩阵A和B的乘积 """
    return [[sum(a * b for a, b in zip(row, col)) for col in zip(*B)] for row in A]

def matrix_power1(matrix, power):
    """ 计算矩阵的power次幂 """
    result = [[1 if i == j else 0 for j in range(len(matrix))] for i in range(len(matrix))]
    base = matrix
    
    while power > 0:
        if (power % 2) == 1:
            result = matrix_multiply1(result, base)
        base = matrix_multiply1(base, base)
        power //= 2
    
    return result

def chebyshev_matrix1(n, x):
    """
    使用矩阵方法计算第n个切比雪夫多项式的值
    :param n: 切比雪夫多项式的阶数
    :param x: 输入值
    :return: 第n个切比雪夫多项式的值
    """
    if n == 0:
        return 1
    elif n == 1:
        return x
    else:
        # 构造转移矩阵
        transfer_matrix = [[2 * x, -1], [1, 0]]
        
        # 计算转移矩阵的n-1次幂
        powered_matrix = matrix_power1(transfer_matrix, n - 1)
        
        # 初始向量 [T_1(x), T_0(x)]
        initial_vector = [x, 1]
        
        # 计算最终向量 [T_n(x), T_{n-1}(x)]
        final_vector = [sum(a * b for a, b in zip(row, initial_vector)) for row in powered_matrix]
        
        return final_vector[0]
    
# 将消息转换为数值
def message_to_number(message):
    # 使用哈希函数将消息转换为固定长度的数值
    hash_object = hashlib.sha256(message.encode())
    hex_dig = hash_object.hexdigest()
    # 将哈希值转换为整数
    message_num = int(hex_dig, 16)
    # 将数值归一化到 [-1, 1] 范围内
    normalized_num = (message_num / (2**256 - 1)) * 2 - 1
    return normalized_num

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

#用户注册
import hashlib
import binascii

class User:
    def __init__(self):
        self.userid = ""
        self.password = ""
        self.bio = ""
    def register_request(self,client):
        #发送注册请求
        print("请输入设备初始信息")
        self.userid = int(input("请输入用户名:"))
        self.password = int(input("请输入密码:"))
        self.bio = int(input("请输入生物信息："))
        print("终端设备向认证中心发送注册请求")
        print("等待认证中心返回身份鉴别参数")
        client.send_request("register", self,userid=self.userid, password=self.password, Bio=self.bio)
        

    def register_proc(self,A,d,N,x,pk,L):
        self.A = A
        self.d = d
        self.N = N
        self.x = x
        self.pk = pk
        self.L = L
    def user_info(self):
        print("用户注册阶段的信息如下")
        print(f"用户的私钥d是：{self.d}") 
        print(f"公钥pk是：{self.pk}")
        print(f"用户的随机数是：{self.L}")
    def auth_pre(self,id,pw,Bio):
        PID1 = sm3_hash(int(str(id)+str(self.L)+str(Bio)))
        A1 = sm3_hash(int(str(id)+str(pw)+str(Bio)))^self.L
        if A1 == self.A:
            print("身份自认证成功")
        else:
            print("身份自认证失败")
            return 
        self.PID = PID1
        QID = chebyshev_matrix(self.d,PID1,self.N)
        self.QID = QID
        QPW = chebyshev_matrix(self.d,pw,self.N)
        QA = chebyshev_matrix(self.d,A1,self.N)
        print("向认证中心发起注册请求")
        return QID,QPW,QA
    
    def Sharedkey_Gen(self,QID1,N1,HM2):
        print("对接收到的认证中心信息进行完整性校验")
        if(HM2 == sm3_hash(int(str(QID1)+str(N1)))):
            print("接收到的消息完整")
        else:
            print("接收到的消息不完整")
        QID2 = QID1^chebyshev_matrix(self.A,self.pk,self.N)
        if(QID2 == self.QID):
            print("QID与注册中心的QID匹配")
        else:
            print("QID与注册中心的QID不匹配")       
        a1 = N1^chebyshev_matrix(self.A,self.pk,self.N)
        print(f"接收到的认证中心随机数为{a1}")
        self.tmpa1 = a1
        print("---------------设备发起共享密钥生成请求------------------")
        b = creat_number(256)
        print(f"终端设备产生自己的会话随机数{b}，并加密发送")
        self.b = b
        N2 = chebyshev_matrix(self.A,self.pk,self.N)^b
        c = a1+b
        TC = chebyshev_matrix(c,self.pk,self.N)
        TA1 = chebyshev_matrix(a1,self.pk,self.N)
        print("产生随机数验证参数，并加密发送至认证中心")
        self.TA1 = TA1
        TB = chebyshev_matrix(b,self.pk,self.N)
        self.TB = TB
        QID2 = chebyshev_matrix(self.d,self.QID,self.N)
        HM3 = sm3_hash(int(str(N2)+str(TC)+str(QID2)))
        print("等待接收认证中心的验证参数")
        return N2,TC,QID2,HM3
    
    def Sharedkey_Gen2(self,TC1,QID3,HM5):
        print("验证消息的完整性")
        if(HM5 == sm3_hash(int(str(TC1)+str(QID3)))):     
            print("接收到的消息完整")
        else:
            print("接收到的消息不完整")
        TA = self.TA1
        TB = self.TB
        print("根据接收到的验证参数，验证接收到的随机数是否正确")
        if (TA*TA + TB*TB+TC1*TC1)%(self.N)  == (2*TA*TB*TC1+1)%(self.N) :
            print("接收到的a与注册中心生成的a相同")
            self.a =self.tmpa1
        else:
            print("a不相同")
            self.tmpa1 = 0
        AA = chebyshev_matrix(self.A,self.pk,self.N)
        print("产生协商密钥")
        KS = sm3_hash(int(str(self.a)+str(self.b)+str(AA)))
        return KS
'''
IP = '192.168.1.116' #填写服务器端的IP地址
port = 40005 #端口号必须一致
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((IP,port))
except Exception as e:
    print('server not find or not open')
    sys.exit()
while True:
    trigger = input("send:")
    s.sendall(trigger.encode())
    data = s.recv(1024)
    data = data.decode()
    print('recieved:',data)
    if trigger.lower() == '1':#发送1结束连接
        break
s.close()'
'''
'''
import socket
import json

def send_auth_request(client_socket):
    type="register"
    username=input("请输入用户名:")
    password=input("请输入密码:")
    Bio = input("请输入生物信息：")
    auth_data = {
        "type":type,
        "username": username,
        "password": password,
        "Bio": Bio
    }
    
    return auth_data

# 测试用例
if __name__ == "__main__":
    # 正常请求 
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('192.168.1.116', 12345))
    print("1.设备注册请求")
    print("2.设备认证请求")
    type= input("请输入请求类型:")
    if type == '1':
        auth_data=send_auth_request(client_socket)
        client_socket.send(json.dumps(auth_data).encode())
        response = client_socket.recv(1024).decode()
        print(json.loads(response))
    else:
        response = client_socket.recv(1024).decode()
        print(json.loads(response))
'''
# ---------- 客户端代码 ---------- 
import socket
import json
import struct

class PersistentClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('192.168.1.118', 12345))
    
    def send_request(self, action,userclient, **params):
        """发送带长度头的结构化请求"""
        request = {"action": action, **params}
        data = json.dumps(request).encode()
        
        # 添加长度头并发送
        header = struct.pack('>I', len(data))
        self.sock.send(header + data)
        
        # 接收响应
        header = self.sock.recv(4)
        resp_len = struct.unpack('>I', header)[0]
        response = b''
        while len(response) < resp_len:
            response += self.sock.recv(resp_len - len(response))
        
        response_data = json.loads(response.decode())
        handle_response(self,response_data,userclient)

    def close(self):
        self.sock.close()

def handle_response(self,response,userclient):
    if response["action"] == "register_ack"and response["status"] == 200:
        print("-------------------设备接收到认证中心生成的注册身份参数-----------------")
        print("设备信息如下：")
        
        userclient.register_proc(response["A"],response["d"],response["N"],response["x"],response["pk"],response["L"])
        userclient.user_info()
        
        while True:
            print("------------------设备发起身份认证请求------------------")  
            print("请输入终端信息，开始身份认证")
            userid=int(input("请输入用户名:"))
            password=int(input("请输入密码:"))
            Bio = int(input("请输入生物信息："))
            ret = userclient.auth_pre(userid,password,Bio)
            print("等待接收认证中心的密钥协商信息")
            if(ret): 
                QID,QPW,QA=ret
                self.send_request("auth_request",userclient,QID=QID,QPW=QPW,QA=QA)
                break
            else:
                print("登录身份不对，请重新输入信息")
    if response["action"] == "SharedKey_Gen_request" :
        print(response)
        if response["status"] == 400:
            print("认证中心身份验证失败,请重新发起请求")
            return -1
        print("--------设备接收到认证端发来的密钥协商请求------------")
        
        print("接收到认证中心发来的密钥协商信息")
        N2,TC,QID2,HM3=userclient.Sharedkey_Gen(response["QID1"],response["N1"],response["HM2"])
        self.send_request("SharedKey_Gen_response",userclient,N2=N2,TC=TC,QID2=QID2,HM3=HM3)
    if response["action"] == "SharedKey_Gen_Finish" and response["status"] == 200:
        print("-------设备接受到认证端发来的随机数验证消息---------")
        KS=userclient.Sharedkey_Gen2(response["TC1"],response["QID3"],response["HM5"])
        print(f"共享密钥KS  {KS }")
   

# 使用示例
if __name__ == "__main__":
    client = PersistentClient()
    print("---------设备信息初始化--------")
    s1 = User()
    # 登录认证
    s1.register_request(client)
    #print(client.send_request("login", username="admin", password="123456"))
    
    # 获取数据
    # 持续交互
    while True:
        cmd = input("输入指令（q退出）:")
        if(cmd == 'q'):
            break
    client.close()