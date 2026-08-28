# -*- coding: utf-8 -*-
"""
Generate multiple Chi-square test results table like论文示例：
- Each sample = one frame (or one "case name")
- Compute p-value via chi-square test

Test mode (recommended):
  H0: Plain and Cipher grayscale histograms are from the SAME distribution
  -> Use chi-square test for homogeneity:
     chi2 = sum((O1 - E1)^2/E1 + (O2 - E2)^2/E2)
     where expected counts are based on pooled distribution.

No CLI args: edit CONFIG and run.
Outputs:
  - prints table
  - saves CSV: chi2_pvalues.csv
"""

import os
import csv
import json
import random
import subprocess
from typing import List, Tuple, Optional

import numpy as np
import cv2
from scipy.stats import chi2 as chi2_dist

# =========================
# CONFIG（改这里）
# =========================
PLAIN_VIDEO  = r"D:/download/0c6c6-main/0c6c6-main/h265_cap_files/h265_1.mp4"
CIPHER_VIDEO = r"encrypted_I_only.mp4"

# 生成多少组结果（对应表格多少行）
NUM_CASES = 10

# 抽样方式：随机抽帧（推荐做“多组”）
RANDOM_SEED = 2029

# 是否统一resize（避免分辨率差异）
RESIZE_TO = None  # e.g. (640, 360) or None

# 输出目录与文件名
OUT_DIR = r"./chi2_table_outputs"
OUT_CSV = "chi2_pvalues.csv"

# 可选：给每一行一个“测试图像名称”
# 若为空，则默认用 Frame_XXX
CASE_NAMES = [
    "Case1", "Case2", "Case3", "Case4", "Case5",
    "Case6", "Case7", "Case8", "Case9", "Case10"
]
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


def gray_hist_counts(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    return np.bincount(gray.ravel(), minlength=256).astype(np.int64)


def chi2_homogeneity_pvalue(h1: np.ndarray, h2: np.ndarray) -> Tuple[float, int, float]:
    """
    Chi-square test of homogeneity for two histograms.
    H0: both samples drawn from the same distribution.
    - pooled proportions define expected counts for each bin.
    - dof = bins-1 (with bins having nonzero total counts).
    """
    h1 = h1.astype(np.float64)
    h2 = h2.astype(np.float64)
    total = h1 + h2
    N1 = float(h1.sum())
    N2 = float(h2.sum())
    N = N1 + N2

    # mask bins with zero total to avoid 0/0
    m = total > 0
    h1 = h1[m]
    h2 = h2[m]
    total = total[m]

    # expected under H0
    p = total / N
    E1 = N1 * p
    E2 = N2 * p

    chi2 = float(np.sum((h1 - E1) ** 2 / E1) + np.sum((h2 - E2) ** 2 / E2))
    dof = int(len(total) - 1)
    pval = float(chi2_dist.sf(chi2, dof))
    return chi2, dof, pval


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    n1 = ffprobe_frame_count(PLAIN_VIDEO)
    n2 = ffprobe_frame_count(CIPHER_VIDEO)
    if n1 is None or n2 is None:
        raise RuntimeError("无法获得帧数。建议先将 .h265 remux 成 mp4。")

    n = min(n1, n2)
    if n <= 0:
        raise RuntimeError("帧数为0。")

    random.seed(RANDOM_SEED)
    frame_indices = sorted(random.sample(range(n), k=min(NUM_CASES, n)))

    rows = []
    for i, fidx in enumerate(frame_indices, start=1):
        p_png = extract_frame_png_bytes(PLAIN_VIDEO, fidx)
        c_png = extract_frame_png_bytes(CIPHER_VIDEO, fidx)
        p_bgr = png_bytes_to_bgr(p_png)
        c_bgr = png_bytes_to_bgr(c_png)

        hp = gray_hist_counts(p_bgr)
        hc = gray_hist_counts(c_bgr)

        chi2, dof, pval = chi2_homogeneity_pvalue(hp, hc)

        name = CASE_NAMES[i-1] if i-1 < len(CASE_NAMES) else f"Frame_{fidx}"
        rows.append([i, name, fidx, chi2, dof, pval])

    # 打印表格（控制台）
    print("\nChi-square test results (H0: Plain and Cipher have same gray distribution)")
    print("{:<4} {:<15} {:<10} {:<14} {:<6} {:<10}".format("No.", "Case", "Frame", "chi2", "dof", "p-value"))
    for r in rows:
        print("{:<4} {:<15} {:<10} {:<14.3f} {:<6d} {:<10.4g}".format(
            r[0], r[1], r[2], r[3], r[4], r[5]
        ))

    # 保存 CSV（论文做表很方便）
    out_csv_path = os.path.join(OUT_DIR, OUT_CSV)
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["No.", "Case", "FrameIndex", "Chi2", "DoF", "PValue"])
        for r in rows:
            w.writerow(r)

    print(f"\n[OK] Saved CSV -> {out_csv_path}")


if __name__ == "__main__":
    main()
