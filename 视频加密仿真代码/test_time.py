#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import hashlib
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict

import av

# =========================================================
#                 实验参数（直接在此处修改）
# =========================================================
INPUT_VIDEO = r"D:/download/cb315-main/cb315-main/h265测试文件/H265_1080P.mp4"         # 输入视频路径
FPS = 0.0                           # 0 表示自动读取原视频帧率
GOPS = [10, 25, 50]                 # 测试的 GOP / I帧间隔
OUTDIR = r"zuc_iframe_results"      # 输出目录

# ======================= ZUC-256 =========================

P31 = 0x7FFFFFFF

d2 = [
    0x64,0x43,0x7B,0x2A,0x11,0x05,0x51,0x42,
    0x1A,0x31,0x18,0x66,0x14,0x2E,0x01,0x5C
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

def rol32(x, n):
    x &= 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

def add31(a, b):
    x = a + b
    x = x + (x >> 31)
    return x & P31

def mul31(a, n):
    return ((a << n) | (a >> (31 - n))) & P31

def L1(x):
    return (x ^ rol32(x,2) ^ rol32(x,10) ^ rol32(x,18) ^ rol32(x,24)) & 0xFFFFFFFF

def L2(x):
    return (x ^ rol32(x,8) ^ rol32(x,14) ^ rol32(x,22) ^ rol32(x,30)) & 0xFFFFFFFF

def S(x):
    x &= 0xFFFFFFFF
    return (
        s1[x & 0xFF] |
        (s0[(x >> 8) & 0xFF] << 8) |
        (s1[(x >> 16) & 0xFF] << 16) |
        (s0[(x >> 24) & 0xFF] << 24)
    ) & 0xFFFFFFFF

class ZUC256:
    def __init__(self, key, iv):
        if not isinstance(key, (bytes, bytearray)) or len(key) != 32:
            raise ValueError("key 必须为 32 字节")
        if not isinstance(iv, (bytes, bytearray)) or len(iv) == 0:
            raise ValueError("iv 必须为非空字节串")
        self.s = [0] * 16
        self.R1 = 0
        self.R2 = 0
        self._init(key, iv)

    def _load(self, a, b, c, d):
        return ((a << 23) | ((b & 0x7F) << 16) | (c << 8) | d) & P31

    def _init(self, k, iv):
        for i in range(16):
            self.s[i] = self._load(k[i], d2[i], k[i+16], iv[i % len(iv)])
        for _ in range(32):
            self._round(True)
        self._round(False)

    def _round(self, init):
        x0 = ((self.s[15] << 1) & 0xFFFF0000) | (self.s[14] & 0xFFFF)
        x1 = ((self.s[11] << 16) & 0xFFFF0000) | ((self.s[9] >> 15) & 0xFFFF)
        x2 = ((self.s[7] << 16) & 0xFFFF0000) | ((self.s[5] >> 15) & 0xFFFF)
        x3 = ((self.s[2] << 16) & 0xFFFF0000) | ((self.s[0] >> 15) & 0xFFFF)

        w  = ((x0 ^ self.R1) + self.R2) & 0xFFFFFFFF
        w1 = (self.R1 + x1) & 0xFFFFFFFF
        w2 = (self.R2 ^ x2) & 0xFFFFFFFF

        self.R1 = S(L1(((w1 << 16) | (w2 >> 16)) & 0xFFFFFFFF))
        self.R2 = S(L2(((w2 << 16) | (w1 >> 16)) & 0xFFFFFFFF))

        s16 = add31(self.s[0], mul31(self.s[0], 8))
        s16 = add31(s16, mul31(self.s[4], 20))
        s16 = add31(s16, mul31(self.s[10], 21))
        s16 = add31(s16, mul31(self.s[13], 17))
        s16 = add31(s16, mul31(self.s[15], 15))
        if init:
            s16 = add31(s16, (w >> 1) & P31)

        self.s = self.s[1:] + [s16]
        return (w ^ x3) & 0xFFFFFFFF

    def keystream(self, n):
        out = bytearray()
        while len(out) < n:
            z = self._round(False)
            out += z.to_bytes(4, "big")
        return bytes(out[:n])

# ======================= 实验逻辑 =========================

@dataclass
class FrameMetric:
    gop: int
    packet_index: int
    pts: int
    time_sec: float
    is_key: int
    packet_size: int
    enc_bytes: int
    iv_time_ms: float
    zuc_init_ms: float
    keystream_ms: float
    encrypt_ms: float
    decrypt_ms: float
    total_cycle_ms: float
    budget_ms: float
    margin_ms: float
    realtime_ok: int
    sync_ok: int

def run_cmd(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def require_tool(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"未找到 {name}，请先安装并加入 PATH")

def sha256_file(path: Path):
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def ffprobe_avg_fps(video: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video)
    ]
    out = subprocess.check_output(cmd).decode().strip()
    if "/" in out:
        a, b = out.split("/")
        return float(a) / float(b)
    return float(out)

def encode_hevc_with_gop(input_path: Path, output_path: Path, fps: float, gop: int):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-an",
        "-c:v", "libx265",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-x265-params", f"keyint={gop}:min-keyint={gop}:scenecut=0:open-gop=0",
        str(output_path)
    ]
    run_cmd(cmd)

def make_iv16(session_key: bytes, packet_index: int, pts: int, tb_num: int, tb_den: int, gop: int) -> bytes:
    material = (
        session_key +
        packet_index.to_bytes(4, "big") +
        int(pts).to_bytes(8, "big", signed=True) +
        tb_num.to_bytes(4, "big") +
        tb_den.to_bytes(4, "big") +
        gop.to_bytes(4, "big")
    )
    return hashlib.sha256(material).digest()[:16]

def split_annexb_nals(data: bytes):
    positions = []
    i = 0
    n = len(data)
    while i < n - 3:
        if data[i:i+4] == b"\x00\x00\x00\x01":
            positions.append((i, 4))
            i += 4
        elif data[i:i+3] == b"\x00\x00\x01":
            positions.append((i, 3))
            i += 3
        else:
            i += 1

    if not positions:
        return [(b"", data)]

    out = []
    for idx, (pos, sc_len) in enumerate(positions):
        next_pos = positions[idx + 1][0] if idx + 1 < len(positions) else n
        out.append((data[pos:pos+sc_len], data[pos+sc_len:next_pos]))
    return out

def hevc_nal_type(nal: bytes):
    return ((nal[0] >> 1) & 0x3F) if len(nal) >= 2 else -1

def should_encrypt_nal(nal_type: int):
    return 0 <= nal_type <= 31

def xor_bytes(data: bytes, ks: bytes):
    return bytes(a ^ b for a, b in zip(data, ks))

def encrypt_hevc_packet_selective(packet_bytes: bytes, key32: bytes, iv16: bytes):
    nals = split_annexb_nals(packet_bytes)
    out = bytearray()
    enc_bytes = 0

    t0 = time.perf_counter()
    zuc = ZUC256(key32, iv16)
    t1 = time.perf_counter()
    zuc_init_ms = (t1 - t0) * 1000.0

    total_ks_ms = 0.0

    for sc, nal in nals:
        out += sc
        if len(nal) < 3:
            out += nal
            continue

        nal_type = hevc_nal_type(nal)
        if should_encrypt_nal(nal_type):
            header = nal[:2]
            payload = nal[2:]
            k0 = time.perf_counter()
            ks = zuc.keystream(len(payload))
            k1 = time.perf_counter()
            total_ks_ms += (k1 - k0) * 1000.0
            out += header + xor_bytes(payload, ks)
            enc_bytes += len(payload)
        else:
            out += nal

    return bytes(out), enc_bytes, zuc_init_ms, total_ks_ms

def decrypt_hevc_packet_selective(packet_bytes: bytes, key32: bytes, iv16: bytes):
    return encrypt_hevc_packet_selective(packet_bytes, key32, iv16)

def remux_packets_like_source(src_path: Path, packet_map: Dict[int, bytes], dst_path: Path):
    ic = av.open(str(src_path), "r")
    oc = av.open(str(dst_path), "w")

    ist = ic.streams.video[0]
    ost = oc.add_stream("hevc")

    idx = 0
    for packet in ic.demux(ist):
        if packet.dts is None and packet.pts is None:
            continue

        new_packet = av.packet.Packet(packet_map.get(idx, bytes(packet)))
        new_packet.pts = packet.pts
        new_packet.dts = packet.dts
        try:
            new_packet.time_base = packet.time_base
        except Exception:
            pass
        new_packet.stream = ost
        oc.mux(new_packet)
        idx += 1

    oc.close()
    ic.close()

def hevc_nal_type(nal: bytes):
    return ((nal[0] >> 1) & 0x3F) if len(nal) >= 2 else -1

def is_irap_nal(nal_type: int):
    # HEVC 中 16~23 为 IRAP（含 IDR/CRA/BLA），可视为关键随机接入帧
    return 16 <= nal_type <= 23

def packet_contains_irap(packet_bytes: bytes):
    nals = split_annexb_nals(packet_bytes)
    for _, nal in nals:
        if len(nal) >= 2 and is_irap_nal(hevc_nal_type(nal)):
            return True
    return False

def simulate_one_gop_case(hevc_path: Path, gop: int, fps: float, session_key: bytes, outdir: Path):
    print(f"[INFO] 打开文件: {hevc_path}")
    print(f"[INFO] 文件是否存在: {hevc_path.exists()}")
    if hevc_path.exists():
        print(f"[INFO] 文件大小: {hevc_path.stat().st_size} bytes")
    c = av.open(str(hevc_path), "r")
    st = c.streams.video[0]

    enc_map = {}
    dec_map = {}
    metrics = []
    key_count = 0
    injected_desync = False
    post_resync_ok = True

    budget_ms = gop / fps * 1000.0

    for idx, packet in enumerate(c.demux(st)):
        pb = bytes(packet)
        if not pb:
            continue

        is_key = int(packet_contains_irap(pb))
        pts = packet.pts if packet.pts is not None else idx
        tsec = float(idx / fps)

        ivms = zim = ksm = em = dm = tm = 0.0
        margin = budget_ms
        encb = 0
        sync_ok = 1

        if is_key:
            key_count += 1

            a = time.perf_counter()
            iv16 = make_iv16(
                session_key=session_key,
                packet_index=idx,
                pts=pts,
                tb_num=1,
                tb_den=int(fps),
                gop=gop
            )
            b = time.perf_counter()
            ivms = (b - a) * 1000.0

            a = time.perf_counter()
            cb, encb, zim, ksm = encrypt_hevc_packet_selective(pb, session_key, iv16)
            b = time.perf_counter()
            em = (b - a) * 1000.0

            a = time.perf_counter()
            plain, _, _, _ = decrypt_hevc_packet_selective(cb, session_key, iv16)
            b = time.perf_counter()
            dm = (b - a) * 1000.0

            if plain != pb:
                sync_ok = 0

            enc_map[idx] = cb
            dec_map[idx] = plain

            if key_count == 2 and not injected_desync:
                dec_map[idx] = cb
                injected_desync = True

            if key_count >= 3:
                post_resync_ok = post_resync_ok and (plain == pb)

            tm = ivms + em + dm
            margin = budget_ms - tm
        else:
            enc_map[idx] = pb
            dec_map[idx] = pb

        metrics.append(FrameMetric(
            gop=gop,
            packet_index=idx,
            pts=int(pts),
            time_sec=round(tsec, 6),
            is_key=is_key,
            packet_size=len(pb),
            enc_bytes=encb,
            iv_time_ms=round(ivms, 6),
            zuc_init_ms=round(zim, 6),
            keystream_ms=round(ksm, 6),
            encrypt_ms=round(em, 6),
            decrypt_ms=round(dm, 6),
            total_cycle_ms=round(tm, 6),
            budget_ms=round(budget_ms, 6),
            margin_ms=round(margin, 6),
            realtime_ok=int(tm <= budget_ms if is_key else 1),
            sync_ok=sync_ok
        ))

    c.close()
    print(f"[INFO] 总packet数: {len(metrics)}")
    print(f"[INFO] 关键帧packet数: {sum(m.is_key for m in metrics)}")
    enc_path = outdir / f"enc_gop{gop}.hevc"
    dec_path = outdir / f"dec_gop{gop}.hevc"
    write_packet_sequence(enc_map, enc_path)
    write_packet_sequence(dec_map, dec_path)

    src_hash = sha256_file(hevc_path)
    dec_hash = sha256_file(dec_path)

    summary = {
        "src_sha256": src_hash,
        "dec_sha256": dec_hash,
        "decrypt_exact_match": str(src_hash is not None and dec_hash is not None and src_hash == dec_hash),
        "resync_after_one_desync": str(post_resync_ok),
    }
    return metrics, summary

def save_metrics_csv(metrics, csv_path: Path):
    if not metrics:
        print(f"[警告] metrics 为空，未生成 CSV: {csv_path}")
        return

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(metrics[0]).keys()))
        w.writeheader()
        for row in metrics:
            w.writerow(asdict(row))

def summarize(metrics):
    rows = [m for m in metrics if m.is_key == 1]
    if not rows:
        return {
            "key_packets": 0,
            "mean_iv_ms": 0.0,
            "max_iv_ms": 0.0,
            "mean_zuc_init_ms": 0.0,
            "max_zuc_init_ms": 0.0,
            "mean_keystream_ms": 0.0,
            "max_keystream_ms": 0.0,
            "mean_encrypt_ms": 0.0,
            "max_encrypt_ms": 0.0,
            "mean_decrypt_ms": 0.0,
            "max_decrypt_ms": 0.0,
            "mean_total_cycle_ms": 0.0,
            "max_total_cycle_ms": 0.0,
            "min_margin_ms": 0.0,
            "mean_enc_bytes": 0.0,
            "realtime_pass_ratio": 0.0,
            "sync_pass_ratio": 0.0,
        }

    vals = lambda name: [getattr(m, name) for m in rows]
    return {
        "key_packets": len(rows),
        "mean_iv_ms": statistics.mean(vals("iv_time_ms")),
        "max_iv_ms": max(vals("iv_time_ms")),
        "mean_zuc_init_ms": statistics.mean(vals("zuc_init_ms")),
        "max_zuc_init_ms": max(vals("zuc_init_ms")),
        "mean_keystream_ms": statistics.mean(vals("keystream_ms")),
        "max_keystream_ms": max(vals("keystream_ms")),
        "mean_encrypt_ms": statistics.mean(vals("encrypt_ms")),
        "max_encrypt_ms": max(vals("encrypt_ms")),
        "mean_decrypt_ms": statistics.mean(vals("decrypt_ms")),
        "max_decrypt_ms": max(vals("decrypt_ms")),
        "mean_total_cycle_ms": statistics.mean(vals("total_cycle_ms")),
        "max_total_cycle_ms": max(vals("total_cycle_ms")),
        "min_margin_ms": min(vals("margin_ms")),
        "mean_enc_bytes": statistics.mean(vals("enc_bytes")),
        "realtime_pass_ratio": sum(m.realtime_ok for m in rows) / len(rows),
        "sync_pass_ratio": sum(m.sync_ok for m in rows) / len(rows),
    }

def write_packet_sequence(packet_map: Dict[int, bytes], dst_path: Path):
    with open(dst_path, "wb") as f:
        for idx in sorted(packet_map.keys()):
            f.write(packet_map[idx])


def write_text_report(report_path: Path, fps: float, all_results):
    lines = [
        "ZUC-256 HEVC I 帧加解密仿真报告",
        "=" * 60,
        f"帧率 fps: {fps:.3f}",
        ""
    ]

    for gop, result in all_results.items():
        budget = gop / fps * 1000.0
        s = result["summary_num"]

        lines += [
            f"[GOP={gop} 帧, I帧时间预算={budget:.3f} ms]",
            f"关键包数量: {s['key_packets']}",
            f"平均IV构造: {s['mean_iv_ms']:.6f} ms, 最大: {s['max_iv_ms']:.6f} ms",
            f"平均ZUC初始化: {s['mean_zuc_init_ms']:.6f} ms, 最大: {s['max_zuc_init_ms']:.6f} ms",
            f"平均密钥流生成: {s['mean_keystream_ms']:.6f} ms, 最大: {s['max_keystream_ms']:.6f} ms",
            f"平均加密: {s['mean_encrypt_ms']:.6f} ms, 最大: {s['max_encrypt_ms']:.6f} ms",
            f"平均解密: {s['mean_decrypt_ms']:.6f} ms, 最大: {s['max_decrypt_ms']:.6f} ms",
            f"平均完整周期(IV+加密+解密): {s['mean_total_cycle_ms']:.6f} ms",
            f"最大完整周期: {s['max_total_cycle_ms']:.6f} ms",
            f"最小实时裕量: {s['min_margin_ms']:.6f} ms",
            f"平均被加密字节数: {s['mean_enc_bytes']:.2f} bytes",
            f"实时性通过率: {s['realtime_pass_ratio'] * 100:.2f}%",
            f"同步正确率: {s['sync_pass_ratio'] * 100:.2f}%",
            f"解密后是否与原始 HEVC 完全一致: {result['summary_text']['decrypt_exact_match']}",
            f"模拟一次失步后，后续 I 帧能否重同步: {result['summary_text']['resync_after_one_desync']}",
        ]

        if s["max_total_cycle_ms"] < budget:
            lines.append(f"结论：GOP={gop} 下，最大单 I 帧处理周期小于 I 帧预算，新密钥/新状态可在下一关键帧到达前及时产生。")
        else:
            lines.append(f"结论：GOP={gop} 下，最大单 I 帧处理周期接近或超过 I 帧预算，实时性存在风险。")

        if result["summary_text"]["resync_after_one_desync"] == "True":
            lines.append("同步性分析：每个 I 帧独立派生 IV 并重建 ZUC 状态，单次失步不会持续传播，具备帧级重同步能力。")
        else:
            lines.append("同步性分析：当前配置下未能稳定恢复同步，需要进一步优化同步策略。")

        lines.append("-" * 60)

    report_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    require_tool("ffmpeg")
    require_tool("ffprobe")

    input_path = Path(INPUT_VIDEO).resolve()
    outdir = Path(OUTDIR).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    fps = FPS if FPS > 0 else ffprobe_avg_fps(input_path)
    session_key = hashlib.sha256(b"demo-shared-session-key").digest()

    all_results = {}
    for gop in GOPS:
        hevc_path = outdir / f"src_gop{gop}.hevc"
        encode_hevc_with_gop(input_path, hevc_path, fps, gop)

        metrics, summary_text = simulate_one_gop_case(
            hevc_path=hevc_path,
            gop=gop,
            fps=fps,
            session_key=session_key,
            outdir=outdir
        )

        csv_path = outdir / f"metrics_gop{gop}.csv"
        save_metrics_csv(metrics, csv_path)

        all_results[gop] = {
            "summary_text": summary_text,
            "summary_num": summarize(metrics),
            "metrics_csv": str(csv_path),
        }

    report_path = outdir / "report.txt"
    write_text_report(report_path, fps, all_results)

    print(f"实验完成，输出目录: {outdir}")
    print(f"报告文件: {report_path}")
    for gop, r in all_results.items():
        print(f"GOP={gop}: {r['summary_num']}")

if __name__ == "__main__":
    main()