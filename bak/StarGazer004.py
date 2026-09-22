#StarGazer004.py
#前回と同じ大きさに開く
#Google AI Studio

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import requests
import json
import os
import datetime
import threading
import uuid
import time

# --- 設定 ---
TARGET_HOURS = [0, 3, 6, 12, 18, 21]
LOCATIONS_FILE = "locations.json"
WEATHER_FILE = "weather_data.json"
APP_CONFIG_FILE = "app_config.json"  # 【追加】設定ファイル名

# --- 配色設定 ---
COLORS = {
    "bg": "#0f172a",          # 全体の背景
    "header_bg": "#1e293b",   # ヘッダー背景
    "text": "#e2e8f0",        # 基本文字色
    "text_dim": "#94a3b8",    # 薄い文字色
    "border": "#334155",      # 枠線
    "accent": "#6366f1",      # アクセント (Indigo)
    "accent_hover": "#4f46e5",
    "danger": "#ef4444",      # 赤 (中止ボタン等)
    
    # 雲量ごとの色
    "cloud_0_15": "#38bdf8",  # <15%
    "cloud_text_0_15": "#082f49", 
    "cloud_15_25": "#fde047", # <25%
    "cloud_text_15_25": "#422006",
    "cloud_25_35": "#fb923c", # <35%
    "cloud_text_25_35": "#ffffff",
    "cloud_over": "#64748b",  # >=35%
    "cloud_text_over": "#e2e8f0",

    # 12:00 (正午)
    "noon_bg": "#facc15",     # 黄色
    "noon_text": "#0f172a"    # 黒
}

# --- デフォルトデータ ---
DEFAULT_LOCATIONS = [
    {"id": "1", "name": "幕張の浜", "lat": 35.640575, "lng": 140.035070},
    {"id": "2", "name": "野辺山", "lat": 35.9416, "lng": 138.4727}
]

# セルサイズ設定
CELL_WIDTH = 100
CELL_HEIGHT = 50
HEADER_HEIGHT = 40
SIDEBAR_WIDTH = 80

class StarGazerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StarGazer Cloud Forecast")
        self.root.configure(bg=COLORS["bg"])

        # 状態管理
        self.locations = self.load_json(LOCATIONS_FILE, DEFAULT_LOCATIONS)
        self.weather_data = self.load_json(WEATHER_FILE, {"updated_at": None, "data": {}, "times": []})
        
        # --- 【追加】アプリ設定（ウィンドウ位置・サイズ）の読み込み ---
        self.app_config = self.load_json(APP_CONFIG_FILE, {})
        # 保存されたジオメトリがあれば適用、なければデフォルト
        init_geometry = self.app_config.get("geometry", "1100x650")
        self.root.geometry(init_geometry)
        
        # --- 【追加】終了時イベントの登録 ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.is_fetching = False
        self.cancel_fetch_flag = False

        self.setup_styles()
        self.create_ui()
        
        # 起動時は保存されているデータを表示
        self.draw_grid()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Header.TFrame", background=COLORS["header_bg"])
        style.configure("TLabel", background=COLORS["header_bg"], foreground=COLORS["text"])
        
        # 標準ボタン
        style.configure("TButton", 
                        background=COLORS["header_bg"], 
                        foreground=COLORS["text"], 
                        borderwidth=1,
                        focuscolor=COLORS["border"])
        style.map("TButton", 
                  background=[("active", COLORS["accent"]), ("pressed", COLORS["accent"])],
                  foreground=[("active", "#ffffff")])
        
        # 中止ボタン用スタイル
        style.configure("Danger.TButton", 
                        background=COLORS["danger"], 
                        foreground="#ffffff", 
                        borderwidth=1)
        style.map("Danger.TButton", 
                  background=[("active", "#dc2626")],
                  foreground=[("active", "#ffffff")])

    def load_json(self, filename, default):
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return default
        return default

    def save_json(self, filename, data):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save Error: {e}")

    def create_ui(self):
        # --- 上部コントロールパネル ---
        control_frame = ttk.Frame(self.root, style="Header.TFrame", padding=10)
        control_frame.pack(fill="x")

        # タイトル
        ttk.Label(control_frame, text="StarGazer", font=("Arial", 14, "bold"), 
                  foreground=COLORS["accent"]).pack(side="left", padx=(5, 10))
        
        # 観測地点数ラベル
        self.count_lbl = ttk.Label(control_frame, text=f"観測地点 ({len(self.locations)})", font=("Meiryo", 10))
        self.count_lbl.pack(side="left", padx=(0, 10))

        # 追加・削除ボタン（左側に移動）
        ttk.Button(control_frame, text="+ 追加", command=self.add_location_dialog, width=6).pack(side="left", padx=2)
        ttk.Button(control_frame, text="- 削除", command=self.delete_location_dialog, width=6).pack(side="left", padx=2)

        # ステータス表示
        self.status_lbl = ttk.Label(control_frame, text="", foreground=COLORS["text_dim"], font=("Meiryo", 9))
        self.status_lbl.pack(side="right", padx=15)

        # 更新ボタン
        self.update_btn = ttk.Button(control_frame, text="更新", command=self.toggle_fetch)
        self.update_btn.pack(side="right", padx=5)

        # 最終更新日時（更新ボタンの左）
        self.last_updated_lbl = ttk.Label(control_frame, text="--/-- --:--", font=("Meiryo", 9))
        self.last_updated_lbl.pack(side="right", padx=5)
        self.update_last_updated_display()

        # --- メイングリッドエリア (枠固定実装) ---
        self.grid_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.grid_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Gridの設定
        self.grid_frame.grid_columnconfigure(1, weight=1) # Main Canvas列
        self.grid_frame.grid_rowconfigure(1, weight=1)    # Main Canvas行

        # 1. 左上コーナー (固定)
        corner = tk.Frame(self.grid_frame, bg=COLORS["header_bg"], width=SIDEBAR_WIDTH, height=HEADER_HEIGHT)
        corner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(corner, text="日時", bg=COLORS["header_bg"], fg=COLORS["text_dim"], font=("Meiryo", 9)).place(relx=0.5, rely=0.5, anchor="center")

        # 2. ヘッダー (横スクロール連動)
        self.header_canvas = tk.Canvas(self.grid_frame, bg=COLORS["bg"], height=HEADER_HEIGHT, highlightthickness=0)
        self.header_canvas.grid(row=0, column=1, sticky="ew", padx=0, pady=1)

        # 3. サイドバー (縦スクロール連動)
        self.sidebar_canvas = tk.Canvas(self.grid_frame, bg=COLORS["bg"], width=SIDEBAR_WIDTH, highlightthickness=0)
        self.sidebar_canvas.grid(row=1, column=0, sticky="ns", padx=1, pady=0)

        # 4. メインデータ (縦横スクロール)
        self.main_canvas = tk.Canvas(self.grid_frame, bg=COLORS["bg"], highlightthickness=0)
        self.main_canvas.grid(row=1, column=1, sticky="nsew")

        # スクロールバー
        self.vsb = ttk.Scrollbar(self.grid_frame, orient="vertical", command=self.on_vsb_scroll)
        self.vsb.grid(row=1, column=2, sticky="ns")
        
        self.hsb = ttk.Scrollbar(self.grid_frame, orient="horizontal", command=self.on_hsb_scroll)
        self.hsb.grid(row=2, column=1, sticky="ew")

        # スクロールイベントのバインド
        self.main_canvas.configure(xscrollcommand=self.hsb.set, yscrollcommand=self.vsb.set)
        
        # マウスホイール対応
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Windows
        self.main_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel) # 横スクロール

    def on_vsb_scroll(self, *args):
        self.main_canvas.yview(*args)
        self.sidebar_canvas.yview(*args)

    def on_hsb_scroll(self, *args):
        self.main_canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _on_mousewheel(self, event):
        # 縦スクロール
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_shift_mousewheel(self, event):
        # 横スクロール (Shift + Wheel)
        self.main_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        self.header_canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    # --- データ取得・更新ロジック ---

    def toggle_fetch(self):
        if self.is_fetching:
            # 中止処理
            self.cancel_fetch_flag = True
            self.status_lbl.config(text="中止しています...", foreground=COLORS["danger"])
            self.update_btn.config(state="disabled") # 連打防止
        else:
            # 開始処理
            self.is_fetching = True
            self.cancel_fetch_flag = False
            self.update_btn.config(text="中止", style="Danger.TButton")
            
            thread = threading.Thread(target=self._fetch_process)
            thread.daemon = True
            thread.start()

    def _fetch_process(self):
        times_set = set()
        new_data_map = {} # { location_id: { time_iso: cloud_cover } }

        try:
            total = len(self.locations)
            for idx, loc in enumerate(self.locations):
                if self.cancel_fetch_flag:
                    break
                
                # 進捗表示更新 (メインスレッドで実行)
                self.root.after(0, self.status_lbl.config, {"text": f"取得中 ({idx+1}/{total}): {loc['name']}...", "foreground": COLORS["accent"]})
                
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": loc["lat"],
                    "longitude": loc["lng"],
                    "hourly": "cloud_cover",
                    "timezone": "auto"
                }
                
                try:
                    # 15秒タイムアウト
                    response = requests.get(url, params=params, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        loc_forecasts = {}
                        
                        if "hourly" in data:
                            for i, t_iso in enumerate(data["hourly"]["time"]):
                                dt = datetime.datetime.fromisoformat(t_iso)
                                if dt.hour in TARGET_HOURS:
                                    times_set.add(t_iso)
                                    loc_forecasts[t_iso] = data["hourly"]["cloud_cover"][i]
                        
                        new_data_map[loc["id"]] = loc_forecasts
                    else:
                         print(f"Failed {loc['name']}: {response.status_code}")

                except requests.exceptions.Timeout:
                    print(f"Timeout: {loc['name']}")
                except Exception as e:
                    print(f"Error {loc['name']}: {e}")
                
                # APIへの負荷軽減のため少し待つ
                time.sleep(0.5)

            if not self.cancel_fetch_flag:
                # データ保存と更新
                sorted_times = sorted(list(times_set))
                
                # weather_data構造の構築
                save_payload = {
                    "updated_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M"),
                    "times": sorted_times,
                    "data": new_data_map
                }
                self.weather_data = save_payload
                self.save_json(WEATHER_FILE, save_payload)
                
                # 完了通知
                self.root.after(0, self.finish_fetch, "更新完了")
            else:
                self.root.after(0, self.finish_fetch, "更新中止")

        except Exception as e:
            print(f"Global Error: {e}")
            self.root.after(0, self.finish_fetch, "エラー発生")

    def finish_fetch(self, msg):
        self.is_fetching = False
        self.update_btn.config(text="更新", style="TButton", state="normal")
        self.status_lbl.config(text=msg, foreground=COLORS["text"])
        
        if msg == "更新完了":
            self.update_last_updated_display()
            self.draw_grid()
        
        # 数秒後にメッセージを消す
        self.root.after(3000, lambda: self.status_lbl.config(text=""))

    def update_last_updated_display(self):
        updated_at = self.weather_data.get("updated_at")
        if updated_at:
            self.last_updated_lbl.config(text=f"最終更新: {updated_at}")
        else:
            self.last_updated_lbl.config(text="未更新")

    # --- 描画ロジック (Canvas使用) ---

    def draw_grid(self):
        # キャンバスクリア
        self.header_canvas.delete("all")
        self.sidebar_canvas.delete("all")
        self.main_canvas.delete("all")

        times = self.weather_data.get("times", [])
        data_map = self.weather_data.get("data", {})
        
        if not times:
            self.main_canvas.create_text(200, 50, text="データがありません。[更新]ボタンを押してください。", fill=COLORS["text_dim"], anchor="w")
            return

        num_rows = len(times)
        num_cols = len(self.locations)

        # スクロール領域のサイズ計算
        total_width = num_cols * CELL_WIDTH
        total_height = num_rows * CELL_HEIGHT

        self.header_canvas.config(scrollregion=(0, 0, total_width, HEADER_HEIGHT))
        self.sidebar_canvas.config(scrollregion=(0, 0, SIDEBAR_WIDTH, total_height))
        self.main_canvas.config(scrollregion=(0, 0, total_width, total_height))

        # --- ヘッダー描画 (Locations) ---
        for j, loc in enumerate(self.locations):
            x = j * CELL_WIDTH
            # 背景
            self.header_canvas.create_rectangle(x, 0, x + CELL_WIDTH, HEADER_HEIGHT, 
                                                fill=COLORS["header_bg"], outline=COLORS["border"])
            # テキスト
            self.header_canvas.create_text(x + CELL_WIDTH/2, HEADER_HEIGHT/2, 
                                           text=loc["name"], fill=COLORS["accent"], 
                                           font=("Meiryo", 9, "bold"), width=CELL_WIDTH-10)

        # --- 行描画 (Times) & データセル ---
        for i, t_iso in enumerate(times):
            y = i * CELL_HEIGHT
            dt = datetime.datetime.fromisoformat(t_iso)
            is_noon = (dt.hour == 12)
            
            # --- サイドバー (日時) ---
            bg_col = COLORS["noon_bg"] if is_noon else COLORS["header_bg"]
            fg_date = COLORS["noon_text"] if is_noon else COLORS["text_dim"]
            fg_time = COLORS["noon_text"] if is_noon else COLORS["text"]

            self.sidebar_canvas.create_rectangle(0, y, SIDEBAR_WIDTH, y + CELL_HEIGHT,
                                                 fill=bg_col, outline=COLORS["border"])
            
            # 日付
            self.sidebar_canvas.create_text(SIDEBAR_WIDTH/2, y + 15,
                                            text=f"{dt.month}/{dt.day}", fill=fg_date, font=("Arial", 8))
            # 時間
            self.sidebar_canvas.create_text(SIDEBAR_WIDTH/2, y + 35,
                                            text=f"{dt.hour}:00", fill=fg_time, font=("Arial", 10, "bold"))

            # --- メインデータセル ---
            for j, loc in enumerate(self.locations):
                x = j * CELL_WIDTH
                
                # 値の取得
                val = None
                if loc["id"] in data_map and t_iso in data_map[loc["id"]]:
                    val = data_map[loc["id"]][t_iso]

                # 色決定
                cell_bg = COLORS["bg"]
                cell_fg = COLORS["text_dim"]
                text_val = "--"

                if val is not None:
                    text_val = str(val)
                    if val < 15:
                        cell_bg = COLORS["cloud_0_15"]
                        cell_fg = COLORS["cloud_text_0_15"]
                    elif val < 25:
                        cell_bg = COLORS["cloud_15_25"]
                        cell_fg = COLORS["cloud_text_15_25"]
                    elif val < 35:
                        cell_bg = COLORS["cloud_25_35"]
                        cell_fg = COLORS["cloud_text_25_35"]
                    else:
                        cell_bg = COLORS["cloud_over"]
                        cell_fg = COLORS["cloud_text_over"]
                else:
                    cell_bg = COLORS["cloud_over"] # データなしの場合もグレーアウト

                # セル描画
                self.main_canvas.create_rectangle(x, y, x + CELL_WIDTH, y + CELL_HEIGHT,
                                                  fill=cell_bg, outline=COLORS["border"])
                
                self.main_canvas.create_text(x + CELL_WIDTH/2, y + CELL_HEIGHT/2,
                                             text=text_val, fill=cell_fg,
                                             font=("Arial", 11, "bold"))

    # --- 地点追加・削除ダイアログ ---
    
    def add_location_dialog(self):
        name = simpledialog.askstring("地点追加", "地点名を入力してください:")
        if not name: return
        
        coord_str = simpledialog.askstring("地点追加", 
            "緯度, 経度を入力してください\n(Googleマップ等からコピペ可)\n例: 35.657..., 140.075...")
        if not coord_str: return

        try:
            clean_str = coord_str.replace("，", ",").replace(" ", "")
            parts = clean_str.split(",")
            if len(parts) != 2: raise ValueError
            lat = float(parts[0])
            lng = float(parts[1])
            
            new_loc = {"id": str(uuid.uuid4()), "name": name, "lat": lat, "lng": lng}
            self.locations.append(new_loc)
            self.save_json(LOCATIONS_FILE, self.locations)
            self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")
            
            # データの再描画（列が増えるため）
            self.draw_grid()

        except:
            messagebox.showerror("エラー", "座標形式が不正です")

    def delete_location_dialog(self):
        if not self.locations: return
        
        del_win = tk.Toplevel(self.root)
        del_win.title("地点を削除")
        del_win.geometry("300x400")
        del_win.configure(bg=COLORS["bg"])
        
        lb_frame = ttk.Frame(del_win)
        lb_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        lb = tk.Listbox(lb_frame, bg=COLORS["header_bg"], fg=COLORS["text"], selectbackground=COLORS["accent"])
        lb.pack(side="left", fill="both", expand=True)
        
        for loc in self.locations:
            lb.insert(tk.END, loc["name"])
            
        def execute():
            selection = lb.curselection()
            if selection:
                idx = selection[0]
                del self.locations[idx]
                self.save_json(LOCATIONS_FILE, self.locations)
                self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")
                self.draw_grid()
                del_win.destroy()
        
        ttk.Button(del_win, text="削除実行", command=execute).pack(pady=10)

    # --- 【追加】アプリ終了処理 ---
    def on_closing(self):
        try:
            # 現在のジオメトリを保存して終了
            self.app_config["geometry"] = self.root.geometry()
            self.save_json(APP_CONFIG_FILE, self.app_config)
        except Exception as e:
            print(f"Config Save Error: {e}")
        finally:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = StarGazerApp(root)
    root.mainloop()