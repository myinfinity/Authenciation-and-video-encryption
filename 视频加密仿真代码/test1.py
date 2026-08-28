"D:/download/cb315-main/cb315-main/h265测试文件/surfing.265"
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从 .h265 裸码流生成 A~E 分类加密码流，并生成图4-5：不同帧类型加密的视觉效果对比截图（contact sheet）
密钥流：ZUC-256（你提供的实现已集成）

依赖：
  - ffmpeg, ffprobe 在 PATH
  - pip install pillow
"""

import json
import mmap
import shutil
import subprocess
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# =========================================================
# 0) 在这里内置你的路径与参数
# =========================================================

# 原始 .h265 裸码流（Annex-B）
ORIGINAL_H265 = r"D:/download/test.h265"

# 输出目录（会生成 enc_A~enc_E.h265 + fig4_5_visual_compare.png）
OUT_DIR = Path(r"./out_fig4_5")

# 选择第几个 GOP（即第几个 I 帧作为起点），0-based
GOP_INDEX = 2

# 抽取 I 帧后续多少帧：I, I+1, ... I+FRAMES_AFTER
FRAMES_AFTER = 6

# 为尽量保持可解码性：跳过每个 VCL NAL 前多少字节（保护 NAL头+部分slice头）
SKIP_PREFIX_BYTES = 48

# 稀疏加密强度：把 rho 解释为“该帧类型中 VCL 载荷被加密的字节比例(近似)”
# 用 step = round(1/rho) 实现：rho=0.10 -> 大约每10字节加密1字节
CONFIGS = {
    "A_I-only":   {"rho_I": 0.10, "rho_P": 0.00, "rho_B": 0.00},
    "B_P-only":   {"rho_I": 0.00, "rho_P": 0.10, "rho_B": 0.00},
    "C_B-only":   {"rho_I": 0.00, "rho_P": 0.00, "rho_B": 0.10},
    "D_I+P":      {"rho_I": 0.07, "rho_P": 0.03, "rho_B": 0.00},
    "E_I+P+B":    {"rho_I": 0.06, "rho_P": 0.03, "rho_B": 0.01},
}

# =========================================================
# 1) 你提供的 ZUC-256 实现（原样集成）
# =========================================================

# ZUC key (32 bytes)
ZUC_KEY = b'\x11' * 32
ARNOLD_ROUNDS = 30  # 这里未使用，仅保留你给的常量
# ----------------------------------------------------

P31 = 0x7FFFFFFF

# ---------------------- ZUC256 implementation ----------------------
d2 = [
    0x64, 0x43, 0x7B, 0x2A, 0x11, 0x05, 0x51, 0x42,
    0x1A, 0x31, 0x18, 0x66, 0x14, 0x2E, 0x01, 0x5C
]
d3 = [
    0x22, 0x2F, 0x24, 0x2A, 0x6D, 0x40, 0x40, 0x40,
    0x40, 0x40, 0x40, 0x40, 0x40, 0x52, 0x10, 0x30
]

# 注意：s0/s1 必须各为 256 项；若你粘贴时被截断，请确保完整
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
    return ((x << n) & 0xFFFFFFFF) | ((x & 0xFFFFFFFF) >> (32 - n))

def add31(a: int, b: int) -> int:
    x = a + b
    x = x + (x >> 31)
    x &= P31
    return x

def mul31(a: int, n: int) -> int:
    return ((a << n) | (a >> (31 - n))) & P31

def L1(x: int) -> int:
    return x ^ rol32(x,2) ^ rol32(x,10) ^ rol32(x,18) ^ rol32(x,24)

def L2(x: int) -> int:
    return x ^ rol32(x,8) ^ rol32(x,14) ^ rol32(x,22) ^ rol32(x,30)

def S_func(x: int) -> int:
    b0 = s1[x & 0xFF]
    b1 = s0[(x >> 8) & 0xFF]
    b2 = s1[(x >> 16) & 0xFF]
    b3 = s0[(x >> 24) & 0xFF]
    return (b0) | (b1 << 8) | (b2 << 16) | (b3 << 24)

class ZUC256:
    def __init__(self, key: bytes, iv: bytes):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes (256-bit)")
        if len(iv) not in (16, 25):
            raise ValueError("IV must be 16 or 25 bytes")
        self.key = key
        self.iv = iv
        self.s = [0]*16
        self.R1 = 0
        self.R2 = 0
        self._init_state()

    @staticmethod
    def _load2(a,b,c,d):
        return ((a << 23) | ((b & 0x7F) << 16) | (c << 8) | d) & 0x7FFFFFFF

    def _bit_reorg(self):
        s = self.s
        x0 = ((s[15] << 1) & 0xFFFF0000) | (s[14] & 0xFFFF)
        x1 = ((s[11] << 16) & 0xFFFF0000) | ((s[9] >> 15) & 0xFFFF)
        x2 = ((s[7] << 16) & 0xFFFF0000) | ((s[5] >> 15) & 0xFFFF)
        x3 = ((s[2] << 16) & 0xFFFF0000) | ((s[0] >> 15) & 0xFFFF)
        return x0,x1,x2,x3

    def _F(self,x0,x1,x2):
        w = ((x0 ^ self.R1) + self.R2) & 0xFFFFFFFF
        w1 = (self.R1 + x1) & 0xFFFFFFFF
        w2 = (self.R2 ^ x2) & 0xFFFFFFFF
        tmp = ((w1 << 16) | (w2 >> 16)) & 0xFFFFFFFF
        tmp = L1(tmp)
        R1_new = S_func(tmp)
        tmp2 = ((w2 << 16) | (w1 >> 16)) & 0xFFFFFFFF
        tmp2 = L2(tmp2)
        R2_new = S_func(tmp2)
        self.R1 = R1_new
        self.R2 = R2_new
        return w & 0xFFFFFFFF

    def _lfsr_init(self,u):
        s = self.s
        s0_ = s[0]
        s16 = add31(s0_, mul31(s0_,8))
        s16 = add31(s16, mul31(s[4],20))
        s16 = add31(s16, mul31(s[10],21))
        s16 = add31(s16, mul31(s[13],17))
        s16 = add31(s16, mul31(s[15],15))
        s16 = add31(s16, u)
        for i in range(15):
            s[i] = s[i+1]
        s[15] = s16

    def _lfsr_work(self):
        s = self.s
        s0_ = s[0]
        s16 = add31(s0_, mul31(s0_,8))
        s16 = add31(s16, mul31(s[4],20))
        s16 = add31(s16, mul31(s[10],21))
        s16 = add31(s16, mul31(s[13],17))
        s16 = add31(s16, mul31(s[15],15))
        for i in range(15):
            s[i] = s[i+1]
        s[15] = s16

    def _init_state(self):
        k = list(self.key)
        iv = list(self.iv)
        if len(iv) == 16:
            self.s[0]  = ZUC256._load2(k[0],  d2[0], k[16], k[24])
            self.s[1]  = ZUC256._load2(k[1],  d2[1], k[17], k[25])
            self.s[2]  = ZUC256._load2(k[2],  d2[2], k[18], k[26])
            self.s[3]  = ZUC256._load2(k[3],  d2[3], k[19], k[27])
            self.s[4]  = ZUC256._load2(k[4],  d2[4], k[20], k[28])
            self.s[5]  = ZUC256._load2(k[5],  d2[5], k[21], k[29])
            self.s[6]  = ZUC256._load2(k[6],  d2[6], k[22], k[30])
            self.s[7]  = ZUC256._load2(k[7],  d2[7], iv[0], iv[8])
            self.s[8]  = ZUC256._load2(k[8],  d2[8], iv[1], iv[9])
            self.s[9]  = ZUC256._load2(k[9],  d2[9], iv[2], iv[10])
            self.s[10] = ZUC256._load2(k[10], d2[10], iv[3], iv[11])
            self.s[11] = ZUC256._load2(k[11], d2[11], iv[4], iv[12])
            self.s[12] = ZUC256._load2(k[12], d2[12], iv[5], iv[13])
            self.s[13] = ZUC256._load2(k[13], d2[13], iv[6], iv[14])
            self.s[14] = ZUC256._load2(k[14], d2[14], iv[7], iv[15])
            self.s[15] = ZUC256._load2(k[15], d2[15], k[23], k[31])
        else:
            D = d3
            if len(iv) < 25:
                raise ValueError("184-bit IV requires 25 bytes")
            def or_d_iv(d_const, small_iv):
                return d_const | (small_iv & 0x3F)
            self.s[0]  = ZUC256._load2(k[0],  D[0],  k[21], k[16])
            self.s[1]  = ZUC256._load2(k[1],  D[1],  k[22], k[17])
            self.s[2]  = ZUC256._load2(k[2],  D[2],  k[23], k[18])
            self.s[3]  = ZUC256._load2(k[3],  D[3],  k[24], k[19])
            self.s[4]  = ZUC256._load2(k[4],  D[4],  k[25], k[20])
            self.s[5]  = ZUC256._load2(iv[0], or_d_iv(D[5], iv[17]), k[5],  k[26])
            self.s[6]  = ZUC256._load2(iv[1], or_d_iv(D[6], iv[18]), k[6],  k[27])
            self.s[7]  = ZUC256._load2(iv[10], or_d_iv(D[7], iv[19]), k[7],  iv[2])
            self.s[8]  = ZUC256._load2(k[8],  or_d_iv(D[8], iv[20]), iv[3],  iv[11])
            self.s[9]  = ZUC256._load2(k[9],  or_d_iv(D[9], iv[21]), iv[12], iv[4])
            self.s[10] = ZUC256._load2(iv[5],  or_d_iv(D[10], iv[22]), k[10], k[28])
            self.s[11] = ZUC256._load2(k[11], or_d_iv(D[11], iv[23]), iv[6],  iv[13])
            self.s[12] = ZUC256._load2(k[12], or_d_iv(D[12], iv[24]), iv[7],  iv[14])
            self.s[13] = ZUC256._load2(k[13], D[13], iv[5], iv[8])
            k31_hi = (k[31] >> 4) & 0x0F
            k31_lo = k[31] & 0x0F
            self.s[14] = ZUC256._load2(k[14], (D[14] | k31_hi), iv[16], iv[9])
            self.s[15] = ZUC256._load2(k[15], (D[15] | k31_lo), k[30], k[29])

        self.R1 = 0
        self.R2 = 0
        for _ in range(32):
            x0,x1,x2,x3 = self._bit_reorg()
            w = self._F(x0,x1,x2)
            w = (w >> 1) & 0x7FFFFFFF
            self._lfsr_init(w)
        x0,x1,x2,x3 = self._bit_reorg()
        _ = self._F(x0,x1,x2)
        self._lfsr_work()

    def keystream_word(self) -> int:
        x0,x1,x2,x3 = self._bit_reorg()
        w = self._F(x0,x1,x2)
        z = w ^ x3
        self._lfsr_work()
        return z & 0xFFFFFFFF

    def keystream_bytes(self, n_bytes: int) -> bytes:
        words = (n_bytes + 3) // 4
        out = bytearray()
        for _ in range(words):
            out += self.keystream_word().to_bytes(4, 'big')
        return bytes(out[:n_bytes])

    def encrypt(self, data: bytes) -> bytes:
        ks = self.keystream_bytes(len(data))
        return bytes(a ^ b for a,b in zip(data, ks))

    def decrypt(self, data: bytes) -> bytes:
        return self.encrypt(data)
# ---------------------- end ZUC256 ----------------------


# =========================================================
# 2) 通用工具 + ffprobe + ffmpeg
# =========================================================

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nstderr:\n{p.stderr}")
    return p.stdout

def ensure_paths():
    if not Path(ORIGINAL_H265).exists():
        raise FileNotFoundError(f"Missing input: {ORIGINAL_H265}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_font(size=20):
    for name in ["DejaVuSans.ttf", "Arial.ttf", "NotoSansCJK-Regular.ttc"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()

def ffprobe_frames_h265(h265_path: str):
    """
    返回 frames 列表：每项含 n(帧号), pict_type(I/P/B), pkt_pos, pkt_size
    """
    out = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=pict_type,pkt_pos,pkt_size",
        "-of", "json",
        h265_path
    ])
    j = json.loads(out)
    frames = j.get("frames", [])
    rows = []
    for i, fr in enumerate(frames):
        if "pkt_pos" not in fr or "pkt_size" not in fr or "pict_type" not in fr:
            continue
        rows.append({
            "n": i,
            "pict_type": fr["pict_type"],
            "pkt_pos": int(fr["pkt_pos"]),
            "pkt_size": int(fr["pkt_size"]),
        })
    if not rows:
        raise RuntimeError("ffprobe did not return usable frame pkt_pos/pkt_size. Check your .h265 stream.")
    return rows

def ffmpeg_extract_frame(video_path: str, frame_idx: int, out_png: Path):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    vf = f"select=eq(n\\,{frame_idx})"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", video_path,
        "-vf", vf,
        "-vframes", "1",
        "-y", str(out_png)
    ])


# =========================================================
# 3) NAL 基础解析（Annex-B start code）
# =========================================================

def find_start_codes(buf: bytes):
    starts = []
    i = 0
    L = len(buf)
    while i + 3 < L:
        if buf[i] == 0 and buf[i+1] == 0 and buf[i+2] == 1:
            starts.append((i, 3))
            i += 3
            continue
        if i + 4 < L and buf[i] == 0 and buf[i+1] == 0 and buf[i+2] == 0 and buf[i+3] == 1:
            starts.append((i, 4))
            i += 4
            continue
        i += 1
    return starts

def hevc_nal_unit_type(first_header_byte: int) -> int:
    # HEVC: nal_unit_type = (byte0 >> 1) & 0x3f
    return (first_header_byte >> 1) & 0x3F

def is_vcl_nal(nal_type: int) -> bool:
    # HEVC VCL NAL types: 0..31
    return 0 <= nal_type <= 31


# =========================================================
# 4) 用 ZUC-256 生成密钥流：Key 固定，IV 按 (配置名|帧号) 派生
# =========================================================

def derive_iv16(cfg_name: str, frame_idx: int) -> bytes:
    """
    生成 16B IV（用于 ZUC-256 初始化）
    这里只做实验用的确定性派生：IV = SHA256(cfg_name|frame_idx)[:16]
    """
    msg = (cfg_name + "|" + str(frame_idx)).encode("utf-8")
    return hashlib.sha256(msg).digest()[:16]

def rho_for_type(cfg: dict, pict_type: str) -> float:
    if pict_type == "I":
        return float(cfg.get("rho_I", 0.0))
    if pict_type == "P":
        return float(cfg.get("rho_P", 0.0))
    if pict_type == "B":
        return float(cfg.get("rho_B", 0.0))
    return 0.0


# =========================================================
# 5) 分类加密：对帧对应的 pkt 区间内 VCL NAL 载荷做稀疏 XOR
# =========================================================

def encrypt_frame_packet_inplace(mm: mmap.mmap, pkt_pos: int, pkt_size: int,
                                 pict_type: str, cfg_name: str, cfg: dict,
                                 frame_idx: int):
    """
    在输出文件的 mmap 上，对该帧对应 pkt 区间内的 VCL NAL 载荷做稀疏 XOR（ZUC-256 密钥流）
    """
    rho = rho_for_type(cfg, pict_type)
    if rho <= 0:
        return 0

    step = max(2, int(round(1.0 / rho)))  # rho=0.1 -> step≈10
    seg = mm[pkt_pos:pkt_pos + pkt_size]  # bytes 用于扫描 start code

    scs = find_start_codes(seg)
    if not scs:
        return 0

    # 该帧初始化一次 ZUC（同帧内多次 keystream_bytes 会连续消耗密钥流）
    iv = derive_iv16(cfg_name, frame_idx)
    zuc = ZUC256(ZUC_KEY, iv)

    encrypted = 0

    for idx, (sc_pos, sc_len) in enumerate(scs):
        nal_hdr_pos = sc_pos + sc_len
        if nal_hdr_pos + 2 > len(seg):
            continue

        nal_end = scs[idx + 1][0] if idx + 1 < len(scs) else len(seg)

        b0 = seg[nal_hdr_pos]
        nal_type = hevc_nal_unit_type(b0)
        if not is_vcl_nal(nal_type):
            continue  # 只加密 VCL NAL（slice）

        abs_payload_start = pkt_pos + nal_hdr_pos + 2 + SKIP_PREFIX_BYTES
        abs_nal_end = pkt_pos + nal_end
        if abs_payload_start >= abs_nal_end:
            continue

        positions = list(range(abs_payload_start, abs_nal_end, step))
        ks = zuc.keystream_bytes(len(positions))

        for i, pos in enumerate(positions):
            mm[pos] = mm[pos] ^ ks[i]
            encrypted += 1

    return encrypted


def generate_encrypted_streams(original_h265: str, frames_info: list):
    outputs = {}
    for cfg_name, cfg in CONFIGS.items():
        out_path = OUT_DIR / f"{cfg_name}.h265"
        shutil.copyfile(original_h265, out_path)

        with open(out_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)
            total_enc = 0

            for fr in frames_info:
                pkt_pos, pkt_size = fr["pkt_pos"], fr["pkt_size"]
                if pkt_pos < 0 or pkt_pos + pkt_size > mm.size():
                    continue
                total_enc += encrypt_frame_packet_inplace(
                    mm=mm,
                    pkt_pos=pkt_pos,
                    pkt_size=pkt_size,
                    pict_type=fr["pict_type"],
                    cfg_name=cfg_name,
                    cfg=cfg,
                    frame_idx=fr["n"]
                )

            mm.flush()
            mm.close()

        outputs[cfg_name] = str(out_path)
        print(f"[ENC] {cfg_name}: saved {out_path} (encrypted_bytes≈{total_enc})")

    return outputs


# =========================================================
# 6) 图4-5：抽同一 GOP 的 I 帧及其后若干帧，拼 contact sheet
# =========================================================

def build_contact_sheet(rows, frames_to_show, out_png: Path,
                        cell_h=240, pad=10, label_w=240):
    tmp_dir = OUT_DIR / "tmp_frames_fig4_5"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    extracted = {}
    for row_label, vpath in rows:
        for n in frames_to_show:
            png = tmp_dir / f"{row_label}_n{n}.png"
            ffmpeg_extract_frame(vpath, n, png)
            extracted[(row_label, n)] = png

    first = Image.open(extracted[(rows[0][0], frames_to_show[0])]).convert("RGB")
    base_w, base_h = first.size
    cell_w = int(base_w * (cell_h / base_h))

    imgs = []
    for row_label, _ in rows:
        row_imgs = []
        for n in frames_to_show:
            im = Image.open(extracted[(row_label, n)]).convert("RGB")
            row_imgs.append(im.resize((cell_w, cell_h)))
        imgs.append(row_imgs)

    sheet_w = label_w + pad + len(frames_to_show) * (cell_w + pad)
    sheet_h = pad + len(rows) * (cell_h + pad)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    font_row = load_font(20)
    font_col = load_font(16)

    for r, (row_label, _) in enumerate(rows):
        y0 = pad + r * (cell_h + pad)
        draw.text((10, y0 + 10), row_label, fill=(0, 0, 0), font=font_row)

        for c, n in enumerate(frames_to_show):
            x0 = label_w + pad + c * (cell_w + pad)
            sheet.paste(imgs[r][c], (x0, y0))
            if r == 0:
                draw.text((x0, max(0, y0 - 20)), f"n={n}", fill=(0, 0, 0), font=font_col)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    print(f"[FIG] Saved Fig4-5 -> {out_png.resolve()}")


# =========================================================
# 7) main
# =========================================================

def main():
    ensure_paths()

    # sbox 长度检查（防止粘贴截断导致运行时异常）
    if len(s0) != 256 or len(s1) != 256:
        raise ValueError(f"s0/s1 length invalid: len(s0)={len(s0)}, len(s1)={len(s1)}. Please paste full 256-byte sboxes.")

    frames_info = ffprobe_frames_h265(ORIGINAL_H265)

    # 生成 A~E 分类加密 .h265
    enc_outputs = generate_encrypted_streams(ORIGINAL_H265, frames_info)

    # 选定同一 GOP：取第 GOP_INDEX 个 I 帧，并抽 I, I+1..I+N
    i_frames = [fr["n"] for fr in frames_info if fr["pict_type"] == "I"]
    if not i_frames:
        raise RuntimeError("No I frames found in ffprobe results.")

    g = max(0, min(GOP_INDEX, len(i_frames) - 1))
    i0 = i_frames[g]
    frames_to_show = [i0 + k for k in range(0, FRAMES_AFTER + 1)]

    rows = [("Original", ORIGINAL_H265)] + [(name, path) for name, path in enc_outputs.items()]
    out_png = OUT_DIR / "fig4_5_visual_compare.png"
    build_contact_sheet(rows, frames_to_show, out_png,
                        cell_h=240, pad=10, label_w=240)

    print(f"[DONE] GOP_INDEX={g}, I-frame n={i0}, shown={frames_to_show}")


if __name__ == "__main__":
    main()
