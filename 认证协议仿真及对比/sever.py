# -*- encoding: utf-8 -*-
import socket
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

# JSON文件路径
json_file_path = 'people.json'

# 初始化JSON文件
def initialize_json_file():
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as file:
            json.dump([], file)

#添加数据
def add_person(pid, A, Auth):
    # 读取现有的数据
    with open(json_file_path, 'r') as file:
        people = json.load(file)
    
    # 创建新的个人数据
    new_person = {
        'name': pid,
        'A': A,
        'Auth': Auth
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
    
# 生成密钥
def generate_keys():
    # 私钥参数
    p = creat_number(64)
    q = creat_number(64)
    n = (p*p-1)*(q*q-1)
    e = creat_number(64)

    d = mod_inverse(e,n)
    N = p * q

    print(f"素数p和q分别是：{p}和{q}")


    # 生成私钥
    private_key = e
    # 生成公钥
    d = d%n
    public_key = d
    
    return public_key, private_key,N,n

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

#注册中心
class authencenter:
    def __init__(self):
        self.p  = creat_number(512)
        self.q  = creat_number(512)
        self.N  = self.p * self.q
        self.n  = (self.p*self.p-1)*(self.q*self.q-1)
        self.x  = creat_number(256)
        self.sk = creat_number(256)
        self.pk = chebyshev_matrix(self.sk,self.x,self.N)
        self.e  = creat_number(256)
        print("注册中心初始化完成")
        self.center_info()

    def center_info(self):
       print("注册中心注册阶段产生的信息如下")
       print(f"素数p和q分别是：{self.p}和{self.q}") 
       print(f"私钥sk是：{self.sk}") 
       print(f"公钥pk是：{self.pk}")
       print(f"私钥e是：{self.e}")
       print("等待设备接入")

    def  user_register(self,uid,pw,Bio):
        initialize_json_file()
        L = creat_number(256)
        k = int(str(pw)+str(self.sk))
        j = int(str(uid)+str(pw)+str(Bio))
        PID = sm3_hash(int(str(uid)+str(L)+str(Bio)))
        RPW = sm3_hash(k)
        A = int(sm3_hash(j))^L
        d = mod_inverse(self.e,self.n)
        TTG = chebyshev_matrix(A,self.pk,self.N)
        Auth = int(sm3_hash(int(str(self.sk)+str(RPW)+str(PID))))
        print(f"用户伪身份PID为：{PID}")
        print(f"用户伪密码RPW为：{RPW}")
        print(f"用户加密后的鉴别参数TA为：{TTG}")
        print(f"用户鉴别参数Auth为：{Auth}")
        print("将伪身份、伪密码、鉴别参数等身份参数发送给终端设备处")
        print("等待终端设备发起认证请求")
        add_person(f"{PID}", f"{TTG}", f"{Auth}")
        return A,d,self.N,self.x,self.pk,L
    
    def user_auth(self,QID,QPW,QA,HM1):
        print("验证消息完整性ing......")
        HM11 = sm3_hash(int(str(QID)+str(QPW)+str(QA)))
        if HM11 == HM1 :
            print("接收的消息完整")
        else:
            print("接收的消息不完整")
            print("消息完整性不正确，收到的信息可能被篡改")
            return -1
        PID1 = chebyshev_matrix(self.e,QID,self.N)
        A1 = chebyshev_matrix(self.e,QA,self.N)
        AA1 = chebyshev_matrix(A1,self.pk,self.N)
        #查表
        ret = get_person_by_name(str(PID1))
        if ret == None:
            print("用户不存在")
            print("结束本次认证")
            return -2
        else:
            AA,Auth = ret
        if AA & Auth:
            print("用户存在")
        else:
            print("用户不存在")
            
        if AA1 == AA:
            print("PID与A匹配")
        else:
            print("PID与A不匹配")
            return -1
        self.A = A1
        PW1 = chebyshev_matrix(self.e,QPW,self.N)
        RPW1 = sm3_hash(int(str(PW1)+str(self.sk)))
        Auth1 = sm3_hash(int(str(self.sk)+str(RPW1)+str(PID1)))
        #查表找PID对应元素
        if Auth == Auth1:
            print("ID与PW匹配")
        else:
            print("ID与PW不匹配")
            return -1
        #返回正确性
        print("对设备的认证信息验证完成，进入共享密钥生成阶段")
        return A1,QID

    def SharedKey_Gen(self,QID,A):
        TTG = chebyshev_matrix(A,self.pk,self.N)
        a = creat_number(256)
        print(f"认证中心生成的会话随机数为：{a}")
        self.a = a
        print("对其进行加密发送")
        N1 = TTG^a
        QID1 = QID^TTG
        self.QID = QID
        HM2 = sm3_hash(int(str(QID1)+str(N1)))
        print("等待接收会话随机数以及验证参数")
        return QID1,N1,HM2
    def SharedKey_Gen2(self,N2,TC,QID2,HM3):
        print("对接收到的终端信息进行完整性校验")
        HM4 = sm3_hash(int(str(N2)+str(TC)+str(QID2)))
        if HM4 == HM3:
            print("接收到的消息完整")
        else:
            print("接收到的消息不完整")
            return -1
        b1 = chebyshev_matrix(self.A,self.pk,self.N)^N2
        print(f"接收到的终端设备会话随机数为：{b1}")
        QID = chebyshev_matrix(self.e,QID2,self.N)
        if(QID == self.QID):
            print("QID与用户的QID匹配")
        else:
            print("QID与用户的QID不匹配")
            return -1
        TA = chebyshev_matrix(self.a,self.pk,self.N)
        TB = chebyshev_matrix(b1,self.pk,self.N)
        print("根据终端设备发送的验证参数，对接收到的终端随机数进行验证")
        if (TA*TA + TB*TB + TC*TC)%self.N  == (2*TA*TB*TC + 1)%self.N :
            print("接收到的b与用户生成的b相同")
        else:
            print("b不相同")
            return -1
        c1 = self.a+b1
        print("产生随机数验证参数，并对其进行加密发送至终端设备")
        QID3 = QID2^chebyshev_matrix(self.A,self.pk,self.N)
        TC1 = chebyshev_matrix(c1,self.pk,self.N)
        print("产生会话密钥")
        KS = sm3_hash(int(str(self.a)+str(b1)+str(chebyshev_matrix(self.A,self.pk,self.N))))
        HM5 = sm3_hash(int(str(TC1)+str(QID3)))
        return TC1,KS,QID3,HM5 

'''
s0 = authencenter(); 
A,d,N,x,pk,L = s0.user_register(6456,1193486,454566)

IP = "192.168.1.116" #服务器端可以写"localhost"，可以为空字符串""，可以为本机IP地址
port = 40005 #端口号
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((IP,port))
s.listen(1)
print('listen at port :',port)
conn,addr = s.accept()
print('connected by',addr)
 
while True:
    data = conn.recv(1024)
    data = data.decode()#解码
    if not data:
        break      
    if data == "register":
        send = "请输入注册的身份信息，格式为：ID,PW,Bio"
        print('recieved message:',data)

        conn.sendall(send.encode())#再编码发送
    print('recieved message:',data)
conn.close()
s.close()'
'''
'''
import socket
import json

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 12345))
    server_socket.listen(5)
    print("Server started, waiting for connections...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        data = client_socket.recv(1024).decode()
        response = process_auth_request(data)
        client_socket.send(response.encode())



def process_auth_request(data):
    """处理认证请求的核心逻辑"""
        # 尝试解析JSON
    auth_data = json.loads(data)
    
    # 检查必需字段
    required_fields = {'type'}
    if not required_fields.issubset(auth_data.keys()):
        missing = required_fields - auth_data.keys()
        return json.dumps({"status": "error", "message": f"Missing fields: {', '.join(missing)}"})
    
    if auth_data["type"] == "register":# 检查字段值有效性（示例校验）
        if not auth_data["username"] or not auth_data["password"]:
            return json.dumps({"status": "error", "message": "Empty credentials"})
        user_name = auth_data["username"]
        user_password = auth_data["password"]
        # 模拟认证验证（实际应查数据库）
        if auth_data["username"] == "kk" and auth_data["password"] == "123456" and auth_data["Bio"] == "12":
            return json.dumps({"status": "success", "message": "Authentication successful"})
        else:
            return json.dumps({"status": "error", "message": "Invalid credentials"})
    elif auth_data["type"] == "auth":
        user_PID = auth_data["PID"]
    elif auth_data["type"] == "Tips":
        return json.dumps(auth_data["message"])
    return json.dumps({"status": "error", "message": "Invalid JSON format"})

if __name__ == "__main__":
    start_server()'
'''

# ---------- 服务端代码 ---------- 
import socket
import json
import struct

def handle_client(client_socket,auclient):
    """持续处理客户端请求"""
    while True:
        try:
            # 读取消息头（4字节长度标识）
            header = client_socket.recv(4)
            if not header:
                print("客户端主动断开连接")
                break
            
            # 解析消息长度
            msg_len = struct.unpack('>I', header)[0]
            
            # 接收完整消息体
            received_data = b''
            while len(received_data) < msg_len:
                chunk = client_socket.recv(msg_len - len(received_data))
                if not chunk:
                    raise ConnectionError("连接中断")
                received_data += chunk
            
            # 处理业务逻辑
            request = json.loads(received_data.decode())
            response = process_request(request,auclient)
            
            # 返回响应（同样添加长度头）
            response_data = json.dumps(response).encode()
            header = struct.pack('>I', len(response_data))
            client_socket.send(header + response_data)
            
        except (ConnectionResetError, json.JSONDecodeError) as e:
            print(f"连接异常: {str(e)}")
            break

def process_request(request,auclient):
    """请求处理路由"""
    action = request.get("action")
    if action == "register":
        return register_handler(request,auclient)
    elif action == "auth_request":
        return auth_request_handler(request,auclient)
    elif action == "SharedKey_Gen_response":
        return SharedKey_Gen_response_handler(request,auclient)
    else:
        return {"status": 400, "message": "未知操作类型"}

def register_handler(request,auclient):
    """设备注册"""
    print("-----------------认证中心接收到注册请求，开始处理------------------")
    print(f"用户ID：{request.get('userid')}")
    print(f"用户密码：{request.get('password')}")
    print(f"用户生物信息：{request.get('Bio')}")
    print("产生相关验证参数如下")
    A,d,N,x,pk,L=auclient.user_register(request.get("userid"),request.get("password"),request.get("Bio"))
    return {"status": 200, "action":"register_ack","message": "注册成功","A":A,"d":d,"N":N,"x":x,"pk":pk,"L":L}


def auth_request_handler(request,auclient):
    """设备认证请求"""
    print("-----------------认证中心接收到认证请求，开始处理------------------")
    ret = auclient.user_auth(request.get("QID"),request.get("QPW"),request.get("QA"),sm3_hash(int(str(request.get("QID"))+str(request.get("QPW"))+str(request.get("QA")))))
    if ret == -1:
        return {"status": 400, "action":"SharedKey_Gen_request","message": "认证失败，完整性未通过"}
    elif ret == -2:
        return {"status": 400, "action":"SharedKey_Gen_request","message": "用户不存在,PID错误"}
    else:
        AA,QID=ret
    print("认证中心生成会话随机数，并对其进行加密发送")
    QID1,N1,HM2 = auclient.SharedKey_Gen(QID,AA)
    print(f"发送给终端设备的QID1  {QID1 }信息，等待接收终端设备的随机数信息")
    return {"status": 200, "action":"SharedKey_Gen_request","message": "发送共享密钥请求","QID1":QID1,"N1":N1,"HM2":HM2}

def SharedKey_Gen_response_handler(request,auclient):
    """认证中心接收共享密钥响应"""
    print("-------------------认证中心接收到共享密钥响应，开始处理-------------------")
    TC1,KS,QID3,HM5 = auclient.SharedKey_Gen2(request.get("N2"),request.get("TC"),request.get("QID2"),request.get("HM3"))
    print(f"共享密钥KS  {KS }")
    return {"status": 200, "action":"SharedKey_Gen_Finish","message": "共享密钥生成成功","TC1":TC1,"KS":KS,"QID3":QID3,"HM5":HM5}


if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))
    server.listen(5)
    s0 = authencenter()
    
    print("---------------认证中心长连接服务已启动---------------")

    while True:
        client, addr = server.accept()
        print(f"新连接: {addr}")
        handle_client(client,s0)
        client.close()


