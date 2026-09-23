# storage.py
# JSONファイルの読み書きおよびマイグレーション

import json
import os
from typing import List, Dict, Any, Tuple
from .config import LOCATIONS_FILE, WEATHER_FILE, APP_CONFIG_FILE
from .models import Location
from .api_client import fetch_elevation

DEFAULT_LOCATIONS = [
    Location(id="1", name="幕張の浜", lat=35.640575, lng=140.035070, elevation=5.0),
    Location(id="2", name="野辺山", lat=35.9416, lng=138.4727, elevation=1350.0)
]

def load_json(filepath: str, default: Any) -> Any:
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    return default


def save_json(filepath: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False


def load_locations() -> List[Location]:
    """locations.json から地点リストを読み込む"""
    data = load_json(LOCATIONS_FILE, None)
    if data is None or not isinstance(data, list):
        return [loc for loc in DEFAULT_LOCATIONS]
    return [Location.from_dict(d) for d in data]


def save_locations(locations: List[Location]) -> bool:
    """locations.json に地点リストを保存する"""
    data = [loc.to_dict() for loc in locations]
    return save_json(LOCATIONS_FILE, data)


def ensure_elevations(locations: List[Location]) -> Tuple[List[Location], bool]:
    """
    標高が未設定（0.0以下）の地点がある場合、APIから自動取得して補完する
    戻り値: (更新後リスト, 変更があったか)
    """
    updated = False
    for loc in locations:
        if loc.elevation <= 0.0:
            elev = fetch_elevation(loc.lat, loc.lng)
            if elev is not None:
                loc.elevation = round(elev, 1)
                updated = True
    if updated:
        save_locations(locations)
    return locations, updated


def load_weather_data() -> Dict[str, Any]:
    """weather_data.json を読み込む"""
    return load_json(WEATHER_FILE, {"updated_at": None, "times": [], "data": {}})


def save_weather_data(weather_data: Dict[str, Any]) -> bool:
    """weather_data.json に保存する"""
    return save_json(WEATHER_FILE, weather_data)


def load_app_config() -> Dict[str, Any]:
    """app_config.json を読み込む"""
    default_config = {
        "geometry": "1180x680",
        "view_mode": "3h",          # "3h" または "1h"
        "cloud_mode": "elevation",  # "elevation" または "total"
        "wind_threshold": 5.0,
        "elevation_threshold": 1500
    }
    loaded = load_json(APP_CONFIG_FILE, default_config)
    # デフォルトキーをマージ
    for k, v in default_config.items():
        if k not in loaded:
            loaded[k] = v
    return loaded


def save_app_config(config: Dict[str, Any]) -> bool:
    """app_config.json に保存する"""
    return save_json(APP_CONFIG_FILE, config)
