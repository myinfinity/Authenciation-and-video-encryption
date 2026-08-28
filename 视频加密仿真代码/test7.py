# -*- coding: utf-8 -*-
"""
Randomly sample 5 matched frames from plaintext & ciphertext videos and compute SSIM/PSNR mean.
- No CLI args: edit the CONFIG section and run.
- Works for containers (mp4/mkv/avi/...) and raw HEVC (.h265/.hevc) via ffmpeg/ffprobe.
"""

import json
import random
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr


# =========================
# CONFIG (edit here)
# =========================
PLAIN_VIDEO  = r"D:/download/0c6c6-main/0c6c6-main/h265_cap_files/h265_1.mp4"        # 明文视频路径（可为 .h265 裸流 或 mp4 等）
CIPHER_VIDEO = r"encrypted_I_only.mp4"    # 密文视频路径（可播放/可被ffmpeg解析即可）

NUM_SAMPLES = 5
RANDOM_SEED = 2026

# 计算方式：灰度（推荐）或 Y 通道（需要额外转色空间）
USE_GRAYSCALE = True
# =========================


@dataclass
class VideoInfo:
    nb_frames: Optional[int]
    duration: Optional[float]
    avg_frame_rate: Optional[float]
    width: Optional[int]
    height: Optional[int]


def run_cmd(cmd: List[str]) -> Tuple[int, bytes, bytes]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return p.returncode, out, err


def ffprobe_info(path: str) -> VideoInfo:
    """
    Use ffprobe to get video stream info.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,avg_frame_rate,width,height:format=duration",
        "-of", "json",
        path
    ]
    rc, out, err = run_cmd(cmd)
    if rc != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{err.decode(errors='ignore')}")

    js = json.loads(out.decode("utf-8", errors="ignore"))
    streams = js.get("streams", [])
    fmt = js.get("format", {})

    if not streams:
        raise RuntimeError(f"No video stream found in {path}")

    s0 = streams[0]
    nb_frames = s0.get("nb_frames", None)
    nb_frames = int(nb_frames) if nb_frames not in (None, "N/A") else None

    afr = s0.get("avg_frame_rate", None)
    avg_frame_rate = None
    if afr and afr != "N/A" and "/" in afr:
        num, den = afr.split("/", 1)
        try:
            num = float(num); den = float(den)
            if den != 0:
                avg_frame_rate = num / den
        except Exception:
            avg_frame_rate = None

    width = s0.get("width", None)
    height = s0.get("height", None)
    width = int(width) if width not in (None, "N/A") else None
    height = int(height) if height not in (None, "N/A") else None

    duration = fmt.get("duration", None)
    duration = float(duration) if duration not in (None, "N/A") else None

    return VideoInfo(
        nb_frames=nb_frames,
        duration=duration,
        avg_frame_rate=avg_frame_rate,
        width=width,
        height=height
    )


def frame_count_fallback(info: VideoInfo) -> Optional[int]:
    """
    If nb_frames unavailable, approximate frames by duration*fps.
    """
    if info.nb_frames is not None:
        return info.nb_frames
    if info.duration is not None and info.avg_frame_rate is not None:
        return int(info.duration * info.avg_frame_rate)
    return None


def extract_frame_png_bytes(path: str, frame_idx: int) -> bytes:
    """
    Extract exactly one frame as PNG bytes using ffmpeg + select filter.
    Works for mp4/mkv and raw hevc (.h265) as long as ffmpeg can decode.
    """
    # -vsync 0 avoids duplicating/dropping frames
    # select='eq(n,IDX)' chooses exact decoded frame number
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
        raise RuntimeError(f"ffmpeg extract frame {frame_idx} failed for {path}:\n{err.decode(errors='ignore')}")
    return out


def png_bytes_to_bgr(png_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Failed to decode PNG bytes into image.")
    return img


def to_compare_plane(img_bgr: np.ndarray) -> np.ndarray:
    """
    Return a single-channel image for SSIM/PSNR.
    Default: grayscale (uint8).
    """
    if USE_GRAYSCALE:
        g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return g

    # Optional: use luma (Y) from YCrCb
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0]
    return y


def center_crop_to_same(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    ha, wa = a.shape[:2]
    hb, wb = b.shape[:2]
    h = min(ha, hb)
    w = min(wa, wb)

    def crop(x):
        hx, wx = x.shape[:2]
        y0 = (hx - h) // 2
        x0 = (wx - w) // 2
        return x[y0:y0+h, x0:x0+w]

    return crop(a), crop(b)


def compute_ssim_psnr(plain_1c: np.ndarray, cipher_1c: np.ndarray) -> Tuple[float, float]:
    # ensure uint8
    if plain_1c.dtype != np.uint8:
        plain_1c = np.clip(plain_1c, 0, 255).astype(np.uint8)
    if cipher_1c.dtype != np.uint8:
        cipher_1c = np.clip(cipher_1c, 0, 255).astype(np.uint8)

    plain_1c, cipher_1c = center_crop_to_same(plain_1c, cipher_1c)

    s = ssim(plain_1c, cipher_1c, data_range=255)
    p = psnr(plain_1c, cipher_1c, data_range=255)
    return float(s), float(p)


def main():
    info_p = ffprobe_info(PLAIN_VIDEO)
    info_c = ffprobe_info(CIPHER_VIDEO)

    n_p = frame_count_fallback(info_p)
    n_c = frame_count_fallback(info_c)
    if n_p is None or n_c is None:
        raise RuntimeError(
            "无法获得帧数（nb_frames和duration/fps都不可用）。\n"
            "建议先把 .h265 remux 成 mp4，或确保 ffprobe 能正确识别帧数。"
        )

    n = min(n_p, n_c)
    if n <= 0:
        raise RuntimeError("帧数为0，无法抽样。")

    random.seed(RANDOM_SEED)
    sample_k = min(NUM_SAMPLES, n)
    indices = sorted(random.sample(range(n), sample_k))

    results = []
    print(f"Plain frames: {n_p}, Cipher frames: {n_c}, Using min={n}")
    print(f"Sample indices ({sample_k}): {indices}\n")

    for idx in indices:
        p_png = extract_frame_png_bytes(PLAIN_VIDEO, idx)
        c_png = extract_frame_png_bytes(CIPHER_VIDEO, idx)

        p_bgr = png_bytes_to_bgr(p_png)
        c_bgr = png_bytes_to_bgr(c_png)

        p_1c = to_compare_plane(p_bgr)
        c_1c = to_compare_plane(c_bgr)

        s, p = compute_ssim_psnr(p_1c, c_1c)
        results.append((idx, s, p))
        print(f"frame={idx:6d}  SSIM={s:.6f}  PSNR={p:.3f} dB")

    ssim_mean = float(np.mean([r[1] for r in results]))
    psnr_mean = float(np.mean([r[2] for r in results]))
    print("\nAverages:")
    print(f"SSIM_mean = {ssim_mean:.6f}")
    print(f"PSNR_mean = {psnr_mean:.3f} dB")


if __name__ == "__main__":
    main()
