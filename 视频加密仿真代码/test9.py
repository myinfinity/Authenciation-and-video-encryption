
# -*- coding: utf-8 -*-
"""
按论文公式(均值/方差/协方差)计算相邻像素相关系数 Rxy
- 支持 HEVC .h265 AnnexB 或 mp4/mkv 等（由 ffmpeg 抽帧）
- 对每帧计算：水平/垂直/对角方向相关系数
- 输出类似“表5-3 相邻像素相关性”的结果

不使用命令行参数：改 CONFIG 后直接运行
"""

import json
import random
import subprocess
from typing import List, Tuple, Optional

import numpy as np
import cv2

# =========================
# CONFIG（改这里）
# =========================
PLAIN_VIDEO  = r"D:/download/0c6c6-main/0c6c6-main/h265_cap_files/h265_1.mp4"
CIPHER_VIDEO = r"encrypted.mp4"

NUM_FRAMES = 5
RANDOM_SEED = 20299

# 每个方向抽取的相邻像素对数量 N（论文常用 2000~10000）
N_PAIRS = 5000

# 是否统一resize（可选）
RESIZE_TO = None  # e.g. (640, 360) or None

# 指定固定帧号（若为空则随机抽）
FIXED_INDICES: List[int] = []  # e.g. [121,327,514,524,662]
# =========================


def run_cmd(cmd: List[str]) -> Tuple[int, bytes, bytes]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return p.returncode, out, err


def ffprobe_frame_count(path: str) -> Optional[int]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,avg_frame_rate:format=duration",
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
        return None

    s0 = streams[0]
    nb_frames = s0.get("nb_frames", None)
    if nb_frames not in (None, "N/A"):
        try:
            return int(nb_frames)
        except Exception:
            pass

    duration = fmt.get("duration", None)
    afr = s0.get("avg_frame_rate", None)
    if duration not in (None, "N/A") and afr not in (None, "N/A") and "/" in afr:
        try:
            duration = float(duration)
            num, den = afr.split("/", 1)
            num = float(num); den = float(den)
            if den != 0:
                fps = num / den
                return int(duration * fps)
        except Exception:
            return None
    return None


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
            f"ffmpeg extract frame {frame_idx} failed for {path}:\n{err.decode(errors='ignore')}"
        )
    return out


def png_bytes_to_bgr(png_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Failed to decode PNG bytes.")
    if RESIZE_TO is not None:
        img = cv2.resize(img, RESIZE_TO, interpolation=cv2.INTER_AREA)
    return img


def to_gray_u8(img_bgr: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if g.dtype != np.uint8:
        g = np.clip(g, 0, 255).astype(np.uint8)
    return g


# -------------------- 核心：按公式计算相关系数 --------------------
def corr_by_formula(x: np.ndarray, y: np.ndarray) -> float:
    """
    严格按论文公式计算 Rxy：
      E(x), E(y), D(x), D(y), cov(x,y) -> Rxy
    x,y: 一维数组，长度 N
    """
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
    if denom == 0:
        return 0.0
    return float(cov / denom)


import numpy as np
import cv2

def sample_pairs_edge(gray: np.ndarray, N: int, mode: str, grad_thresh: int = 20):
    """
    只在“高梯度(纹理/边缘)”区域采样相邻像素对，避免平坦块导致 r≈1
    grad_thresh: 越大越严格（建议 10~40 试）
    """
    H, W = gray.shape

    # 梯度幅值（Sobel）
    gx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
    mag = (np.abs(gx) + np.abs(gy)).astype(np.int32)

    # 方向有效区域（保证邻居存在）
    if mode == 'h':
        valid = np.zeros_like(gray, dtype=bool)
        valid[:, :-1] = True
    elif mode == 'v':
        valid = np.zeros_like(gray, dtype=bool)
        valid[:-1, :] = True
    elif mode == 'd':
        valid = np.zeros_like(gray, dtype=bool)
        valid[:-1, :-1] = True
    else:
        raise ValueError("mode must be 'h','v','d'")

    mask = (mag >= grad_thresh) & valid
    xs, ys = np.where(mask)

    # 若边缘点太少，放宽阈值或退化为全图采样
    if len(xs) < 100:
        # 退化：全图随机（避免无样本）
        if mode == 'h':
            xs = np.random.randint(0, H, size=N)
            ys = np.random.randint(0, W - 1, size=N)
        elif mode == 'v':
            xs = np.random.randint(0, H - 1, size=N)
            ys = np.random.randint(0, W, size=N)
        else:
            xs = np.random.randint(0, H - 1, size=N)
            ys = np.random.randint(0, W - 1, size=N)
    else:
        idx = np.random.choice(len(xs), size=N, replace=len(xs) < N)
        xs, ys = xs[idx], ys[idx]

    x = gray[xs, ys]
    if mode == 'h':
        y = gray[xs, ys + 1]
    elif mode == 'v':
        y = gray[xs + 1, ys]
    else:
        y = gray[xs + 1, ys + 1]

    return x, y


def corr_by_formula(x: np.ndarray, y: np.ndarray) -> float:
    x = x.astype(np.float64); y = y.astype(np.float64)
    N = x.size
    Ex = np.sum(x) / N
    Ey = np.sum(y) / N
    Dx = np.sum((x - Ex) ** 2) / N
    Dy = np.sum((y - Ey) ** 2) / N
    cov = np.sum((x - Ex) * (y - Ey)) / N
    denom = np.sqrt(Dx) * np.sqrt(Dy)
    return float(cov / denom) if denom != 0 else 0.0


def adjacent_corr_for_frame_edge(gray: np.ndarray, N: int, grad_thresh: int = 20):
    xh, yh = sample_pairs_edge(gray, N, 'h', grad_thresh)
    xv, yv = sample_pairs_edge(gray, N, 'v', grad_thresh)
    xd, yd = sample_pairs_edge(gray, N, 'd', grad_thresh)
    return corr_by_formula(xh, yh), corr_by_formula(xv, yv), corr_by_formula(xd, yd)


def pick_indices() -> List[int]:
    if FIXED_INDICES:
        return FIXED_INDICES[:NUM_FRAMES]

    n1 = ffprobe_frame_count(PLAIN_VIDEO)
    n2 = ffprobe_frame_count(CIPHER_VIDEO)
    if n1 is None or n2 is None:
        raise RuntimeError("无法获得帧数，建议先将 .h265 remux 成 mp4。")
    n = min(n1, n2)
    if n <= 0:
        raise RuntimeError("帧数为0。")

    random.seed(RANDOM_SEED)
    return sorted(random.sample(range(n), k=min(NUM_FRAMES, n)))


def main():
    np.random.seed(RANDOM_SEED)

    indices = pick_indices()
    print(f"Sample frames: {indices}\n")

    # 先算明文（只取第一帧当“明文”行，也可取平均）
    # 这里按你截图表 5-3 的写法：明文 1 行 + 密文多行
    p_png = extract_frame_png_bytes(PLAIN_VIDEO, indices[0])
    p_gray = to_gray_u8(png_bytes_to_bgr(p_png))
    rh_p, rv_p, rd_p = adjacent_corr_for_frame_edge(p_gray, N_PAIRS, grad_thresh=30)

    print("表：相邻像素相关性（按公式计算）")
    print("{:<8} {:>10} {:>10} {:>10}".format("图像(帧)", "水平方向", "垂直方向", "对角方向"))
    print("{:<8} {:>10.4f} {:>10.4f} {:>10.4f}".format("明文", rh_p, rv_p, rd_p))

    # 密文：对每个抽样帧算一次
    for i, idx in enumerate(indices, start=1):
        c_png = extract_frame_png_bytes(CIPHER_VIDEO, idx)
        c_gray = to_gray_u8(png_bytes_to_bgr(c_png))
        rh_c, rv_c, rd_c = adjacent_corr_for_frame_edge(c_gray, N_PAIRS, grad_thresh=30)

        print("{:<8} {:>10.4f} {:>10.4f} {:>10.4f}".format(f"密文{i}", rh_c, rv_c, rd_c))


if __name__ == "__main__":
    main()
