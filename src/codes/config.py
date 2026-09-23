# config.py
# Stargazer2 設定および定数定義

import os

# --- アプリケーション情報 ---
APP_TITLE = "Stargazer2 260923(1)"

# --- 通信・リトライ設定 ---
MAX_API_RETRIES = 2        # 失敗時の最大再試行回数（計3回試行）
RETRY_DELAY_SEC = 2.0      # 再試行前の待機時間（秒）

# --- ファイルパス (codesフォルダー内) ---
CODES_DIR = os.path.abspath(os.path.dirname(__file__))
LOCATIONS_FILE = os.path.join(CODES_DIR, "locations.json")
WEATHER_FILE = os.path.join(CODES_DIR, "weather_data.json")
APP_CONFIG_FILE = os.path.join(CODES_DIR, "app_config.json")

# --- 観測・判定設定 ---
TARGET_HOURS_3H = [0, 3, 6, 12, 18, 21]
DEFAULT_ELEVATION_THRESHOLD = 1500  # 標高考慮モードの閾値 (m)
DEFAULT_WIND_THRESHOLD = 5.0        # 風速警告表示の閾値 (m/s)

# --- カラーパレット ---
COLORS = {
    "bg": "#0f172a",          # 全体背景 (ダークスレート)
    "header_bg": "#1e293b",   # ヘッダー・サイドバー背景
    "text": "#e2e8f0",        # 基本文字色
    "text_dim": "#94a3b8",    # 薄い文字色
    "border": "#334155",      # セル枠線
    "accent": "#38bdf8",      # プライマリアクセント (スカイブルー)
    "accent_hover": "#0284c7",
    "danger": "#ef4444",      # 赤 (中止ボタン等)
    "btn_active": "#334155",  # 押下中ボタンスタイル

    # 判定背景色
    "status_good": "#38bdf8",     # 良 (<30%): スカイブルー
    "status_fair": "#fde047",     # 可 (30-50%): イエロー
    "status_poor": "#64748b",     # 不可 (>=50%): グレー

    # セル内基本文字色（雲量数値用）
    "text_good": "#0f172a",       # スカイブルー背景上の濃い文字
    "text_fair": "#0f172a",       # イエロー背景上の濃い文字
    "text_poor": "#f8fafc",       # グレー背景上の白系文字
    "text_nodata": "#94a3b8",     # データなし時の薄い文字

    # 警告文字色（風速・霧用: 明るい赤）
    "alert_good": "#dc2626",      # 良（青背景）上の明るい赤
    "alert_fair": "#dc2626",      # 可（黄背景）上の明るい赤
    "alert_poor": "#fca5a5",      # 不可（グレー背景）上の明るい赤

    # 正午 (12:00) のサイドバー配色
    "noon_bg": "#facc15",
    "noon_text": "#0f172a"
}

# --- セル描画サイズ ---
CELL_WIDTH = 100
CELL_HEIGHT = 54
HEADER_HEIGHT = 44
SIDEBAR_WIDTH = 80
