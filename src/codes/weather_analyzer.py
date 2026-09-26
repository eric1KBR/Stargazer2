# weather_analyzer.py
# 雲量重みづけ・霧リスク判定・高速事前計算モジュール

from typing import Dict, List, Tuple, Optional, Any
from .models import Location, CellPrecomputed
from .config import DEFAULT_ELEVATION_THRESHOLD, DEFAULT_WIND_THRESHOLD

def classify_aloft_cloud(mid: float, high: float) -> Tuple[float, str]:
    """
    標高1500m以上向けの上空合成雲量（中層・高層のランダム重なり近似）と状態判定
    - aloft >= 50 or high >= 50 -> poor (不可: グレー)
    - aloft >= 30 or high >= 30 -> fair (可: 黄)
    - それ以外 -> good (良: 青)
    """
    mid_clamped = max(0.0, min(100.0, float(mid)))
    high_clamped = max(0.0, min(100.0, float(high)))
    
    aloft = 100.0 * (1.0 - (1.0 - mid_clamped / 100.0) * (1.0 - high_clamped / 100.0))
    
    if aloft >= 50.0 or high_clamped >= 50.0:
        return aloft, "poor"
    if aloft >= 30.0 or high_clamped >= 30.0:
        return aloft, "fair"
    return aloft, "good"


def classify_total_cloud(total: float) -> str:
    """
    総雲量による基本判定
    - total >= 50 -> poor
    - total >= 30 -> fair
    - それ以外 -> good
    """
    tot = max(0.0, min(100.0, float(total)))
    if tot >= 50.0:
        return "poor"
    if tot >= 30.0:
        return "fair"
    return "good"


def classify_fog_level(temp: float, dew_point: float, humidity: float, wind: float) -> str:
    """
    露点差、湿度、風速に基づく霧・結露判定
    - 高: spread <= 1.0 and humidity >= 95 and wind <= 2.0
    - 中: spread <= 2.0 and humidity >= 90 and wind <= 3.0
    - 露 (結露注意): spread <= 3.0 or humidity >= 85
    - なし (低)
    """
    spread = temp - dew_point
    if spread <= 1.0 and humidity >= 95.0 and wind <= 2.0:
        return "高"
    elif spread <= 2.0 and humidity >= 90.0 and wind <= 3.0:
        return "中"
    elif spread <= 3.0 or humidity >= 85.0:
        return "露"
    return ""


def format_wind_text(wind: float, threshold: float = DEFAULT_WIND_THRESHOLD) -> str:
    """
    風速が閾値以上の場合のみ、数字文字列（四捨五入）を返す
    """
    if wind >= threshold:
        return str(round(wind))
    return ""


def precompute_location_data(
    loc: Location,
    loc_hourly_dict: Dict[str, Dict[str, Any]],
    elevation_threshold: float = DEFAULT_ELEVATION_THRESHOLD,
    wind_threshold: float = DEFAULT_WIND_THRESHOLD
) -> Dict[str, CellPrecomputed]:
    """
    1地点の全時刻について事前計算オブジェクトを生成
    """
    result: Dict[str, CellPrecomputed] = {}
    is_high_altitude = (loc.elevation >= elevation_threshold)

    for t_iso, raw_val in loc_hourly_dict.items():
        if isinstance(raw_val, dict):
            raw = raw_val
        elif isinstance(raw_val, (int, float)):
            # 旧形式（cloud_coverの数値のみ）の後方互換
            raw = {"cloud_cover": raw_val}
        else:
            raw = {}

        cell = CellPrecomputed(raw_data=raw, is_high_altitude=is_high_altitude)
        
        # 総雲量
        tot = raw.get("cloud_cover")
        if tot is not None:
            cell.total_val = round(float(tot))
            cell.total_status = classify_total_cloud(cell.total_val)
        
        # 標高考慮雲量
        if is_high_altitude:
            mid = raw.get("cloud_cover_mid", 0.0)
            high = raw.get("cloud_cover_high", 0.0)
            if mid is not None and high is not None:
                aloft_val, status = classify_aloft_cloud(float(mid), float(high))
                cell.elevation_val = round(aloft_val)
                cell.elevation_status = status
            else:
                cell.elevation_val = cell.total_val
                cell.elevation_status = cell.total_status
        else:
            cell.elevation_val = cell.total_val
            cell.elevation_status = cell.total_status

        # 風速警告
        wind = raw.get("wind_speed_10m")
        if wind is not None:
            cell.wind_text = format_wind_text(float(wind), wind_threshold)
        
        # 霧警告
        temp = raw.get("temperature_2m")
        dew = raw.get("dew_point_2m")
        hum = raw.get("relative_humidity_2m")
        if temp is not None and dew is not None and hum is not None and wind is not None:
            cell.fog_text = classify_fog_level(float(temp), float(dew), float(hum), float(wind))

        result[t_iso] = cell

    return result


def precompute_all(
    locations: List[Location],
    weather_dict: Dict[str, Any],
    elevation_threshold: float = DEFAULT_ELEVATION_THRESHOLD,
    wind_threshold: float = DEFAULT_WIND_THRESHOLD
) -> Dict[str, Dict[str, CellPrecomputed]]:
    """
    全地点の全時刻データを事前計算してキャッシュ辞書を返す
    { loc_id: { time_iso: CellPrecomputed } }
    """
    cache: Dict[str, Dict[str, CellPrecomputed]] = {}
    data_map = weather_dict.get("data", {})

    for loc in locations:
        loc_hourly = data_map.get(loc.id, {})
        cache[loc.id] = precompute_location_data(
            loc, loc_hourly, elevation_threshold, wind_threshold
        )

    return cache
