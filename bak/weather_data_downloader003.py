#weather_data_downloader.py
# by manus 2025-11-18



import requests
import pandas as pd
import os
from pathlib import Path
from datetime import datetime

# 1. 地点情報
LOCATIONS = {
    "鮫川村": (36.982514, 140.534597),
    "南会津町": (37.110380, 139.616209),
    "日光": (36.778869, 139.450716),
    "山ノ内町": (36.669601, 138.518654),
    "乗鞍高原": (36.110891, 137.627510),
    "木曽町": (35.930299, 137.627078),
    "白山市一里野": (36.268379, 136.714988),
    "能登_柳田": (37.335247, 137.136606),
    "大多喜町": (35.219871, 140.232766),
}

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Asia/Tokyo"
HOURLY_VARIABLE = "cloud_cover"
BASE_FILENAME = "weather_forecast"

def get_download_folder( ):
    """
    Windows PCのダウンロードフォルダのパスを取得する。
    一般的なパスとして、ユーザーのホームディレクトリ直下の'Downloads'を使用する。
    """
    # Windows/Linux/macOSで動作する一般的な方法
    download_path = Path.home() / "Downloads"
    
    # フォルダが存在しない場合は作成を試みる（通常は存在するはずだが念のため）
    download_path.mkdir(parents=True, exist_ok=True)
    
    return download_path

def fetch_weather_data(latitude, longitude):
    """Open-Meteo APIから指定地点の天気データを取得する"""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_VARIABLE,
        "timezone": TIMEZONE,
    }
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIからのデータ取得中にエラーが発生しました: {e}")
        return None

def process_data():
    """全地点のデータを取得し、指定された形式のCSVに加工してダウンロードフォルダに保存する"""
    
    # データ取得日時を記録
    now = datetime.now()
    fetch_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # ファイル名用の日時フォーマット (YYMMDD_HHMMSS)
    # %y: 年の西暦下2桁, %m: 月, %d: 日, %H: 24時間表記の時, %M: 分, %S: 秒
    filename_time_str = now.strftime("%y%m%d_%H%M%S")
    output_filename = f"{BASE_FILENAME}_{filename_time_str}.csv"
    
    all_data = {}

    for location_name, (lat, lon) in LOCATIONS.items():
        print(f"Fetching data for {location_name}...")
        data = fetch_weather_data(lat, lon)
        
        if data is None or "hourly" not in data:
            print(f"Skipping {location_name} due to data fetching error.")
            continue

        # タイムスタンプと雲量データを抽出
        timestamps = data["hourly"]["time"]
        cloud_cover = data["hourly"][HOURLY_VARIABLE]

        # データを辞書に格納
        all_data[location_name] = pd.Series(cloud_cover, index=timestamps)

    if not all_data:
        print("全ての地点でデータ取得に失敗しました。処理を終了します。")
        return

    # 辞書からDataFrameを作成
    df = pd.DataFrame(all_data)

    # インデックス（タイムスタンプ）をdatetimeオブジェクトに変換
    df.index = pd.to_datetime(df.index)

    # dateとtimeの列を作成
    df.insert(0, 'time', df.index.strftime('%H:%M'))
    df.insert(0, 'date', df.index.strftime('%Y-%m-%d'))

    # インデックスをリセット
    df = df.reset_index(drop=True)

    # 保存先パスを取得
    download_folder = get_download_folder()
    output_path = download_folder / output_filename

    # CSVファイルとして保存
    try:
        # Excelでの文字化けを防ぐため、BOM付きUTF-8で保存
        # まず、取得日時をファイルに書き込む
        with open(output_path, 'w', encoding='utf_8_sig') as f:
            f.write(f"# データ取得日時: {fetch_time_str}\n")
        
        # 次に、データフレームを追記モードで書き込む (header=Trueでヘッダーも書き込まれる)
        df.to_csv(output_path, index=False, encoding='utf_8_sig', mode='a')
        
        print(f"\n✅ 処理が完了しました。")
        print(f"CSVファイルは以下の場所に保存されました: {output_path}")
    except Exception as e:
        print(f"CSVファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    # 必要なライブラリのチェック
    try:
        import requests
        import pandas as pd
    except ImportError:
        print("必要なライブラリ(requests, pandas)がインストールされていません。")
        print("コマンドプロンプトで以下のコマンドを実行してインストールしてください:")
        print("pip install requests pandas")
        exit(1)

    process_data()
