# ui_components.py
# メイングリッド描画 Canvas およびスクロール連動コンポーネント

import tkinter as tk
from tkinter import ttk
import datetime
from typing import List, Dict, Callable, Optional
from .config import (
    COLORS, CELL_WIDTH, CELL_HEIGHT, HEADER_HEIGHT, SIDEBAR_WIDTH, TARGET_HOURS_3H
)
from .models import Location, CellPrecomputed
from .ui_detail_dlg import show_detail_dialog

class WeatherGrid:
    def __init__(
        self,
        parent: tk.Widget,
        root: tk.Tk,
        get_locations: Callable[[], List[Location]],
        get_precomputed_cache: Callable[[], Dict[str, Dict[str, CellPrecomputed]]],
        get_all_times: Callable[[], List[str]],
        get_view_mode: Callable[[], str],   # "3h" or "1h"
        get_cloud_mode: Callable[[], str]  # "elevation" or "total"
    ):
        self.parent = parent
        self.root = root
        self.get_locations = get_locations
        self.get_precomputed_cache = get_precomputed_cache
        self.get_all_times = get_all_times
        self.get_view_mode = get_view_mode
        self.get_cloud_mode = get_cloud_mode

        # 現在描画されている行の時刻リスト
        self.displayed_times: List[str] = []

        self.setup_ui()

    def setup_ui(self):
        self.grid_frame = tk.Frame(self.parent, bg=COLORS["bg"])
        self.grid_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.grid_frame.grid_columnconfigure(1, weight=1)
        self.grid_frame.grid_rowconfigure(1, weight=1)

        # 1. 左上コーナー (固定)
        self.corner = tk.Frame(self.grid_frame, bg=COLORS["header_bg"], width=SIDEBAR_WIDTH, height=HEADER_HEIGHT)
        self.corner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        tk.Label(
            self.corner, text="日時", bg=COLORS["header_bg"], fg=COLORS["text_dim"], font=("Meiryo", 9)
        ).place(relx=0.5, rely=0.5, anchor="center")

        # 2. 上部ヘッダー (地点名・標高、横スクロール連動)
        self.header_canvas = tk.Canvas(
            self.grid_frame, bg=COLORS["bg"], height=HEADER_HEIGHT, highlightthickness=0
        )
        self.header_canvas.grid(row=0, column=1, sticky="ew", padx=0, pady=1)

        # 3. 左側サイドバー (日時、縦スクロール連動)
        self.sidebar_canvas = tk.Canvas(
            self.grid_frame, bg=COLORS["bg"], width=SIDEBAR_WIDTH, highlightthickness=0
        )
        self.sidebar_canvas.grid(row=1, column=0, sticky="ns", padx=1, pady=0)

        # 4. メインキャンバス (気象セルデータ、縦横スクロール)
        self.main_canvas = tk.Canvas(
            self.grid_frame, bg=COLORS["bg"], highlightthickness=0
        )
        self.main_canvas.grid(row=1, column=1, sticky="nsew")
        self.main_canvas.bind("<Button-1>", self.on_cell_click)

        # スクロールバー
        self.vsb = ttk.Scrollbar(self.grid_frame, orient="vertical", command=self.on_vsb_scroll)
        self.vsb.grid(row=1, column=2, sticky="ns")

        self.hsb = ttk.Scrollbar(self.grid_frame, orient="horizontal", command=self.on_hsb_scroll)
        self.hsb.grid(row=2, column=1, sticky="ew")

        self.main_canvas.configure(xscrollcommand=self.hsb.set, yscrollcommand=self.vsb.set)

        # マウスホイールイベントバインド (Windows)
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.main_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def on_vsb_scroll(self, *args):
        self.main_canvas.yview(*args)
        self.sidebar_canvas.yview(*args)

    def on_hsb_scroll(self, *args):
        self.main_canvas.xview(*args)
        self.header_canvas.xview(*args)

    def _on_mousewheel(self, event):
        delta = int(-1 * (event.delta / 120))
        self.main_canvas.yview_scroll(delta, "units")
        self.sidebar_canvas.yview_scroll(delta, "units")

    def _on_shift_mousewheel(self, event):
        delta = int(-1 * (event.delta / 120))
        self.main_canvas.xview_scroll(delta, "units")
        self.header_canvas.xview_scroll(delta, "units")

    def get_filtered_times(self) -> List[str]:
        all_times = self.get_all_times()
        mode = self.get_view_mode()
        if mode == "1h":
            return all_times
        # 3h モード: TARGET_HOURS_3H [0, 3, 6, 12, 18, 21] のみ抽出
        filtered = []
        for t_iso in all_times:
            try:
                dt = datetime.datetime.fromisoformat(t_iso)
                if dt.hour in TARGET_HOURS_3H:
                    filtered.append(t_iso)
            except:
                pass
        return filtered

    def render(self):
        """グリッド全体の描画（キャッシュを参照して高速実行）"""
        self.header_canvas.delete("all")
        self.sidebar_canvas.delete("all")
        self.main_canvas.delete("all")

        locations = self.get_locations()
        cache = self.get_precomputed_cache()
        cloud_mode = self.get_cloud_mode()
        self.displayed_times = self.get_filtered_times()

        if not self.displayed_times:
            self.main_canvas.create_text(
                200, 50,
                text="気象データがありません。[更新]ボタンを押して取得してください。",
                fill=COLORS["text_dim"], anchor="w", font=("Meiryo", 10)
            )
            return

        num_cols = len(locations)
        num_rows = len(self.displayed_times)
        total_width = num_cols * CELL_WIDTH
        total_height = num_rows * CELL_HEIGHT

        # スクロール領域設定
        self.header_canvas.config(scrollregion=(0, 0, total_width, HEADER_HEIGHT))
        self.sidebar_canvas.config(scrollregion=(0, 0, SIDEBAR_WIDTH, total_height))
        self.main_canvas.config(scrollregion=(0, 0, total_width, total_height))

        # --- 1. ヘッダー描画 (地点名 + 標高) ---
        for j, loc in enumerate(locations):
            x = j * CELL_WIDTH
            self.header_canvas.create_rectangle(
                x, 0, x + CELL_WIDTH, HEADER_HEIGHT,
                fill=COLORS["header_bg"], outline=COLORS["border"]
            )
            # 地点名
            self.header_canvas.create_text(
                x + CELL_WIDTH / 2, 16,
                text=loc.name, fill=COLORS["accent"],
                font=("Meiryo", 9, "bold"), width=CELL_WIDTH - 6
            )
            # 標高
            elev_txt = f"{int(loc.elevation)}m"
            self.header_canvas.create_text(
                x + CELL_WIDTH / 2, 32,
                text=elev_txt, fill=COLORS["text_dim"],
                font=("Arial", 8)
            )

        # --- 2. 行 (日時) ＆ セル描画 ---
        for i, t_iso in enumerate(self.displayed_times):
            y = i * CELL_HEIGHT
            dt = datetime.datetime.fromisoformat(t_iso)
            is_noon = (dt.hour == 12)

            # サイドバー (日時)
            bg_sidebar = COLORS["noon_bg"] if is_noon else COLORS["header_bg"]
            fg_date = COLORS["noon_text"] if is_noon else COLORS["text_dim"]
            fg_time = COLORS["noon_text"] if is_noon else COLORS["text"]

            self.sidebar_canvas.create_rectangle(
                0, y, SIDEBAR_WIDTH, y + CELL_HEIGHT,
                fill=bg_sidebar, outline=COLORS["border"]
            )
            # 日付 (月/日)
            self.sidebar_canvas.create_text(
                SIDEBAR_WIDTH / 2, y + 16,
                text=f"{dt.month}/{dt.day}", fill=fg_date, font=("Arial", 8)
            )
            # 時刻 (時:分)
            self.sidebar_canvas.create_text(
                SIDEBAR_WIDTH / 2, y + 36,
                text=f"{dt.hour:02d}:00", fill=fg_time, font=("Arial", 10, "bold")
            )

            # メインセル
            for j, loc in enumerate(locations):
                x = j * CELL_WIDTH
                loc_cache = cache.get(loc.id, {})
                cell = loc_cache.get(t_iso)

                val_str = "--"
                status = "none"
                wind_txt = ""
                fog_txt = ""

                if cell is not None:
                    if cloud_mode == "elevation":
                        val_num = cell.elevation_val
                        status = cell.elevation_status
                    else:
                        val_num = cell.total_val
                        status = cell.total_status

                    if val_num is not None:
                        val_str = str(val_num)
                    wind_txt = cell.wind_text
                    fog_txt = cell.fog_text

                # 背景色
                if status == "good":
                    cell_bg = COLORS["status_good"]
                    text_fg = COLORS["text_good"]
                    alert_fg = COLORS["alert_good"]
                elif status == "fair":
                    cell_bg = COLORS["status_fair"]
                    text_fg = COLORS["text_fair"]
                    alert_fg = COLORS["alert_fair"]
                elif status == "poor":
                    cell_bg = COLORS["status_poor"]
                    text_fg = COLORS["text_poor"]
                    alert_fg = COLORS["alert_poor"]
                else:
                    cell_bg = COLORS["bg"]
                    text_fg = COLORS["text_nodata"]
                    alert_fg = COLORS["alert_poor"]

                # 背景長方形
                self.main_canvas.create_rectangle(
                    x, y, x + CELL_WIDTH, y + CELL_HEIGHT,
                    fill=cell_bg, outline=COLORS["border"]
                )

                # 上段：雲量（数字のみ）
                self.main_canvas.create_text(
                    x + CELL_WIDTH / 2, y + 18,
                    text=val_str, fill=text_fg,
                    font=("Arial", 11, "bold")
                )

                # 下段：左に風速（数字のみ）、右に霧（漢字のみ）
                if wind_txt:
                    self.main_canvas.create_text(
                        x + 22, y + 38,
                        text=wind_txt, fill=alert_fg,
                        font=("Arial", 9, "bold")
                    )

                if fog_txt:
                    self.main_canvas.create_text(
                        x + CELL_WIDTH - 22, y + 38,
                        text=fog_txt, fill=alert_fg,
                        font=("Meiryo", 9, "bold")
                    )

    def on_cell_click(self, event):
        """セルクリック時に詳細ダイアログを表示"""
        # キャンバスのスクロールオフセットを考慮した座標取得
        canvas_x = self.main_canvas.canvasx(event.x)
        canvas_y = self.main_canvas.canvasy(event.y)

        col = int(canvas_x // CELL_WIDTH)
        row = int(canvas_y // CELL_HEIGHT)

        locations = self.get_locations()
        if not (0 <= col < len(locations) and 0 <= row < len(self.displayed_times)):
            return

        loc = locations[col]
        t_iso = self.displayed_times[row]
        cache = self.get_precomputed_cache()
        cell = cache.get(loc.id, {}).get(t_iso)

        raw_data = cell.raw_data if cell else {}
        if raw_data:
            show_detail_dialog(self.root, loc, t_iso, raw_data)
