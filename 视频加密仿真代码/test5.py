#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图4-8：误差传播长度与重同步性能对比图
(1) 扰乱持续/恢复阈值帧数：基于图4-6导出的 ssim_per_frame.csv + frame_types.csv
(2) 丢包条件下重同步时间：基于“刷新点(锚点)”的蒙特卡洛仿真（不依赖容器duration）

输出（矢量图）：
  - out_fig4_8/fig4_8_recovery_frames.pdf/.svg
  - out_fig4_8/fig4_8_resync_time_ms.pdf/.svg
  - out_fig4_8/fig4_8_metrics.csv

依赖：
  pip install numpy pandas matplotlib
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt


# =========================
# 0) 内置输入路径（改这里）
# =========================
SSIM_CSV = Path(r"D:/学术方向/视频流加密/测试加密/out_fig4_6/ssim_per_frame.csv")      # 你的帧级SSIM结果
FRAME_TYPES_CSV = Path(r"D:/学术方向/视频流加密/测试加密/out_fig4_6/frame_types.csv") # 你的I/P/B标注（来自ffprobe）
OUT_DIR = Path("./out_fig4_8")

# =========================
# 1) 实验/仿真参数（按论文口径调整）
# =========================
FPS = 30.0                 # 用于把“帧数”换算成“时间(ms)”
PRE_W = 6                  # I帧前窗口：pre6
POST_SEARCH = 64           # 从I帧起最多搜索多少帧来判断“恢复”
ALPHA = 0.90               # 恢复阈值：SSIM >= ALPHA * pre_mean
ABS_THR = 0.80             # 同时满足绝对阈值更稳：SSIM >= max(ALPHA*pre_mean, ABS_THR)

# 丢包仿真：把“丢包”近似成“丢帧/关键数据导致该帧不可用”，统计到下一个刷新点的等待时间
LOSS_RATE = 0.01           # 丢包/丢帧概率（可改 1%/3%/5%）
SIM_RUNS = 200             # 蒙特卡洛重复次数（越大越稳定）
SEED = 2026

# =========================
# 2) 刷新点/锚点规则（用于重同步时间对比）
#    - I_ANCHOR: 以I帧为锚点刷新（你论文强调的机制）
#    - PERIODIC: 固定周期刷新（对比基线，可改周期）
#    - NONE: 不刷新（理论上不可恢复，这里用“到下一个I帧”近似作为上界）
# =========================
REFRESH_RULES = {
    "A_I-only":  ("I_ANCHOR", None),
    "B_P-only":  ("PERIODIC", 64),   # 例：无I锚定时只能靠固定周期（可改成GOP=32或更大）
    "C_B-only":  ("PERIODIC", 64),
    "D_I+P":     ("I_ANCHOR", None),
    "E_I+P+B":   ("I_ANCHOR", None),
}

# =========================
# 3) 矢量输出设置
# =========================
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["svg.fonttype"] = "none"
mpl.rcParams["axes.unicode_minus"] = False


# =========================
# 4) 计算：恢复阈值帧数
# =========================
def compute_recovery_lengths(ssim_series: np.ndarray, i_frames: np.ndarray,
                             pre_w=6, post_search=64, alpha=0.9, abs_thr=0.8):
    """
    对每个I帧 i0：
      pre_mean = mean(ssim[i0-pre_w : i0])
      thr = max(alpha*pre_mean, abs_thr)
      recovery_len = 最小 k>=0 使得 ssim[i0+k] >= thr （在0..post_search内搜索）
    返回：list[int] 每个I帧的恢复帧数；若找不到则记为 post_search+1
    """
    N = len(ssim_series)
    rec = []
    for i0 in i_frames:
        if i0 <= 0 or i0 >= N:
            continue
        pre_start = max(0, i0 - pre_w)
        pre_slice = ssim_series[pre_start:i0]
        if len(pre_slice) == 0:
            pre_mean = float(np.nanmean(ssim_series))
        else:
            pre_mean = float(np.nanmean(pre_slice))
        thr = max(alpha * pre_mean, abs_thr)

        found = False
        for k in range(0, post_search + 1):
            j = i0 + k
            if j >= N:
                break
            if np.isfinite(ssim_series[j]) and ssim_series[j] >= thr:
                rec.append(k)
                found = True
                break
        if not found:
            rec.append(post_search + 1)
    return np.array(rec, dtype=int)


# =========================
# 5) 计算：丢包条件下重同步时间（到下一个刷新点）
# =========================
def make_refresh_points(rule, period, i_frames, total_frames):
    if rule == "I_ANCHOR":
        pts = np.array(sorted(set([p for p in i_frames if 0 <= p < total_frames])), dtype=int)
        return pts
    if rule == "PERIODIC":
        if not period or period <= 0:
            period = 32
        pts = np.arange(0, total_frames, period, dtype=int)
        return pts
    if rule == "NONE":
        # 无刷新：理论不可恢复，这里用“下一I帧”当作上界
        pts = np.array(sorted(set([p for p in i_frames if 0 <= p < total_frames])), dtype=int)
        return pts
    # 默认兜底：I锚点
    pts = np.array(sorted(set([p for p in i_frames if 0 <= p < total_frames])), dtype=int)
    return pts

def next_refresh_delay_frames(loss_frame, refresh_points):
    """
    给定丢包发生在 frame n，返回到下一刷新点的等待帧数
    若n本身就是刷新点，则返回0；若后面没有刷新点，则返回NaN
    """
    idx = np.searchsorted(refresh_points, loss_frame, side="left")
    if idx >= len(refresh_points):
        return np.nan
    return int(refresh_points[idx] - loss_frame)

def simulate_resync_ms(total_frames, refresh_points, loss_rate, fps, runs=200, seed=0):
    """
    近似：每一帧独立以 loss_rate 发生丢包/不可用 -> 统计到下一刷新点的等待时间
    返回：平均重同步时间(ms)、P95(ms)
    """
    rng = np.random.default_rng(seed)
    delays = []
    for _ in range(runs):
        # 生成丢包帧索引
        mask = rng.random(total_frames) < loss_rate
        lost = np.where(mask)[0]
        for n in lost:
            d = next_refresh_delay_frames(n, refresh_points)
            if np.isfinite(d):
                delays.append(d / fps * 1000.0)
    if len(delays) == 0:
        return np.nan, np.nan
    delays = np.array(delays, dtype=float)
    return float(np.mean(delays)), float(np.percentile(delays, 95))


# =========================
# 6) 主流程：读CSV -> 计算 -> 画图
# =========================
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 读数据
    df_ssim = pd.read_csv(SSIM_CSV)
    df_ft = pd.read_csv(FRAME_TYPES_CSV)

    # I帧位置
    i_frames = df_ft.loc[df_ft["pict_type"] == "I", "n"].to_numpy(dtype=int)
    total_frames = int(df_ssim["n"].max()) + 1

    # 配置列（除n以外）
    configs = [c for c in df_ssim.columns if c != "n"]
    # 若你的列名与REFRESH_RULES不一致，建议在这里做映射；否则按交集取
    configs = [c for c in configs if c in REFRESH_RULES]

    # (1) 恢复帧数统计
    rec_rows = []
    for cfg in configs:
        ssim = df_ssim[cfg].to_numpy(dtype=float)
        rec = compute_recovery_lengths(ssim, i_frames,
                                       pre_w=PRE_W, post_search=POST_SEARCH,
                                       alpha=ALPHA, abs_thr=ABS_THR)
        rec_rows.append({
            "Config": cfg,
            "recovery_mean_frames": float(np.mean(rec)),
            "recovery_p95_frames": float(np.percentile(rec, 95)),
            "recovery_std_frames": float(np.std(rec)),
            "num_I_frames_used": int(len(rec)),
        })

    df_rec = pd.DataFrame(rec_rows).sort_values("Config")

    # 画：恢复帧数柱状图（均值 + 误差条=标准差）
    plt.figure()
    plt.bar(df_rec["Config"], df_rec["recovery_mean_frames"])
    plt.errorbar(df_rec["Config"], df_rec["recovery_mean_frames"],
                 yerr=df_rec["recovery_std_frames"], fmt="none", capsize=3)
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(f"Recovery length (frames)\nSSIM >= max({ALPHA}*pre{PRE_W}, {ABS_THR})")
    # y轴留白
    ymax = df_rec["recovery_mean_frames"].max() + df_rec["recovery_std_frames"].max()
    plt.ylim(0, ymax * 1.25 if ymax > 0 else 1.0)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig4_8_recovery_frames.pdf")
    plt.savefig(OUT_DIR / "fig4_8_recovery_frames.svg")
    plt.close()

    # (2) 重同步时间仿真（ms）
    resync_rows = []
    for cfg in configs:
        rule, period = REFRESH_RULES[cfg]
        refresh_pts = make_refresh_points(rule, period, i_frames, total_frames)
        mean_ms, p95_ms = simulate_resync_ms(total_frames, refresh_pts,
                                            loss_rate=LOSS_RATE, fps=FPS,
                                            runs=SIM_RUNS, seed=SEED)
        resync_rows.append({
            "Config": cfg,
            "refresh_rule": rule,
            "period_frames": period if period else "",
            "loss_rate": LOSS_RATE,
            "resync_mean_ms": mean_ms,
            "resync_p95_ms": p95_ms,
        })

    df_rs = pd.DataFrame(resync_rows).sort_values("Config")

    # 画：重同步时间柱状图
    plt.figure()
    plt.bar(df_rs["Config"], df_rs["resync_mean_ms"])
    plt.xticks(rotation=30, ha="right")
    plt.ylabel(f"Resync time (ms) under loss_rate={LOSS_RATE} (Monte Carlo)")
    # y轴留白
    ymax2 = np.nanmax(df_rs["resync_mean_ms"].to_numpy(dtype=float))
    plt.ylim(0, ymax2 * 1.25 if np.isfinite(ymax2) and ymax2 > 0 else 1.0)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "fig4_8_resync_time_ms.pdf")
    plt.savefig(OUT_DIR / "fig4_8_resync_time_ms.svg")
    plt.close()

    # 汇总导出
    df_out = df_rec.merge(df_rs, on="Config", how="left")
    df_out.to_csv(OUT_DIR / "fig4_8_metrics.csv", index=False, encoding="utf-8-sig")

    print(f"[DONE] Fig4-8 outputs -> {OUT_DIR.resolve()}")
    print(" - fig4_8_recovery_frames.pdf/.svg")
    print(" - fig4_8_resync_time_ms.pdf/.svg")
    print(" - fig4_8_metrics.csv (all numbers)")

if __name__ == "__main__":
    main()
