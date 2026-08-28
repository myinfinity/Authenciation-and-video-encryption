# -*- coding: utf-8 -*-
"""
补充实验（对标文献）—扩充版输出：
- 从明文视频抽取5帧
- 在像素域用 ZUC-256 对灰度像素 XOR 生成“像素域密文帧”（噪声化）
- 按论文公式计算相邻像素相关系数（水平/垂直/对角）
- 输出类似“表5-3 / 表4.3”的相关系数数据（控制台 + CSV）
- 生成类似“图4.10”的 3D 散点图：明文一张 + 密文一张（horizontal/vertical/diagonal）
- 保存明文帧/密文帧图像用于论文插图

不使用命令行参数：改 CONFIG 后运行。
"""

import os
import csv
import subprocess
from typing import List, Tuple

import numpy as np
import cv2
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# =========================
# CONFIG（改这里）
# =========================
PLAIN_VIDEO = r"D:/download/0c6c6-main/0c6c6-main/h265_cap_files/h265-2_test.h265"

# 固定抽帧（建议用你之前那5帧）
FRAME_INDICES = [121, 327, 514, 524, 662]
NUM_FRAMES = 5

RANDOM_SEED = 2026

# 每方向抽取相邻像素对数量 N（文献常用 2000~10000）
N_PAIRS = 5000

# 输出目录
OUT_DIR = r"./pixel_cipher_corr"

# 输出表格 CSV 文件名
OUT_CSV = "table_adjacent_corr_pixelcipher.csv"

# 生成“图4.10”3D散点图：选哪一帧做示例（None=用第一个帧）
PLOT_FRAME = None

# 3D 散点图显示点数（过大绘图慢）
PLOT_MAX_POINTS = 3000
# =========================


# =========================
# ZUC-256（你的实现：保持不变）
# =========================
ZUC_KEY = b"\x11" * 32
ZUC_IV16 = b"\x22" * 16

P31 = 0x7FFFFFFF
d2 = [
    0x64, 0x43, 0x7B, 0x2A, 0x11, 0x05, 0x51, 0x42,
    0x1A, 0x31, 0x18, 0x66, 0x14, 0x2E, 0x01, 0x5C
]
d3 = [
    0x22, 0x2F, 0x24, 0x2A, 0x6D, 0x40, 0x40, 0x40,
    0x40, 0x40, 0x40, 0x40, 0x40, 0x52, 0x10, 0x30
]

s0 = [
0x3E,0x72,0x5B,0x47,0xCA,0xE0,0x00,0x33,0x04,0xD1,0x54,0x98,0x09,0xB9,0x6D,0xCB,
0x8F,0xEA,0x20,0xAB,0x6A,0x41,0x7C,0x11,0xCF,0x7E,0xC7,0x7B,0x73,0xBC,0x5C,0x6F,
0x45,0x2E,0x33,0x67,0x24,0x4F,0x6B,0x48,0x8A,0x0F,0x5F,0xF7,0x1A,0xA2,0xF3,0x91,
0xEB,0x2D,0x0E,0x8B,0xA9,0x0C,0x86,0x1B,0xAE,0xC4,0x10,0x6C,0xF0,0x0A,0x5A,0xE9,
0x3D,0x46,0x8E,0xB4,0xE5,0x37,0xE7,0x0B,0xE8,0x2F,0x2B,0xA7,0x3B,0xD4,0x9D,0xFC,
0x7D,0x3F,0x29,0xB7,0x99,0x2C,0x9A,0xE3,0x9E,0xC6,0x5D,0x34,0x1C,0x9B,0xAF,0x1E,
0x3A,0x77,0x70,0xF1,0x39,0xAC,0xD0,0x1D,0x5E,0x62,0xCE,0x1F,0x8C,0xB3,0xE1,0xA5,
0x27,0x4B,0x2A,0xFD,0xDB,0x15,0xA4,0x4E,0x95,0xA0,0x14,0xF5,0x4A,0x61,0x83,0x38,
0x6E,0xD7,0x84,0x4D,0x1B,0x7F,0xC2,0xDC,0xEF,0x8D,0xAD,0xD8,0x26,0xB0,0xD6,0x93,
0x60,0x88,0xA8,0xBA,0xC5,0x21,0x9C,0xBD,0x92,0x16,0xF9,0xA6,0xFB,0xC1,0x0D,0x56,
0x44,0x85,0x57,0x12,0xC3,0xC9,0x90,0xEF,0x58,0x6F,0x4C,0x43,0xB6,0xD9,0x68,0x82,
0x30,0x52,0x71,0x5C,0x9F,0x36,0x64,0xA1,0x94,0xEA,0x13,0x2D,0x22,0xAD,0x97,0xB1,
0x79,0xF2,0x17,0x63,0xB8,0xD5,0x89,0x4C,0x59,0x23,0x25,0x66,0x08,0xD2,0x35,0xF8,
0x19,0x01,0x46,0x87,0xA3,0x55,0x96,0x69,0x42,0x0F,0xE2,0xCB,0x32,0x78,0xA9,0x7A,
0x6A,0xA4,0xFB,0xFB,0xE4,0x2C,0xC8,0xD3,0x80,0x05,0xC0,0x31,0xB5,0xF4,0x40,0x0D,
0x75,0x14,0xC7,0xD1,0xB2,0xF6,0x65,0x03,0xB9,0x09,0x7E,0x02,0x11,0x6D,0xA0,0x2E
]
s1 = [
0x55,0xC2,0x63,0x71,0x3B,0xC8,0x47,0x86,0x9F,0x3C,0xDA,0x5B,0x29,0xAA,0xFD,0x77,
0x8C,0xC5,0x94,0x0C,0xA6,0x1A,0x13,0x00,0xE3,0xA8,0x16,0x72,0x40,0xF9,0xF8,0x42,
0x44,0x26,0x68,0x96,0x81,0xD9,0x45,0x3E,0x10,0x76,0xC6,0xA7,0x8B,0x39,0x43,0xE1,
0x3A,0xB5,0x56,0x2A,0xC0,0x6D,0xB3,0x05,0x22,0x66,0xBF,0xDC,0x0B,0xFA,0x62,0x48,
0x24,0x91,0x8A,0x4B,0x9A,0x86,0xE7,0x1F,0x6B,0xD6,0xE6,0x18,0x30,0x0D,0xAB,0xF1,
0xA2,0x8D,0x6F,0x98,0x0A,0x7B,0x0E,0xC1,0xEF,0xDE,0xDB,0x1D,0xA4,0x9D,0x2F,0x5F,
0xB4,0xAF,0xEC,0x07,0xE2,0x67,0xF0,0xF6,0x4F,0x2B,0xBD,0xB8,0x4E,0x93,0x92,0x1B,
0x37,0xB0,0x28,0x60,0x64,0x15,0xCD,0xC3,0xF4,0x9C,0x36,0x1C,0xA5,0xD0,0x5A,0x7F,
0xDB,0x21,0x50,0xCF,0x04,0x88,0x6A,0x8E,0x9B,0xB6,0x20,0x14,0xE0,0x4A,0x6C,0x5D,
0x46,0x34,0x2D,0x49,0x7C,0x3D,0x85,0xA7,0x99,0x0F,0xF2,0x33,0x59,0x82,0x3F,0xE4,
0xC9,0xC7,0x97,0xA9,0xEC,0x3E,0x01,0xDD,0xC4,0x41,0x31,0x5C,0x7A,0x78,0x95,0x6E,
0x27,0xAB,0x35,0x52,0x17,0xBE,0x02,0x4C,0x6F,0xE8,0xA1,0xBD,0x12,0x0B,0xC5,0xCE,
0xE9,0x7D,0x1E,0xA3,0x08,0xB1,0x65,0x32,0xB7,0xF3,0xF5,0xC0,0x87,0xFE,0x89,0x25,
0x5E,0xC8,0x2C,0x51,0x4D,0xF7,0x61,0x54,0xAE,0x9E,0x11,0xD8,0x3B,0x73,0xD5,0xA0,
0x5B,0xD1,0xE5,0xF8,0x6D,0x43,0x03,0x96,0x38,0x4B,0x44,0x29,0x19,0xCA,0xB2,0xB9,
0x84,0x71,0x8F,0x53,0x2A,0x9F,0x57,0x0C,0xA6,0x16,0x75,0x40,0x2E,0xAD,0x09,0xD4
]

def rol32(x: int, n: int) -> int:
    x &= 0xFFFFFFFF
    return ((x << n) & 0xFFFFFFFF) | (x >> (32 - n))

def add31(a: int, b: int) -> int:
    x = a + b
    x = x + (x >> 31)
    x &= P31
    return x

def mul31(a: int, n: int) -> int:
    return ((a << n) | (a >> (31 - n))) & P31

def L1(x: int) -> int:
    return x ^ rol32(x, 2) ^ rol32(x, 10) ^ rol32(x, 18) ^ rol32(x, 24)

def L2(x: int) -> int:
    return x ^ rol32(x, 8) ^ rol32(x, 14) ^ rol32(x, 22) ^ rol32(x, 30)

def S_func(x: int) -> int:
    b0 = s1[x & 0xFF]
    b1 = s0[(x >> 8) & 0xFF]
    b2 = s1[(x >> 16) & 0xFF]
    b3 = s0[(x >> 24) & 0xFF]
    return (b0) | (b1 << 8) | (b2 << 16) | (b3 << 24)

class ZUC256:
    def __init__(self, key: bytes, iv: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes")
        if len(iv) != 16:
            raise ValueError("This script uses 16-byte IV only.")
        if len(s0) != 256 or len(s1) != 256:
            raise ValueError("s0/s1 must be 256 entries each")
        self.key = key
        self.iv = iv
        self.s = [0] * 16
        self.R1 = 0
        self.R2 = 0
        self._init_state()

    @staticmethod
    def _load2(a, b, c, d):
        return ((a << 23) | ((b & 0x7F) << 16) | (c << 8) | d) & 0x7FFFFFFF

    def _bit_reorg(self):
        s = self.s
        x0 = ((s[15] << 1) & 0xFFFF0000) | (s[14] & 0xFFFF)
        x1 = ((s[11] << 16) & 0xFFFF0000) | ((s[9] >> 15) & 0xFFFF)
        x2 = ((s[7] << 16) & 0xFFFF0000) | ((s[5] >> 15) & 0xFFFF)
        x3 = ((s[2] << 16) & 0xFFFF0000) | ((s[0] >> 15) & 0xFFFF)
        return x0, x1, x2, x3

    def _F(self, x0, x1, x2):
        w = ((x0 ^ self.R1) + self.R2) & 0xFFFFFFFF
        w1 = (self.R1 + x1) & 0xFFFFFFFF
        w2 = (self.R2 ^ x2) & 0xFFFFFFFF
        tmp = ((w1 << 16) | (w2 >> 16)) & 0xFFFFFFFF
        tmp = L1(tmp)
        self.R1 = S_func(tmp)
        tmp2 = ((w2 << 16) | (w1 >> 16)) & 0xFFFFFFFF
        tmp2 = L2(tmp2)
        self.R2 = S_func(tmp2)
        return w & 0xFFFFFFFF

    def _lfsr_init(self, u):
        s = self.s
        s0_ = s[0]
        s16 = add31(s0_, mul31(s0_, 8))
        s16 = add31(s16, mul31(s[4], 20))
        s16 = add31(s16, mul31(s[10], 21))
        s16 = add31(s16, mul31(s[13], 17))
        s16 = add31(s16, mul31(s[15], 15))
        s16 = add31(s16, u)
        for i in range(15):
            s[i] = s[i + 1]
        s[15] = s16

    def _lfsr_work(self):
        s = self.s
        s0_ = s[0]
        s16 = add31(s0_, mul31(s0_, 8))
        s16 = add31(s16, mul31(s[4], 20))
        s16 = add31(s16, mul31(s[10], 21))
        s16 = add31(s16, mul31(s[13], 17))
        s16 = add31(s16, mul31(s[15], 15))
        for i in range(15):
            s[i] = s[i + 1]
        s[15] = s16

    def _init_state(self):
        k = list(self.key)
        iv = list(self.iv)
        self.s[0]  = ZUC256._load2(k[0],  d2[0],  k[16], k[24])
        self.s[1]  = ZUC256._load2(k[1],  d2[1],  k[17], k[25])
        self.s[2]  = ZUC256._load2(k[2],  d2[2],  k[18], k[26])
        self.s[3]  = ZUC256._load2(k[3],  d2[3],  k[19], k[27])
        self.s[4]  = ZUC256._load2(k[4],  d2[4],  k[20], k[28])
        self.s[5]  = ZUC256._load2(k[5],  d2[5],  k[21], k[29])
        self.s[6]  = ZUC256._load2(k[6],  d2[6],  k[22], k[30])
        self.s[7]  = ZUC256._load2(k[7],  d2[7],  iv[0], iv[8])
        self.s[8]  = ZUC256._load2(k[8],  d2[8],  iv[1], iv[9])
        self.s[9]  = ZUC256._load2(k[9],  d2[9],  iv[2], iv[10])
        self.s[10] = ZUC256._load2(k[10], d2[10], iv[3], iv[11])
        self.s[11] = ZUC256._load2(k[11], d2[11], iv[4], iv[12])
        self.s[12] = ZUC256._load2(k[12], d2[12], iv[5], iv[13])
        self.s[13] = ZUC256._load2(k[13], d2[13], iv[6], iv[14])
        self.s[14] = ZUC256._load2(k[14], d2[14], iv[7], iv[15])
        self.s[15] = ZUC256._load2(k[15], d2[15], k[23], k[31])

        self.R1 = 0
        self.R2 = 0
        for _ in range(32):
            x0, x1, x2, x3 = self._bit_reorg()
            w = self._F(x0, x1, x2)
            w = (w >> 1) & 0x7FFFFFFF
            self._lfsr_init(w)
        x0, x1, x2, x3 = self._bit_reorg()
        _ = self._F(x0, x1, x2)
        self._lfsr_work()

    def keystream_word(self) -> int:
        x0, x1, x2, x3 = self._bit_reorg()
        w = self._F(x0, x1, x2)
        z = w ^ x3
        self._lfsr_work()
        return z & 0xFFFFFFFF

    def keystream_bytes(self, n_bytes: int) -> bytes:
        words = (n_bytes + 3) // 4
        out = bytearray()
        for _ in range(words):
            out += self.keystream_word().to_bytes(4, "big")
        return bytes(out[:n_bytes])


def zuc_keystream_bytes(nbytes: int, key: bytes, iv: bytes) -> bytes:
    zuc = ZUC256(key, iv)
    return zuc.keystream_bytes(nbytes)


# ---------- ffmpeg helpers ----------
def run_cmd(cmd: List[str]) -> Tuple[int, bytes, bytes]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return p.returncode, out, err


def extract_frame_png_bytes(path: str, frame_idx: int) -> bytes:
    vf = f"select=eq(n\\,{frame_idx})"
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", path,
        "-vf", vf,
        "-vsync", "0",
        "-frames:v", "1",
        "-f", "image2pipe",
        "-vcodec", "png",
        "pipe:1"
    ]
    rc, out, err = run_cmd(cmd)
    if rc != 0 or not out:
        raise RuntimeError(
            f"ffmpeg extract frame {frame_idx} failed:\n{err.decode(errors='ignore')}"
        )
    return out


def png_bytes_to_bgr(png_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Failed to decode PNG bytes.")
    return img


def to_gray_u8(bgr: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if g.dtype != np.uint8:
        g = np.clip(g, 0, 255).astype(np.uint8)
    return g


# ---------- 像素域密文化（ZUC XOR） ----------
def pixel_cipher_gray(gray: np.ndarray, frame_idx: int) -> np.ndarray:
    # 让每帧 IV 不同（简单混入 frame_idx）
    iv = bytearray(ZUC_IV16)
    iv[0] ^= (frame_idx & 0xFF)
    iv[1] ^= ((frame_idx >> 8) & 0xFF)
    iv = bytes(iv)

    flat = gray.reshape(-1)
    ks = zuc_keystream_bytes(flat.size, ZUC_KEY, iv)
    ks_arr = np.frombuffer(ks, dtype=np.uint8)
    cipher_flat = np.bitwise_xor(flat, ks_arr)
    return cipher_flat.reshape(gray.shape)


# ---------- 按论文公式计算相关系数 ----------
def corr_by_formula(x: np.ndarray, y: np.ndarray) -> float:
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    N = x.size
    if N == 0:
        return 0.0
    Ex = np.sum(x) / N
    Ey = np.sum(y) / N
    Dx = np.sum((x - Ex) ** 2) / N
    Dy = np.sum((y - Ey) ** 2) / N
    cov = np.sum((x - Ex) * (y - Ey)) / N
    denom = np.sqrt(Dx) * np.sqrt(Dy)
    return float(cov / denom) if denom != 0 else 0.0


def sample_pairs(gray: np.ndarray, N: int, mode: str) -> Tuple[np.ndarray, np.ndarray]:
    H, W = gray.shape
    if mode == 'h':
        xs = np.random.randint(0, H, size=N)
        ys = np.random.randint(0, W - 1, size=N)
        x = gray[xs, ys]
        y = gray[xs, ys + 1]
    elif mode == 'v':
        xs = np.random.randint(0, H - 1, size=N)
        ys = np.random.randint(0, W, size=N)
        x = gray[xs, ys]
        y = gray[xs + 1, ys]
    elif mode == 'd':
        xs = np.random.randint(0, H - 1, size=N)
        ys = np.random.randint(0, W - 1, size=N)
        x = gray[xs, ys]
        y = gray[xs + 1, ys + 1]
    else:
        raise ValueError("mode must be 'h','v','d'")
    return x, y


def adjacent_corr(gray: np.ndarray, N: int) -> Tuple[float, float, float]:
    xh, yh = sample_pairs(gray, N, 'h')
    xv, yv = sample_pairs(gray, N, 'v')
    xd, yd = sample_pairs(gray, N, 'd')
    return corr_by_formula(xh, yh), corr_by_formula(xv, yv), corr_by_formula(xd, yd)


# ---------- 新增：图4.10风格 3D 散点图 ----------
def _downsample(p: np.ndarray, q: np.ndarray, max_points: int) -> Tuple[np.ndarray, np.ndarray]:
    n = p.size
    if n <= max_points:
        return p, q
    idx = np.random.choice(n, size=max_points, replace=False)
    return p[idx], q[idx]


def plot_corr_3d(ph, qh, pv, qv, pd, qd, title: str, out_path: str, max_points: int = 3000):
    ph, qh = _downsample(ph, qh, max_points)
    pv, qv = _downsample(pv, qv, max_points)
    pd, qd = _downsample(pd, qd, max_points)

    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection='3d')

    x1 = np.ones_like(ph) * 1
    x2 = np.ones_like(pv) * 2
    x3 = np.ones_like(pd) * 3

    ax.scatter(x1, ph, qh, s=2, label="horizontal")
    ax.scatter(x2, pv, qv, s=2, label="vertical")
    ax.scatter(x3, pd, qd, s=2, label="diagonal")

    ax.set_xlabel("direction (1=h,2=v,3=d)")
    ax.set_ylabel("x (pixel)")
    ax.set_zlabel("y (neighbor)")
    ax.set_xlim(0.5, 3.5)
    ax.set_ylim(0, 255)
    ax.set_zlim(0, 255)
    ax.set_title(title)
    ax.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    np.random.seed(RANDOM_SEED)

    idxs = FRAME_INDICES[:NUM_FRAMES]
    print(f"Sample frames: {idxs}\n")

    # 生成表格数据：对每帧分别算明文与像素域密文相关系数
    table_rows = []

    for frame_idx in idxs:
        p_png = extract_frame_png_bytes(PLAIN_VIDEO, frame_idx)
        plain_gray = to_gray_u8(png_bytes_to_bgr(p_png))

        cipher_gray = pixel_cipher_gray(plain_gray, frame_idx)

        ph, pv, pd = adjacent_corr(plain_gray, N_PAIRS)
        ch, cv, cd = adjacent_corr(cipher_gray, N_PAIRS)

        table_rows.append([frame_idx, ph, pv, pd, ch, cv, cd])

        # 保存明文/密文帧图像
        cv2.imwrite(os.path.join(OUT_DIR, f"plain_frame_{frame_idx}.png"), plain_gray)
        cv2.imwrite(os.path.join(OUT_DIR, f"cipher_pixel_frame_{frame_idx}.png"), cipher_gray)

    # ---------- 输出“表 4.3 / 表 5-3”风格（控制台） ----------
    print("表：相邻像素相关性（像素域密文，对标文献）")
    print("{:<8} {:>10} {:>10} {:>10}  ||  {:>10} {:>10} {:>10}".format(
        "测试帧", "明文-水平", "明文-垂直", "明文-对角", "密文-水平", "密文-垂直", "密文-对角"
    ))
    for r in table_rows:
        frame_idx, ph, pv, pd, ch, cv, cd = r
        print("{:<8d} {:>10.4f} {:>10.4f} {:>10.4f}  ||  {:>10.4f} {:>10.4f} {:>10.4f}".format(
            frame_idx, ph, pv, pd, ch, cv, cd
        ))

    # ---------- 保存 CSV（用于论文表格） ----------
    out_csv_path = os.path.join(OUT_DIR, OUT_CSV)
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["FrameIndex",
                    "Plain_H", "Plain_V", "Plain_D",
                    "Cipher_H", "Cipher_V", "Cipher_D"])
        for r in table_rows:
            w.writerow(r)
    print(f"\n[OK] CSV saved -> {out_csv_path}")

    # ---------- 生成“图 4.10”3D 散点图（明文 + 密文） ----------
    plot_frame = PLOT_FRAME if PLOT_FRAME is not None else idxs[0]

    # 取示例帧
    p_png = extract_frame_png_bytes(PLAIN_VIDEO, plot_frame)
    plain_gray = to_gray_u8(png_bytes_to_bgr(p_png))
    cipher_gray = pixel_cipher_gray(plain_gray, plot_frame)

    # 为画图重新采样三方向像素对
    ph, qh = sample_pairs(plain_gray, N_PAIRS, 'h')
    pv, qv = sample_pairs(plain_gray, N_PAIRS, 'v')
    pd, qd = sample_pairs(plain_gray, N_PAIRS, 'd')

    ch, cq = sample_pairs(cipher_gray, N_PAIRS, 'h')
    cv, cw = sample_pairs(cipher_gray, N_PAIRS, 'v')
    cd, ce = sample_pairs(cipher_gray, N_PAIRS, 'd')

    out_fig_plain = os.path.join(OUT_DIR, f"Fig4_10_plain_corr3d_frame_{plot_frame}.png")
    out_fig_cipher = os.path.join(OUT_DIR, f"Fig4_10_cipher_corr3d_frame_{plot_frame}.png")

    plot_corr_3d(ph, qh, pv, qv, pd, qd,
                 title=f"(a) Plain adjacent correlation (frame {plot_frame})",
                 out_path=out_fig_plain,
                 max_points=PLOT_MAX_POINTS)

    plot_corr_3d(ch, cq, cv, cw, cd, ce,
                 title=f"(b) Cipher adjacent correlation (frame {plot_frame})",
                 out_path=out_fig_cipher,
                 max_points=PLOT_MAX_POINTS)

    print(f"[OK] 3D scatter saved -> {out_fig_plain}")
    print(f"[OK] 3D scatter saved -> {out_fig_cipher}")
    print(f"[OK] Images saved in: {OUT_DIR}")


if __name__ == "__main__":
    main()
