# ui_detail_dlg.py
# セルクリック時の詳細気象データポップアップ

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from .config import COLORS
from .models import Location
from .weather_analyzer import classify_aloft_cloud, classify_fog_level

COMPASS_DIRECTIONS = [
    "北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東",
    "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"
]

def degree_to_compass(deg: Optional[float]) -> str:
    if deg is None:
        return "--"
    val = int((deg / 22.5) + 0.5)
    return COMPASS_DIRECTIONS[val % 16]


def show_detail_dialog(parent: tk.Tk, loc: Location, time_iso: str, raw: Dict[str, Any]):
    """セル詳細情報を表示するモーダルダイアログ"""
    dlg = tk.Toplevel(parent)
    dlg.title(f"{loc.name} - 詳細予報")
    dlg.geometry("420x480")
    dlg.configure(bg=COLORS["bg"])
    dlg.transient(parent)
    dlg.grab_set()

    # タイトル部分
    header_frame = tk.Frame(dlg, bg=COLORS["header_bg"], padx=15, pady=10)
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text=f"{loc.name} (標高: {int(loc.elevation)}m)",
        bg=COLORS["header_bg"],
        fg=COLORS["accent"],
        font=("Meiryo", 12, "bold")
    ).pack(anchor="w")

    # 日時フォーマット (2026-09-23T15:00 -> 2026/09/23 15:00)
    time_str = time_iso.replace("T", " ")
    tk.Label(
        header_frame,
        text=f"予報日時: {time_str}",
        bg=COLORS["header_bg"],
        fg=COLORS["text_dim"],
        font=("Meiryo", 9)
    ).pack(anchor="w")

    # メインコンテンツ
    content_frame = tk.Frame(dlg, bg=COLORS["bg"], padx=15, pady=12)
    content_frame.pack(fill="both", expand=True)

    # データ取り出し
    tot = raw.get("cloud_cover")
    low = raw.get("cloud_cover_low")
    mid = raw.get("cloud_cover_mid")
    high = raw.get("cloud_cover_high")
    temp = raw.get("temperature_2m")
    dew = raw.get("dew_point_2m")
    hum = raw.get("relative_humidity_2m")
    wind_spd = raw.get("wind_speed_10m")
    wind_dir = raw.get("wind_direction_10m")
    precip = raw.get("precipitation")

    spread = (temp - dew) if (temp is not None and dew is not None) else None
    aloft_val = None
    if mid is not None and high is not None:
        aloft_val, _ = classify_aloft_cloud(float(mid), float(high))
        if tot is not None:
            aloft_val = min(aloft_val, float(tot))

    fog_lvl = classify_fog_level(temp or 0, dew or 0, hum or 0, wind_spd or 0)
    if not fog_lvl:
        fog_lvl = "低 (安全)"
    elif fog_lvl == "高":
        fog_lvl = "高 (視界不良・ガス警戒)"
    elif fog_lvl == "中":
        fog_lvl = "中 (雨上がり・放射冷却警戒)"
    elif fog_lvl == "露":
        fog_lvl = "結露注意 (ヒーター準備推奨)"

    # 低層雲アラート
    low_cloud_msg = "通常"
    if low is not None and float(low) >= 50.0:
        if loc.elevation >= 1500:
            low_cloud_msg = "雲海または山麓ガスの可能性"
        else:
            low_cloud_msg = "低層雲・霧の警戒"

    rows = [
        ("【雲量】", ""),
        ("  総雲量", f"{tot}%" if tot is not None else "--"),
        ("  中高層合成雲量", f"{round(aloft_val)}%" if aloft_val is not None else "--"),
        ("  高層雲 (約8km以上)", f"{high}%" if high is not None else "--"),
        ("  中層雲 (約3-8km)", f"{mid}%" if mid is not None else "--"),
        ("  低層雲 (地上-約3km)", f"{low}% ({low_cloud_msg})" if low is not None else "--"),
        ("【気象条件】", ""),
        ("  気温 / 露点温度", f"{temp}°C / {dew}°C" if (temp is not None and dew is not None) else "--"),
        ("  露点差 (T - Td)", f"{spread:.1f}°C" if spread is not None else "--"),
        ("  相対湿度", f"{hum}%" if hum is not None else "--"),
        ("  降水量 (前1時間)", f"{precip} mm" if precip is not None else "--"),
        ("【風・霧】", ""),
        ("  風速 / 風向", f"{wind_spd} m/s ({degree_to_compass(wind_dir)})" if wind_spd is not None else "--"),
        ("  霧・結露リスク", fog_lvl),
    ]

    for label, val in rows:
        row_frame = tk.Frame(content_frame, bg=COLORS["bg"])
        row_frame.pack(fill="x", pady=2)
        if label.startswith("【"):
            tk.Label(
                row_frame, text=label, bg=COLORS["bg"], fg=COLORS["accent"],
                font=("Meiryo", 9, "bold")
            ).pack(anchor="w")
        else:
            tk.Label(
                row_frame, text=label, bg=COLORS["bg"], fg=COLORS["text_dim"],
                font=("Meiryo", 9), width=18, anchor="w"
            ).pack(side="left")
            
            # 警告等の文字色
            fg_color = COLORS["text"]
            if "高" in val or "中" in val or "結露注意" in val:
                fg_color = COLORS["danger"]

            tk.Label(
                row_frame, text=val, bg=COLORS["bg"], fg=fg_color,
                font=("Meiryo", 9, "bold" if fg_color == COLORS["danger"] else "normal")
            ).pack(side="left")

    btn_frame = tk.Frame(dlg, bg=COLORS["bg"], pady=10)
    btn_frame.pack(fill="x")
    close_btn = ttk.Button(btn_frame, text="閉じる", command=dlg.destroy)
    close_btn.pack(side="right", padx=15)

    dlg.bind("<Escape>", lambda e: dlg.destroy())
