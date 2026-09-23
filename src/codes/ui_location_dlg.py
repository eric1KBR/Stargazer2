# ui_location_dlg.py
# 観測地点管理ダイアログ（追加・編集・削除・並び替え・標高自動取得）

import tkinter as tk
from tkinter import ttk, messagebox
import uuid
from typing import List, Callable, Optional, Tuple
from .config import COLORS
from .models import Location
from .api_client import fetch_elevation

class LocationManagerDialog:
    def __init__(self, parent: tk.Tk, locations: List[Location], on_save: Callable[[List[Location]], None]):
        self.dlg = tk.Toplevel(parent)
        self.dlg.title("観測地点の管理")
        self.dlg.geometry("540x560")
        self.dlg.configure(bg=COLORS["bg"])
        self.dlg.transient(parent)
        self.dlg.grab_set()

        # 編集用ローカルコピー
        self.locations: List[Location] = [Location.from_dict(loc.to_dict()) for loc in locations]
        self.on_save = on_save

        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        # 1. リスト表示エリア
        list_frame = tk.Frame(self.dlg, bg=COLORS["bg"], padx=10, pady=8)
        list_frame.pack(fill="both", expand=True)

        tk.Label(
            list_frame,
            text="観測地点一覧 (地点を選んで上下で並び替え、または下欄で編集できます)",
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
            font=("Meiryo", 9)
        ).pack(anchor="w", pady=(0, 4))

        # リストボックス＋スクロールバー＋上下ボタン
        box_frame = tk.Frame(list_frame, bg=COLORS["bg"])
        box_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            box_frame,
            bg=COLORS["header_bg"],
            fg=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground="#0f172a",
            font=("Meiryo", 9),
            activestyle="none",
            borderwidth=1,
            relief="solid"
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_location)

        scrollbar = ttk.Scrollbar(box_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # 並び替え上下ボタン
        move_btn_frame = tk.Frame(box_frame, bg=COLORS["bg"], padx=6)
        move_btn_frame.pack(side="right", fill="y")

        ttk.Button(move_btn_frame, text="▲ 上へ", width=8, command=self.move_up).pack(pady=4)
        ttk.Button(move_btn_frame, text="▼ 下へ", width=8, command=self.move_down).pack(pady=4)
        ttk.Button(move_btn_frame, text="削除", width=8, command=self.delete_selected).pack(pady=(15, 4))

        # 2. 地点編集・追加フォームエリア
        form_frame = tk.LabelFrame(
            self.dlg,
            text="地点の登録・編集",
            bg=COLORS["header_bg"],
            fg=COLORS["text"],
            font=("Meiryo", 9, "bold"),
            padx=12,
            pady=8
        )
        form_frame.pack(fill="x", padx=10, pady=6)

        # 地点名
        f1 = tk.Frame(form_frame, bg=COLORS["header_bg"])
        f1.pack(fill="x", pady=2)
        tk.Label(f1, text="地点名:", bg=COLORS["header_bg"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")
        self.name_entry = ttk.Entry(f1)
        self.name_entry.pack(side="left", fill="x", expand=True)
        self.name_entry.bind("<Return>", lambda e: self.update_selected())

        # 座標 (緯度, 経度)
        f2 = tk.Frame(form_frame, bg=COLORS["header_bg"])
        f2.pack(fill="x", pady=2)
        tk.Label(f2, text="緯度, 経度:", bg=COLORS["header_bg"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")
        self.coord_entry = ttk.Entry(f2)
        self.coord_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(f2, text="標高を取得", command=self.auto_fetch_elevation).pack(side="left")
        self.coord_entry.bind("<Return>", lambda e: self.update_selected())

        # 標高
        f3 = tk.Frame(form_frame, bg=COLORS["header_bg"])
        f3.pack(fill="x", pady=2)
        tk.Label(f3, text="標高 (m):", bg=COLORS["header_bg"], fg=COLORS["text"], width=10, anchor="w").pack(side="left")
        self.elev_entry = ttk.Entry(f3, width=12)
        self.elev_entry.pack(side="left")
        self.elev_entry.bind("<Return>", lambda e: self.update_selected())

        # 操作ボタン（新規登録 / 選択地点を更新）
        f_btn = tk.Frame(form_frame, bg=COLORS["header_bg"])
        f_btn.pack(fill="x", pady=(8, 2))
        ttk.Button(f_btn, text="選択地点を更新", command=self.update_selected).pack(side="left", padx=2)
        ttk.Button(f_btn, text="+ 新規地点として追加", command=self.add_location).pack(side="left", padx=4)
        ttk.Button(f_btn, text="クリア", command=self.clear_form).pack(side="right", padx=2)

        # 案内テキスト
        tk.Label(
            form_frame,
            text="※一覧で地点を選んで編集後、「選択地点を更新」または「保存して適用」を押すと反映されます。",
            bg=COLORS["header_bg"],
            fg=COLORS["text_dim"],
            font=("Meiryo", 8)
        ).pack(anchor="w", pady=(4, 0))

        # 3. 最下部アクションボタン (保存 / キャンセル)
        bottom_frame = tk.Frame(self.dlg, bg=COLORS["bg"], padx=10, pady=10)
        bottom_frame.pack(fill="x")

        ttk.Button(bottom_frame, text="保存して適用", style="Accent.TButton", command=self.save_and_close).pack(side="right", padx=4)
        ttk.Button(bottom_frame, text="キャンセル", command=self.dlg.destroy).pack(side="right", padx=4)

    def refresh_list(self, select_idx: int = -1):
        self.listbox.delete(0, tk.END)
        for i, loc in enumerate(self.locations):
            self.listbox.insert(
                tk.END,
                f"{i+1:2d}. {loc.name:<10s} (標高: {int(loc.elevation)}m) [{loc.lat:.4f}, {loc.lng:.4f}]"
            )
        if 0 <= select_idx < len(self.locations):
            self.listbox.selection_set(select_idx)
            self.listbox.see(select_idx)

    def on_select_location(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        loc = self.locations[idx]
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, loc.name)

        self.coord_entry.delete(0, tk.END)
        self.coord_entry.insert(0, f"{loc.lat}, {loc.lng}")

        self.elev_entry.delete(0, tk.END)
        self.elev_entry.insert(0, str(int(loc.elevation)))

    def clear_form(self):
        self.name_entry.delete(0, tk.END)
        self.coord_entry.delete(0, tk.END)
        self.elev_entry.delete(0, tk.END)
        self.listbox.selection_clear(0, tk.END)

    def parse_coords(self) -> Tuple[float, float]:
        raw = self.coord_entry.get().replace("，", ",").replace(" ", "").strip()
        parts = raw.split(",")
        if len(parts) != 2:
            raise ValueError("緯度, 経度の形式で入力してください (例: 36.228, 138.132)")
        return float(parts[0]), float(parts[1])

    def auto_fetch_elevation(self):
        try:
            lat, lng = self.parse_coords()
        except Exception as e:
            messagebox.showwarning("入力エラー", str(e), parent=self.dlg)
            return

        elev = fetch_elevation(lat, lng)
        if elev is not None:
            self.elev_entry.delete(0, tk.END)
            self.elev_entry.insert(0, str(int(round(elev))))
            # 選択中の地点があれば即座に一覧にも仮反映
            sel = self.listbox.curselection()
            if sel:
                self._apply_form_to_selected(silent=True)
        else:
            messagebox.showerror("取得エラー", "標高の取得に失敗しました。数値を直接手入力してください。", parent=self.dlg)

    def _apply_form_to_selected(self, silent: bool = False) -> bool:
        """入力フォームの内容を選択中の地点に反映する共通処理"""
        sel = self.listbox.curselection()
        if not sel:
            if not silent:
                messagebox.showinfo("案内", "更新する地点を一覧から選択してください", parent=self.dlg)
            return False

        idx = sel[0]
        name = self.name_entry.get().strip()
        if not name:
            if not silent:
                messagebox.showwarning("入力エラー", "地点名を入力してください", parent=self.dlg)
            return False

        try:
            lat, lng = self.parse_coords()
        except Exception as e:
            if not silent:
                messagebox.showwarning("入力エラー", str(e), parent=self.dlg)
            return False

        try:
            elev = float(self.elev_entry.get().strip() or "0")
        except ValueError:
            if not silent:
                messagebox.showwarning("入力エラー", "標高には数値を入力してください", parent=self.dlg)
            return False

        target = self.locations[idx]
        target.name = name
        target.lat = lat
        target.lng = lng
        target.elevation = elev
        self.refresh_list(idx)
        return True

    def update_selected(self):
        """「選択地点を更新」ボタンの処理"""
        if self._apply_form_to_selected(silent=False):
            # 更新成功を小さく通知するかリスト選択を維持
            pass

    def add_location(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("入力エラー", "地点名を入力してください", parent=self.dlg)
            return
        try:
            lat, lng = self.parse_coords()
        except Exception as e:
            messagebox.showwarning("入力エラー", str(e), parent=self.dlg)
            return

        try:
            elev = float(self.elev_entry.get().strip() or "0")
        except ValueError:
            messagebox.showwarning("入力エラー", "標高には数値を入力してください", parent=self.dlg)
            return

        new_loc = Location(id=str(uuid.uuid4()), name=name, lat=lat, lng=lng, elevation=elev)
        self.locations.append(new_loc)
        self.refresh_list(len(self.locations) - 1)
        self.clear_form()

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self.locations[idx].name
        if messagebox.askyesno("削除確認", f"「{name}」を削除しますか？", parent=self.dlg):
            del self.locations[idx]
            new_sel = min(idx, len(self.locations) - 1)
            self.refresh_list(new_sel)
            self.clear_form()

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.locations[idx - 1], self.locations[idx] = self.locations[idx], self.locations[idx - 1]
        self.refresh_list(idx - 1)

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.locations) - 1:
            return
        idx = sel[0]
        self.locations[idx + 1], self.locations[idx] = self.locations[idx], self.locations[idx + 1]
        self.refresh_list(idx + 1)

    def save_and_close(self):
        # リスト選択中かつフォームに文字が入っている場合は自動で反映してから保存
        if self.listbox.curselection():
            self._apply_form_to_selected(silent=True)

        if not self.locations:
            messagebox.showwarning("警告", "観測地点が1件もありません", parent=self.dlg)
            return

        self.on_save(self.locations)
        self.dlg.destroy()
