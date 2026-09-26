# Stargazer2 260926
# コミットメッセージ: 標高考慮対象地点における「標高考慮/全層雲量」のセル左右2色分割表示および数値並記（35 / 70）の実装

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
import time
import os
import sys

# src/ 配下からの相対インポートまたは codes パッケージの読み込み
sys.path.insert(0, os.path.dirname(__file__))

from codes.config import (
    APP_TITLE, COLORS, LOCATIONS_FILE, WEATHER_FILE, APP_CONFIG_FILE,
    DEFAULT_ELEVATION_THRESHOLD, DEFAULT_WIND_THRESHOLD,
    MAX_API_RETRIES, RETRY_DELAY_SEC
)
from codes.models import Location, CellPrecomputed
from codes.storage import (
    load_locations, save_locations, ensure_elevations,
    load_weather_data, save_weather_data,
    load_app_config, save_app_config
)
from codes.weather_analyzer import precompute_all
from codes.api_client import fetch_location_weather
from codes.ui_components import WeatherGrid
from codes.ui_location_dlg import LocationManagerDialog


class StarGazer2App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=COLORS["bg"])

        # アプリ設定読み込み
        self.app_config = load_app_config()
        init_geom = self.app_config.get("geometry", "1180x680")
        self.root.geometry(init_geom)

        # 表示モード状態
        self.view_mode = self.app_config.get("view_mode", "3h")         # "3h" or "1h"
        self.cloud_mode = self.app_config.get("cloud_mode", "elevation") # "elevation" or "total"
        self.wind_threshold = float(self.app_config.get("wind_threshold", DEFAULT_WIND_THRESHOLD))
        self.elev_threshold = float(self.app_config.get("elevation_threshold", DEFAULT_ELEVATION_THRESHOLD))

        # データ管理
        self.locations = load_locations()
        self.weather_data = load_weather_data()
        self.precomputed_cache = {}

        # フェッチスレッド状態
        self.is_fetching = False
        self.cancel_fetch_flag = False

        # スタイル設定
        self.setup_styles()

        # UI構築
        self.create_ui()

        # ウィンドウ終了イベント
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初回起動時の標高チェック＆キャッシュ初期化
        self.init_data()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Header.TFrame", background=COLORS["header_bg"])
        style.configure("TLabel", background=COLORS["header_bg"], foreground=COLORS["text"])

        # 標準ボタン
        style.configure(
            "TButton",
            background=COLORS["header_bg"],
            foreground=COLORS["text"],
            borderwidth=1,
            focuscolor=COLORS["border"],
            font=("Meiryo", 9)
        )
        style.map(
            "TButton",
            background=[("active", COLORS["border"]), ("pressed", COLORS["accent"])],
            foreground=[("active", "#ffffff")]
        )

        # 強調ボタン
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="#0f172a",
            font=("Meiryo", 9, "bold"),
            borderwidth=1
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLORS["accent_hover"])],
            foreground=[("active", "#ffffff")]
        )

        # トグルONボタン
        style.configure(
            "ToggleOn.TButton",
            background=COLORS["accent"],
            foreground="#0f172a",
            font=("Meiryo", 9, "bold"),
            borderwidth=1
        )
        style.map(
            "ToggleOn.TButton",
            background=[("active", COLORS["accent_hover"])],
            foreground=[("active", "#ffffff")]
        )

        # 中止ボタン用スタイル
        style.configure(
            "Danger.TButton",
            background=COLORS["danger"],
            foreground="#ffffff",
            font=("Meiryo", 9, "bold"),
            borderwidth=1
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#dc2626")],
            foreground=[("active", "#ffffff")]
        )

    def create_ui(self):
        # --- 上部コントロールパネル ---
        control_frame = ttk.Frame(self.root, style="Header.TFrame", padding=(10, 6))
        control_frame.pack(fill="x")

        # 左側: タイトル ＆ 地点数 ＆ 地点管理ボタン
        title_lbl = ttk.Label(
            control_frame, text="StarGazer2", font=("Arial", 13, "bold"),
            foreground=COLORS["accent"]
        )
        title_lbl.pack(side="left", padx=(4, 10))

        self.count_lbl = ttk.Label(
            control_frame, text=f"観測地点 ({len(self.locations)})", font=("Meiryo", 9)
        )
        self.count_lbl.pack(side="left", padx=(0, 6))

        ttk.Button(
            control_frame, text="地点管理...", command=self.open_location_manager
        ).pack(side="left", padx=4)

        # 区切り
        ttk.Separator(control_frame, orient="vertical").pack(side="left", fill="y", padx=8, pady=2)

        # 表示切替ボタングループ
        # 1. 時間間隔切替 (3時間 / 詳細1h)
        self.btn_view_mode = ttk.Button(
            control_frame,
            text="時間: 3時間" if self.view_mode == "3h" else "時間: 詳細(1h)",
            command=self.toggle_view_mode
        )
        self.btn_view_mode.pack(side="left", padx=3)

        # 2. 雲量評価モード切替 (標高考慮 / 総雲量)
        self.btn_cloud_mode = ttk.Button(
            control_frame,
            text="判定: 標高考慮" if self.cloud_mode == "elevation" else "判定: 総雲量",
            command=self.toggle_cloud_mode
        )
        self.btn_cloud_mode.pack(side="left", padx=3)

        # 凡例表示（コンパクト）
        legend_frame = tk.Frame(control_frame, bg=COLORS["header_bg"])
        legend_frame.pack(side="left", padx=10)
        tk.Label(legend_frame, text="凡例:", bg=COLORS["header_bg"], fg=COLORS["text_dim"], font=("Meiryo", 8)).pack(side="left")
        tk.Label(legend_frame, text="■良", bg=COLORS["header_bg"], fg=COLORS["status_good"], font=("Meiryo", 8, "bold")).pack(side="left", padx=2)
        tk.Label(legend_frame, text="■可", bg=COLORS["header_bg"], fg=COLORS["status_fair"], font=("Meiryo", 8, "bold")).pack(side="left", padx=2)
        tk.Label(legend_frame, text="■不可", bg=COLORS["header_bg"], fg=COLORS["status_poor"], font=("Meiryo", 8, "bold")).pack(side="left", padx=2)
        tk.Label(legend_frame, text="[高地: 標高/全層]", bg=COLORS["header_bg"], fg=COLORS["accent"], font=("Meiryo", 8)).pack(side="left", padx=4)
        tk.Label(legend_frame, text="(赤字: 強風/霧)", bg=COLORS["header_bg"], fg=COLORS["danger"], font=("Meiryo", 8)).pack(side="left", padx=2)

        # 右側: 更新ボタン ＆ 最終更新日時 ＆ ステータス
        self.update_btn = ttk.Button(
            control_frame, text="更新", style="Accent.TButton", command=self.toggle_fetch
        )
        self.update_btn.pack(side="right", padx=5)

        self.last_updated_lbl = ttk.Label(control_frame, text="--/-- --:--", font=("Meiryo", 9))
        self.last_updated_lbl.pack(side="right", padx=6)
        self.update_last_updated_display()

        self.status_lbl = ttk.Label(control_frame, text="", foreground=COLORS["text_dim"], font=("Meiryo", 9))
        self.status_lbl.pack(side="right", padx=10)

        # --- メイングリッド ---
        self.grid = WeatherGrid(
            parent=self.root,
            root=self.root,
            get_locations=lambda: self.locations,
            get_precomputed_cache=lambda: self.precomputed_cache,
            get_all_times=lambda: self.weather_data.get("times", []),
            get_view_mode=lambda: self.view_mode,
            get_cloud_mode=lambda: self.cloud_mode
        )

    def init_data(self):
        """起動時の初期化（標高チェック・事前計算キャッシュ構築・初回描画）"""
        # 標高未設定地点の自動補完を非同期で確認
        def check_elevations():
            locs, updated = ensure_elevations(self.locations)
            if updated:
                self.locations = locs
                self.root.after(0, self.rebuild_cache_and_render)

        threading.Thread(target=check_elevations, daemon=True).start()

        # 既存データのキャッシュ構築と描画
        self.rebuild_cache_and_render()

    def rebuild_cache_and_render(self):
        """事前計算キャッシュを再生成してグリッドを再描画（高速）"""
        self.precomputed_cache = precompute_all(
            self.locations,
            self.weather_data,
            self.elev_threshold,
            self.wind_threshold
        )
        self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")
        self.grid.render()

    # --- モード切替アクション（再計算せず即座に切り替え） ---

    def toggle_view_mode(self):
        """3時間刻み と 詳細(1h) のトグル切替"""
        if self.view_mode == "3h":
            self.view_mode = "1h"
            self.btn_view_mode.config(text="時間: 詳細(1h)")
        else:
            self.view_mode = "3h"
            self.btn_view_mode.config(text="時間: 3時間")
        # 描画のみ更新（キャッシュがあるため一瞬で切り替わる）
        self.grid.render()

    def toggle_cloud_mode(self):
        """標高考慮 と 総雲量 のトグル切替"""
        if self.cloud_mode == "elevation":
            self.cloud_mode = "total"
            self.btn_cloud_mode.config(text="判定: 総雲量")
        else:
            self.cloud_mode = "elevation"
            self.btn_cloud_mode.config(text="判定: 標高考慮")
        # 描画のみ更新（キャッシュがあるため一瞬で切り替わる）
        self.grid.render()

    # --- 地点管理ダイアログ ---

    def open_location_manager(self):
        def on_locations_saved(new_locations: list[Location]):
            self.locations = new_locations
            save_locations(self.locations)
            self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")
            self.rebuild_cache_and_render()

        LocationManagerDialog(self.root, self.locations, on_locations_saved)

    # --- データ取得・更新処理 ---

    def toggle_fetch(self):
        if self.is_fetching:
            # 中止リクエスト
            self.cancel_fetch_flag = True
            self.status_lbl.config(text="中止中...", foreground=COLORS["danger"])
            self.update_btn.config(state="disabled")
        else:
            # 取得開始
            self.is_fetching = True
            self.cancel_fetch_flag = False
            self.update_btn.config(text="中止", style="Danger.TButton")
            thread = threading.Thread(target=self._fetch_process, daemon=True)
            thread.start()

    def _fetch_process(self):
        all_times_set = set()
        new_data_map = {}
        total = len(self.locations)

        try:
            for idx, loc in enumerate(self.locations):
                if self.cancel_fetch_flag:
                    break

                hourly_records = None
                # 初回取得 + 最大 MAX_API_RETRIES 回の再試行
                for attempt in range(MAX_API_RETRIES + 1):
                    if self.cancel_fetch_flag:
                        break

                    if attempt == 0:
                        status_msg = f"取得中 ({idx+1}/{total}): {loc.name}..."
                        status_col = COLORS["accent"]
                    else:
                        status_msg = f"再試行中 ({attempt}/{MAX_API_RETRIES}): {loc.name}..."
                        status_col = COLORS["status_fair"]
                        time.sleep(RETRY_DELAY_SEC)

                    self.root.after(
                        0, self.status_lbl.config,
                        {"text": status_msg, "foreground": status_col}
                    )

                    hourly_records = fetch_location_weather(loc.lat, loc.lng, loc.elevation)
                    if hourly_records:
                        break
                    else:
                        print(f"[{loc.name}] 取得失敗 (試行 {attempt + 1}/{MAX_API_RETRIES + 1})")

                if self.cancel_fetch_flag:
                    break

                # 2回再送信（計3回試行）しても回答が得られなかった場合
                if not hourly_records:
                    print(f"Communication error: Failed to get data for {loc.name} after retries.")
                    self.root.after(0, self.handle_connection_error, loc.name)
                    return

                new_data_map[loc.id] = hourly_records
                for t_iso in hourly_records.keys():
                    all_times_set.add(t_iso)

                # API負荷軽減のウェイト
                time.sleep(0.3)

            if not self.cancel_fetch_flag:
                sorted_times = sorted(list(all_times_set))
                # 既存データとマージして保存
                existing_data = self.weather_data.get("data", {})
                existing_data.update(new_data_map)

                save_payload = {
                    "updated_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "times": sorted_times,
                    "data": existing_data
                }
                self.weather_data = save_payload
                save_weather_data(save_payload)

                self.root.after(0, self.finish_fetch, "更新完了")
            else:
                self.root.after(0, self.finish_fetch, "更新中止")

        except Exception as e:
            print(f"Fetch Error: {e}")
            self.root.after(0, self.finish_fetch, "エラー発生")

    def handle_connection_error(self, loc_name: str):
        self.finish_fetch("通信エラーにより中止")
        messagebox.showerror(
            "通信エラー",
            f"「{loc_name}」の気象データ取得においてタイムアウトが発生し、再送信を2回試行しましたが応答が得られませんでした。\n\n"
            "通信状況またはAPIサーバーの状態を確認の上、時間をおいて再度お試しください。"
        )

    def finish_fetch(self, msg: str):
        self.is_fetching = False
        self.update_btn.config(text="更新", style="Accent.TButton", state="normal")
        fg_col = COLORS["danger"] if ("エラー" in msg or "中止" in msg) else COLORS["text"]
        self.status_lbl.config(text=msg, foreground=fg_col)

        if msg == "更新完了":
            self.update_last_updated_display()
            self.rebuild_cache_and_render()

        self.root.after(4000, lambda: self.status_lbl.config(text=""))

    def update_last_updated_display(self):
        updated_at = self.weather_data.get("updated_at")
        if updated_at:
            self.last_updated_lbl.config(text=f"最終更新: {updated_at}")
        else:
            self.last_updated_lbl.config(text="未更新")

    # --- 終了時処理 ---

    def on_closing(self):
        try:
            self.app_config["geometry"] = self.root.geometry()
            self.app_config["view_mode"] = self.view_mode
            self.app_config["cloud_mode"] = self.cloud_mode
            save_app_config(self.app_config)
        except Exception as e:
            print(f"Config Save Error: {e}")
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    # Windows高DPIスケーリング対応
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = StarGazer2App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
