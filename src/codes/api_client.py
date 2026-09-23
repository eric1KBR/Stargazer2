# api_client.py
# Open-Meteo API 通信クライアント（気象データ取得・標高取得）

import requests
from typing import Optional, Dict, Any, List

ELEVATION_API_URL = "https://api.open-meteo.com/v1/elevation"
JMA_API_URL = "https://api.open-meteo.com/v1/jma"
FALLBACK_API_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "temperature_2m",
    "dew_point_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation"
]

def fetch_elevation(lat: float, lng: float, timeout: int = 10) -> Optional[float]:
    """
    Open-Meteo Elevation API を使用して緯度・経度から標高(m)を取得
    """
    try:
        params = {"latitude": lat, "longitude": lng}
        resp = requests.get(ELEVATION_API_URL, params=params, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            elevations = data.get("elevation")
            if elevations and len(elevations) > 0:
                return float(elevations[0])
    except Exception as e:
        print(f"Elevation fetch error ({lat}, {lng}): {e}")
    return None


def fetch_location_weather(
    lat: float,
    lng: float,
    elevation: float = 0.0,
    timeout: int = 15
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    1地点の10日分気象データを取得（気象庁JMAモデル優先、フォールバックあり）
    戻り値: { "2026-09-23T00:00": { "cloud_cover": 20, ... }, ... }
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "elevation": elevation,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "Asia/Tokyo",
        "wind_speed_unit": "ms",
        "forecast_days": 10
    }

    # 1. JMAモデルでリクエスト
    data = None
    try:
        resp = requests.get(JMA_API_URL, params=params, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
    except Exception as e:
        print(f"JMA API request error: {e}")

    # 2. 失敗時は汎用forecastモデルにフォールバック
    if not data or "hourly" not in data:
        try:
            resp = requests.get(FALLBACK_API_URL, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
        except Exception as e:
            print(f"Fallback forecast API request error: {e}")
            return None

    if not data or "hourly" not in data:
        return None

    hourly = data["hourly"]
    times = hourly.get("time", [])
    if not times:
        return None

    parsed_result: Dict[str, Dict[str, Any]] = {}
    for i, t_iso in enumerate(times):
        record: Dict[str, Any] = {}
        for var in HOURLY_VARS:
            arr = hourly.get(var)
            if arr is not None and i < len(arr):
                record[var] = arr[i]
            else:
                record[var] = None
        parsed_result[t_iso] = record

    return parsed_result
