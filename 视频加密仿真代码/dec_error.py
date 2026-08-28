# -*- coding: utf-8 -*-
"""
HEVC (.h265 AnnexB) Encrypt ONLY I-frames (IDR/CRA) using ZUC-256
- No CLI args: edit CONFIG and run.
- Keeps stream decodable: VPS/SPS/PPS/AUD/SEI kept plaintext.
- Encrypts ONLY NAL unit types {19,20,21} (IDR/CRA common set).
- For safety, skips first SKIP bytes of payload (slice header area).
"""

import struct
import hashlib
from typing import List, Tuple

# ============================================================
#                  USER CONFIG (edit here)
# ============================================================
INPUT_H265       = r"D:/download/0c6c6-main/0c6c6-main/h265_cap_files/h265-2_test.h265"
ENCRYPTED_H265   = r"encrypted_I_only.h265"
DECRYPTED_H265   = r"decrypted_I_only_FAILED.h265" # 修改文件名以示区别

MASTER_KEY32 = b"\x11" * 32          # 32B session/master key
SKIP_PAYLOAD_PREFIX = 64             # try 64/128 if needed

DO_ENCRYPT = True
DO_DECRYPT = True

# ============================================================
# ============================================================
#                 ZUC-256 (your implementation)
#   !!! Ensure s0/s1 are COMPLETE 256 entries each !!!
# ============================================================
P31 = 0x7FFFFFFF

d2 = [
    0x64, 0x43, 0x7B, 0x2A, 0x11, 0x05, 0x51, 0x42,
    0x1A, 0x31, 0x18, 0x66, 0x14, 0x2E, 0x01, 0x5C
]
d3 = [
    0x22, 0x2F, 0x24, 0x2A, 0x6D, 0x40, 0x40, 0x40,
    0x40, 0x40, 0x40, 0x40, 0x40, 0x52, 0x10, 0x30
]

# Paste full 256-entry S-boxes here (your s0/s1)
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
        if len(iv) not in (16, 25):
            raise ValueError("IV must be 16 or 25 bytes")
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
        if len(iv) == 16:
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
        else:
            raise ValueError("This script uses 16-byte IV only.")
            
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

def zuc256_keystream(key32: bytes, iv16: bytes, nbytes: int) -> bytes:
    return ZUC256(key32, iv16).keystream_bytes(nbytes)

# ============================================================
#                      AnnexB parsing
# ============================================================
START3 = b"\x00\x00\x01"
START4 = b"\x00\x00\x00\x01"

def find_start_codes(data: bytes) -> List[Tuple[int, int]]:
    out = []
    i = 0
    n = len(data)
    while i < n - 3:
        if data[i:i+4] == START4:
            out.append((i, 4))
            i += 4
        elif data[i:i+3] == START3:
            out.append((i, 3))
            i += 3
        else:
            i += 1
    return out

def split_annexb_nalus(data: bytes) -> List[Tuple[bytes, bytes]]:
    scs = find_start_codes(data)
    if not scs:
        raise ValueError("No AnnexB start codes found.")
    
    nalus = []
    for idx, (pos, sclen) in enumerate(scs):
        start = pos + sclen
        end = scs[idx + 1][0] if idx + 1 < len(scs) else len(data)
        nalu = data[start:end]
        if len(nalu) < 2:
            continue
        nalus.append((data[pos:pos+sclen], nalu))
    return nalus

def join_annexb_nalus(nalus: List[Tuple[bytes, bytes]]) -> bytes:
    return b"".join(sc + nalu for sc, nalu in nalus)

def hevc_nal_unit_type(nalu: bytes) -> int:
    return (nalu[0] >> 1) & 0x3F

def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

# ============================================================
#              Encrypt only I-frames (IDR/CRA)
# ============================================================
# Keep parameter sets / metadata plaintext
KEEP_PLAINTEXT_TYPES = {32, 33, 34, 35, 39, 40}  # VPS,SPS,PPS,AUD,SEI

# Treat these as "I-frame-like" access units (common & practical)
I_ONLY_TYPES = {19, 20, 21}  # IDR_W_RADL, IDR_N_LP, CRA

def extract_feat32(nalu: bytes) -> bytes:
    payload = nalu[2:]
    if len(payload) >= 32:
        return payload[:32]
    return payload + b"\x00" * (32 - len(payload))

def kdf_key_iv(master_key32: bytes, feat32: bytes, nal_index: int) -> Tuple[bytes, bytes]:
    key32 = hashlib.sha256(master_key32 + feat32 + struct.pack(">I", nal_index)).digest()
    iv16 = hashlib.sha256(feat32 + struct.pack(">I", nal_index) + master_key32).digest()[:16]
    return key32, iv16

def hevc_xor_i_only(in_path: str, out_path: str, master_key32: bytes, skip_prefix: int):
    data = open(in_path, "rb").read()
    nalus = split_annexb_nalus(data)
    
    out = []
    nal_index = 0
    
    for sc, nalu in nalus:
        ntype = hevc_nal_unit_type(nalu)
        
        # Always keep these plaintext
        if ntype in KEEP_PLAINTEXT_TYPES:
            out.append((sc, nalu))
            continue
            
        # Only encrypt IDR/CRA VCL NALs
        if ntype not in I_ONLY_TYPES:
            out.append((sc, nalu))
            continue
        
        header2 = nalu[:2]
        payload = nalu[2:]
        
        if len(payload) <= skip_prefix:
            out.append((sc, nalu))
            continue
            
        prefix = payload[:skip_prefix]
        body = payload[skip_prefix:]
        
        # Extract features (for encryption, payload is plain; for decryption, payload is already cipher)
        # BUT because skip_prefix=64 and feat32 uses first 32 bytes, feat32 is always from PLAINTEXT prefix
        # so this logic works correctly for valid keys.
        feat32 = extract_feat32(nalu)
        
        key32, iv16 = kdf_key_iv(master_key32, feat32, nal_index)
        nal_index += 1
        
        ks = zuc256_keystream(key32, iv16, len(body))
        out_body = xor_bytes(body, ks)
        
        out.append((sc, header2 + prefix + out_body))
        
    open(out_path, "wb").write(join_annexb_nalus(out))

# ============================================================
#                           Run
# ============================================================
if __name__ == "__main__":
    if DO_ENCRYPT:
        hevc_xor_i_only(INPUT_H265, ENCRYPTED_H265, MASTER_KEY32, SKIP_PAYLOAD_PREFIX)
        print(f"[OK] Encrypt(I-only) -> {ENCRYPTED_H265}")

    if DO_DECRYPT:
        # ================================================================
        # 修改部分：使用错误的密钥进行解密，从而产生解密失败（花屏）的视频
        # ================================================================
        WRONG_KEY32 = b"\x00" * 32  # 创建一个全0的错误密钥
        print(f"[!!] Intentionally using WRONG KEY to produce corrupt output...")
        
        hevc_xor_i_only(ENCRYPTED_H265, DECRYPTED_H265, WRONG_KEY32, SKIP_PAYLOAD_PREFIX)
        
        print(f"[OK] Decrypt(I-only) -> {DECRYPTED_H265} (Corrupted/Failed)")
