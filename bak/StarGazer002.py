#StarGazer002.py
#Google AI Studio


import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import requests
import json
import os
import datetime
import threading
import uuid

# --- 設定 ---
# 表示する時間帯 (0時, 3時, 6時, 12時, 18時, 21時)
TARGET_HOURS = [0, 3, 6, 12, 18, 21]
DATA_FILE = "locations.json"

# --- 配色設定 (Webアプリのデザインに合わせる) ---
COLORS = {
    "bg": "#0f172a",          # 全体の背景 (Slate 900)
    "header_bg": "#1e293b",   # ヘッダー背景 (Slate 800)
    "text": "#e2e8f0",        # 基本文字色 (Slate 200)
    "text_dim": "#94a3b8",    # 薄い文字色 (Slate 400)
    "border": "#334155",      # 枠線 (Slate 700)
    "accent": "#6366f1",      # アクセント (Indigo 500)
    
    # 雲量ごとの色
    "cloud_0_15": "#38bdf8",  # <15% (Sky 400)
    "cloud_text_0_15": "#082f49", 
    
    "cloud_15_25": "#fde047", # <25% (Yellow 300)
    "cloud_text_15_25": "#422006",
    
    "cloud_25_35": "#fb923c", # <35% (Orange 400)
    "cloud_text_25_35": "#ffffff",
    
    "cloud_over": "#64748b",  # >=35% (Slate 500)
    "cloud_text_over": "#e2e8f0",

    # 12:00 (正午) の強調表示
    "noon_bg": "#facc15",     # 明るめの黄色 (Yellow 400)
    "noon_text": "#0f172a"    # 黒文字 (Slate 900)
}

# --- デフォルトの観測地点 ---
DEFAULT_LOCATIONS = [
    {"id": "1", "name": "幕張の浜", "lat": 35.640575, "lng": 140.035070},
    {"id": "2", "name": "野辺山", "lat": 35.9416, "lng": 138.4727}
]

class StarGazerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StarGazer Cloud Forecast")
        self.root.geometry("1100x650")
        self.root.configure(bg=COLORS["bg"])

        # ロケーションデータの読み込み
        self.locations = self.load_locations()

        # スタイル設定
        self.setup_styles()

        # UI構築
        self.create_ui()
        
        # データ取得開始
        self.refresh_data()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # フレーム等のスタイル
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Header.TFrame", background=COLORS["header_bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        
        # ボタン
        style.configure("TButton", 
                        background=COLORS["header_bg"], 
                        foreground=COLORS["text"], 
                        borderwidth=1,
                        focusthickness=3,
                        focuscolor=COLORS["border"])
        style.map("TButton", 
                  background=[("active", COLORS["accent"]), ("pressed", COLORS["accent"])],
                  foreground=[("active", "#ffffff")])
        
        # スクロールバー
        style.configure("Vertical.TScrollbar", 
                        gripcount=0,
                        background=COLORS["header_bg"],
                        darkcolor=COLORS["bg"],
                        lightcolor=COLORS["bg"],
                        troughcolor=COLORS["bg"],
                        bordercolor=COLORS["bg"],
                        arrowcolor=COLORS["text"])

    def load_locations(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return DEFAULT_LOCATIONS
        return DEFAULT_LOCATIONS

    def save_locations(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.locations, f, ensure_ascii=False, indent=2)

    def create_ui(self):
        # --- 上部コントロールパネル ---
        control_frame = ttk.Frame(self.root, style="Header.TFrame", padding=10)
        control_frame.pack(fill="x")

        # タイトル
        title_lbl = ttk.Label(control_frame, text="StarGazer", font=("Arial", 14, "bold"), background=COLORS["header_bg"], foreground=COLORS["accent"])
        title_lbl.pack(side="left", padx=(5, 10))
        
        count_lbl = ttk.Label(control_frame, text=f"観測地点 ({len(self.locations)})", font=("Meiryo", 10), background=COLORS["header_bg"])
        count_lbl.pack(side="left")
        self.count_lbl = count_lbl # 更新用に保持

        # ボタン群
        ttk.Button(control_frame, text="更新", command=self.refresh_data).pack(side="right", padx=5)
        ttk.Button(control_frame, text="削除", command=self.delete_location_dialog).pack(side="right", padx=5)
        ttk.Button(control_frame, text="追加", command=self.add_location_dialog).pack(side="right", padx=5)

        # --- メインエリア (スクロール付き) ---
        container = ttk.Frame(self.root, style="TFrame")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # テーブルを表示するフレーム
        self.scrollable_frame = ttk.Frame(self.canvas, style="TFrame")

        # スクロール領域の更新処理
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイール対応
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_location_dialog(self):
        # 地点名入力
        name = simpledialog.askstring("地点追加", "地点名を入力してください:")
        if not name: return
        
        # 座標一括入力
        coord_str = simpledialog.askstring("地点追加", 
            "緯度, 経度を入力してください\n(Googleマップ等からコピペ可)\n例: 35.657..., 140.075...")
        if not coord_str: return

        # 座標解析
        try:
            # 全角カンマやスペースへの対応
            clean_str = coord_str.replace("，", ",").replace(" ", "")
            parts = clean_str.split(",")
            
            if len(parts) != 2:
                raise ValueError("カンマで区切られていません")
                
            lat = float(parts[0])
            lng = float(parts[1])
            
            new_loc = {
                "id": str(uuid.uuid4()),
                "name": name,
                "lat": lat,
                "lng": lng
            }
            self.locations.append(new_loc)
            self.save_locations()
            self.refresh_data()
            self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")

        except ValueError:
            messagebox.showerror("エラー", "座標の形式が正しくありません。\n「35.123, 140.123」のように数値とカンマで入力してください。")

    def delete_location_dialog(self):
        if not self.locations: return

        # 削除ウィンドウを作成
        del_win = tk.Toplevel(self.root)
        del_win.title("地点を削除")
        del_win.geometry("300x400")
        del_win.configure(bg=COLORS["bg"])
        
        # リストボックス
        lb_frame = ttk.Frame(del_win, style="TFrame")
        lb_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        lb = tk.Listbox(lb_frame, bg=COLORS["header_bg"], fg=COLORS["text"], 
                        selectbackground=COLORS["accent"], borderwidth=0, highlightthickness=0)
        lb.pack(side="left", fill="both", expand=True)
        
        scr = ttk.Scrollbar(lb_frame, orient="vertical", command=lb.yview)
        scr.pack(side="right", fill="y")
        lb.config(yscrollcommand=scr.set)

        for loc in self.locations:
            lb.insert(tk.END, loc["name"])
        
        def execute_delete():
            selection = lb.curselection()
            if selection:
                idx = selection[0]
                del self.locations[idx]
                self.save_locations()
                self.refresh_data()
                self.count_lbl.config(text=f"観測地点 ({len(self.locations)})")
                del_win.destroy()
        
        btn = ttk.Button(del_win, text="選択した地点を削除", command=execute_delete)
        btn.pack(pady=10)

    def refresh_data(self):
        # 既存の内容をクリア
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # ロード中メッセージ
        loading_lbl = tk.Label(self.scrollable_frame, text="データを取得中...", 
                               bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Meiryo", 12))
        loading_lbl.pack(pady=30, padx=20)

        # UIの描画をブロックしないように別スレッドで通信
        thread = threading.Thread(target=self._fetch_logic)
        thread.daemon = True
        thread.start()

    def _fetch_logic(self):
        if not self.locations:
            self.root.after(0, self._draw_empty)
            return

        full_data = {} # { time_iso: { location_id: cloud_cover } }
        times_set = set()

        try:
            for loc in self.locations:
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": loc["lat"],
                    "longitude": loc["lng"],
                    "hourly": "cloud_cover",
                    "timezone": "auto" # 現地時間で取得
                }
                
                # タイムアウト設定を追加
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if "hourly" not in data:
                    continue

                for i, t_iso in enumerate(data["hourly"]["time"]):
                    dt = datetime.datetime.fromisoformat(t_iso)
                    if dt.hour in TARGET_HOURS:
                        times_set.add(t_iso)
                        
                        if t_iso not in full_data:
                            full_data[t_iso] = {}
                        
                        full_data[t_iso][loc["id"]] = data["hourly"]["cloud_cover"][i]
            
            sorted_times = sorted(list(times_set))
            # メインスレッドで描画実行
            self.root.after(0, lambda: self._draw_grid(sorted_times, full_data))

        except Exception as e:
            print(f"Error: {e}")
            self.root.after(0, lambda: messagebox.showerror("通信エラー", "天気データの取得に失敗しました。\nインターネット接続を確認してください。"))
            self.root.after(0, self._draw_empty)

    def _draw_empty(self):
        # クリア (ロード中表示を消すため)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        tk.Label(self.scrollable_frame, text="地点を登録してください", 
                 bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(pady=20)

    def _draw_grid(self, times, full_data):
        # クリア
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # グリッド設定
        # 列0: 日時, 列1~: 各地点
        
        # --- ヘッダー行 (地点名) ---
        # 固定ヘッダーっぽい見た目のため、日時部分は少し空ける
        tk.Label(self.scrollable_frame, text="日時", 
                 bg=COLORS["bg"], fg=COLORS["text_dim"], 
                 width=8, pady=5, font=("Meiryo", 9)).grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        for j, loc in enumerate(self.locations):
            # 地点名ラベル
            lbl = tk.Label(self.scrollable_frame, text=loc["name"], 
                           bg=COLORS["header_bg"], fg=COLORS["accent"],
                           width=10, pady=8, font=("Meiryo", 10, "bold"), wraplength=100)
            lbl.grid(row=0, column=j+1, sticky="nsew", padx=1, pady=1)

        # --- データ行 ---
        for i, t_iso in enumerate(times):
            dt = datetime.datetime.fromisoformat(t_iso)
            month = dt.month
            day = dt.day
            hour = dt.hour
            
            is_noon = (hour == 12)
            
            # --- 日時セル ---
            # 12:00の場合は背景黄色、文字黒。それ以外はデフォルト
            time_bg = COLORS["noon_bg"] if is_noon else COLORS["header_bg"]
            
            # 日付部分の文字色
            date_fg = COLORS["noon_text"] if is_noon else COLORS["text_dim"]
            # 時間部分の文字色 (強調のため少し濃くするか、同じにするか)
            time_fg = COLORS["noon_text"] if is_noon else COLORS["text"]

            # フレームを使って日時を2段組にする (省スペース)
            time_frame = tk.Frame(self.scrollable_frame, bg=time_bg)
            time_frame.grid(row=i+1, column=0, sticky="nsew", padx=1, pady=1)
            
            # センタリング用
            time_frame.grid_columnconfigure(0, weight=1)
            time_frame.grid_rowconfigure(0, weight=1)
            time_frame.grid_rowconfigure(1, weight=1)

            # 月日 (例: 10/25)
            tk.Label(time_frame, text=f"{month}/{day}", 
                     bg=time_bg, fg=date_fg, font=("Arial", 8)).pack(side="top", pady=(2,0))
            # 時間 (例: 21:00)
            tk.Label(time_frame, text=f"{hour}:00", 
                     bg=time_bg, fg=time_fg, font=("Arial", 10, "bold")).pack(side="top", pady=(0,2))

            # --- 各地点のデータセル ---
            for j, loc in enumerate(self.locations):
                val = full_data.get(t_iso, {}).get(loc["id"], None)
                
                cell_bg = COLORS["cloud_over"]
                cell_fg = COLORS["cloud_text_over"]
                text = "--"

                if val is not None:
                    text = str(val)
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
                
                # 数値表示
                lbl = tk.Label(self.scrollable_frame, text=text, 
                               bg=cell_bg, fg=cell_fg,
                               font=("Arial", 11, "bold"), width=8, pady=4)
                lbl.grid(row=i+1, column=j+1, sticky="nsew", padx=1, pady=1)

# メイン処理
if __name__ == "__main__":
    root = tk.Tk()
    
    # 高DPIディスプレイ対応 (Windowsで文字がぼやけるのを防ぐ)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    app = StarGazerApp(root)
    root.mainloop()