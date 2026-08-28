
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fig 4-7: Δbitrate% (robust for raw .h265) + CPU% / FPS bar charts

核心修复：
- 对裸 .h265 无 duration 的情况：用 Δsize% 作为 Δbitrate%（同输入时长相同可约掉）
- 可选：指定 FPS，用 “帧数/FPS” 估算 duration，从而给出绝对 bitrate(bps)

依赖：
  - ffprobe 在 PATH（用于可选的帧数统计）
  - pip install pandas matplotlib
"""

import os
import subprocess
from pathlib import Path

import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

# =========================
# 1) 内部配置：改这里即可
# =========================

OUT_DIR = Path("./out_fig4_7")

ORIGINAL = r"D:/download/7aaf8-main/H264和H265测试影片/H265_1080.mp4"
VARIANTS = {
    "A_I-only": r"./out_fig4_5/A_I-only.h265",
    "B_P-only": r"./out_fig4_5/B_P-only.h265",
    "C_B-only": r"./out_fig4_5/C_B-only.h265",
    "D_I+P":    r"./out_fig4_5/D_I+P.h265",
    "E_I+P+B":  r"./out_fig4_5/E_I+P+B.h265",
}

# 性能数据（可选）。期望列：Config,cpu_percent,fps
PERF_CSV = r"./out_fig4_7/perf_results.csv"  # 不存在也没关系

# 若你需要“绝对码率(bps)”而不是只要 Δbitrate%：
# 给出正确帧率（必须与编码一致，比如 25/30/60）
USE_FPS_ESTIMATION_FOR_ABS_BITRATE = False
FPS = 25.0

# 矢量输出设置（论文友好）
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["svg.fonttype"] = "none"
mpl.rcParams["axes.unicode_minus"] = False


# =========================
# 2) 工具函数
# =========================
import numpy as np

def set_y_margin(values, top_margin=0.25, bottom_margin=0.15):
    """
    根据数据自动放大y轴范围：
      - top_margin: 上边留白比例（0.25 表示多留25%）
      - bottom_margin: 下边留白比例（有负值时生效）
    """
    v = np.array([x for x in values if np.isfinite(x)], dtype=float)
    if v.size == 0:
        return
    vmax = v.max()
    vmin = v.min()

    if vmin >= 0:
        plt.ylim(0, vmax * (1.0 + top_margin) if vmax != 0 else 1.0)
    else:
        up = vmax * (1.0 + top_margin) if vmax != 0 else 1.0
        down = vmin * (1.0 + bottom_margin)  # vmin是负值，乘(1+margin)会更“低”
        plt.ylim(down, up)





def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nstderr:\n{p.stderr}")
    return p.stdout

def file_size_bytes(path: str) -> int:
    return os.path.getsize(path)

def ffprobe_count_frames(video_path: str) -> int:
    """
    对裸 h265：用 -f hevc 明确指定格式，并用 -count_frames 统计读取帧数
    若失败，会抛异常；脚本中会自动兜底为 None
    """
    out = run([
        "ffprobe", "-v", "error",
        "-f", "hevc",
        "-count_frames",
        "-select_streams", "v:0",
        "-show_entries", "stream=nb_read_frames",
        "-of", "default=nokey=1:noprint_wrappers=1",
        video_path
    ]).strip()
    return int(out)

def bitrate_bps_via_fps(video_path: str, fps: float) -> float:
    """
    用 帧数 / FPS 估算 duration，再计算 bitrate = size*8 / duration
    """
    nframes = ffprobe_count_frames(video_path)
    duration = nframes / fps
    return file_size_bytes(video_path) * 8.0 / duration


# =========================
# 3) 主流程
# =========================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- (1) Δbitrate%：对裸码流用 Δsize% 代替（最稳） ---
    org_size = file_size_bytes(ORIGINAL)
    rows = []

    for name, path in VARIANTS.items():
        size = file_size_bytes(path)
        delta_pct = (size - org_size) / org_size * 100.0 if org_size > 0 else float("nan")

        row = {
            "Config": name,
            "size_bytes": size,
            "delta_bitrate_pct": delta_pct,  # 等价于 Δsize%（同一视频时长相同）
        }

        # 可选：给出绝对 bitrate(bps)
        if USE_FPS_ESTIMATION_FOR_ABS_BITRATE:
            try:
                row["bitrate_bps_est"] = bitrate_bps_via_fps(path, FPS)
            except Exception:
                row["bitrate_bps_est"] = float("nan")

        rows.append(row)

    df_br = pd.DataFrame(rows)
    df_br.to_csv(OUT_DIR / "bitrate_delta.csv", index=False, encoding="utf-8-sig")

    # Δbitrate% 柱状图（矢量）
    plt.figure()
    plt.bar(df_br["Config"], df_br["delta_bitrate_pct"])
    set_y_margin(df_br["delta_bitrate_pct"], top_margin=0.30, bottom_margin=0.20)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel("Δbitrate (%) vs Original")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig4_7_delta_bitrate.pdf")
    plt.savefig(OUT_DIR / "fig4_7_delta_bitrate.svg")
    plt.close()


    # --- (2) CPU占用与吞吐 fps（从CSV读取） ---
    perf_path = Path(PERF_CSV) if PERF_CSV else None
    if perf_path and perf_path.exists():
        dfp = pd.read_csv(perf_path)
        order = df_br["Config"].tolist()
        dfp = dfp.set_index("Config").reindex(order).reset_index()

        if "cpu_percent" in dfp.columns and dfp["cpu_percent"].notna().any():
            plt.figure()
            plt.bar(dfp["Config"], dfp["cpu_percent"])
            set_y_margin(dfp["cpu_percent"], top_margin=0.20, bottom_margin=0.10)
            plt.xticks(rotation=30, ha="right")
            plt.ylabel("CPU usage (%)")
            plt.tight_layout()
            plt.savefig(OUT_DIR / "fig4_7_cpu_bar.pdf")
            plt.savefig(OUT_DIR / "fig4_7_cpu_bar.svg")
            plt.close()


        if "fps" in dfp.columns and dfp["fps"].notna().any():
            plt.figure()
            plt.bar(dfp["Config"], dfp["fps"])
            set_y_margin(dfp["fps"], top_margin=0.15, bottom_margin=0.05)
            plt.xticks(rotation=30, ha="right")
            plt.ylabel("Throughput (fps)")
            plt.tight_layout()
            plt.savefig(OUT_DIR / "fig4_7_fps_bar.pdf")
            plt.savefig(OUT_DIR / "fig4_7_fps_bar.svg")
            plt.close()


    print(f"[DONE] Saved Fig4-7 outputs to: {OUT_DIR.resolve()}")
    print(" - fig4_7_delta_bitrate.pdf/.svg (Δbitrate% computed as Δsize%)")
    if perf_path and perf_path.exists():
        print(" - fig4_7_cpu_bar.pdf/.svg (if cpu_percent provided)")
        print(" - fig4_7_fps_bar.pdf/.svg (if fps provided)")
    print(" - bitrate_delta.csv")

if __name__ == "__main__":
    main()
