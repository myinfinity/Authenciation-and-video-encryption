#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图4-6：帧级 PSNR/SSIM 随帧号变化曲线（不同配置对比），并标注 I 帧位置

输入：
  - 原始视频（.h265 裸码流或 mp4/mkv/ts 均可，ffmpeg能解码即可）
  - A~E 加密后视频（同分辨率/同帧率/同帧数为佳）

输出：
  - out/fig4_6_psnr_curve.png
  - out/fig4_6_ssim_curve.png
  - out/psnr_per_frame.csv, out/ssim_per_frame.csv
  - out/frame_types.csv（用于记录I/P/B帧位置）

依赖：
  - ffmpeg, ffprobe 在 PATH
  - pip install numpy pandas opencv-python scikit-image matplotlib
"""

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import cv2
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import matplotlib.pyplot as plt


# =========================
# 1) 内部配置：修改这里即可
# =========================

OUT_DIR = Path("./out_fig4_6")
TMP_DIR = OUT_DIR / "tmp_frames"

ORIGINAL = r"D:/download/cb315-main/cb315-main/h265测试文件/surfing.265"   # 也可以是 original.mp4
VARIANTS = {
    "A_I-only": r"./out_fig4_5/A_I-only.h265",
    "B_P-only": r"./out_fig4_5/B_P-only.h265",
    "C_B-only": r"./out_fig4_5/C_B-only.h265",
    "D_I+P":    r"./out_fig4_5/D_I+P.h265",
    "E_I+P+B":  r"./out_fig4_5/E_I+P+B.h265",
}

MAX_FRAMES = 300          # 只算前多少帧（论文画图一般取几百帧就够）
USE_Y_CHANNEL = True      # True：只用Y通道算PSNR/SSIM（更贴近视觉）


# =========================
# 2) 工具函数
# =========================

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nstderr:\n{p.stderr}")
    return p.stdout

def ensure_paths():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    paths = [ORIGINAL] + list(VARIANTS.values())
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        raise FileNotFoundError("Missing file(s):\n" + "\n".join(missing))

def ffprobe_frame_types(video_path: str) -> pd.DataFrame:
    """
    读取每帧的 pict_type（I/P/B）与时间戳（可选）
    """
    out = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=pict_type,best_effort_timestamp_time",
        "-of", "json",
        video_path
    ])
    j = json.loads(out)
    frames = j.get("frames", [])
    rows = []
    for i, fr in enumerate(frames):
        rows.append({
            "n": i,
            "pict_type": fr.get("pict_type", ""),
            "t": float(fr.get("best_effort_timestamp_time", "0") or 0.0)
        })
    return pd.DataFrame(rows)

def ffmpeg_extract_frame_png(video_path: str, frame_idx: int, out_png: Path):
    """
    用 ffmpeg 按绝对帧号 n 抽取一帧到 PNG
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)
    vf = f"select=eq(n\\,{frame_idx})"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", video_path,
        "-vf", vf,
        "-vframes", "1",
        "-y", str(out_png)
    ])

def load_frame_array(png_path: Path, y_only: bool) -> np.ndarray:
    """
    读取 PNG → numpy，默认只取Y通道
    """
    img = cv2.imread(str(png_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(str(png_path))
    if not y_only:
        return img
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    return ycrcb[:, :, 0]  # Y

def get_frame_cached(video_path: str, tag: str, n: int, y_only: bool) -> np.ndarray:
    """
    抽帧并缓存到 TMP_DIR，避免重复抽取
    """
    png = TMP_DIR / f"{tag}_n{n}.png"
    if not png.exists():
        ffmpeg_extract_frame_png(video_path, n, png)
    return load_frame_array(png, y_only)

def calc_psnr_ssim(ref: np.ndarray, test: np.ndarray):
    """
    PSNR/SSIM 计算（uint8图像，data_range=255）
    """
    psnr = peak_signal_noise_ratio(ref, test, data_range=255)
    ssim = structural_similarity(ref, test, data_range=255)
    return float(psnr), float(ssim)


# =========================
# 3) 主流程：计算并绘图
# =========================

def main():
    ensure_paths()

    # 1) 解析帧类型，用于标注 I 帧位置
    ft = ffprobe_frame_types(ORIGINAL)
    ft.to_csv(OUT_DIR / "frame_types.csv", index=False, encoding="utf-8-sig")
    i_frames = ft.loc[ft["pict_type"] == "I", "n"].tolist()

    # 2) 限制计算帧数
    total_frames = int(ft["n"].max()) + 1 if not ft.empty else 0
    N = min(MAX_FRAMES, total_frames)
    ns = list(range(N))

    # 3) 预加载原始帧（作为参考）
    ref_frames = []
    for n in ns:
        ref_frames.append(get_frame_cached(ORIGINAL, "ORIG", n, USE_Y_CHANNEL))

    # 4) 逐配置计算 PSNR/SSIM
    psnr_map = {}
    ssim_map = {}

    for name, vpath in VARIANTS.items():
        psnrs, ssims = [], []
        for idx, n in enumerate(ns):
            test = get_frame_cached(vpath, name, n, USE_Y_CHANNEL)
            psnr, ssim = calc_psnr_ssim(ref_frames[idx], test)
            psnrs.append(psnr)
            ssims.append(ssim)
        psnr_map[name] = psnrs
        ssim_map[name] = ssims
        print(f"[OK] computed {name}")

    # 5) 导出 CSV
    df_psnr = pd.DataFrame({"n": ns, **psnr_map})
    df_ssim = pd.DataFrame({"n": ns, **ssim_map})
    df_psnr.to_csv(OUT_DIR / "psnr_per_frame.csv", index=False, encoding="utf-8-sig")
    df_ssim.to_csv(OUT_DIR / "ssim_per_frame.csv", index=False, encoding="utf-8-sig")

    # 6) 绘制 PSNR 曲线 + 标注 I 帧
    plt.figure()
    for name in VARIANTS.keys():
        plt.plot(ns, psnr_map[name], label=name)
    for n in i_frames:
        if n < N:
            plt.axvline(n, linewidth=0.6)  # 用默认颜色即可
    plt.xlabel("Frame index n")
    plt.ylabel("PSNR (dB)" + (" [Y]" if USE_Y_CHANNEL else ""))
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig4_6_psnr_curve.png", dpi=200)
    plt.close()

    # 7) 绘制 SSIM 曲线 + 标注 I 帧
    plt.figure()
    for name in VARIANTS.keys():
        plt.plot(ns, ssim_map[name], label=name)
    for n in i_frames:
        if n < N:
            plt.axvline(n, linewidth=0.6)
    plt.xlabel("Frame index n")
    plt.ylabel("SSIM" + (" [Y]" if USE_Y_CHANNEL else ""))
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig4_6_ssim_curve.png", dpi=200)
    plt.close()

    print(f"[DONE] Saved to: {OUT_DIR.resolve()}")
    print(" - fig4_6_psnr_curve.png")
    print(" - fig4_6_ssim_curve.png")
    print(" - psnr_per_frame.csv / ssim_per_frame.csv")
    print(" - frame_types.csv (I帧位置用于论文标注)")

if __name__ == "__main__":
    main()
