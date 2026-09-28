# moon_phase.py
# 月齢計算モジュール（PyEphemを使用）

import datetime
from typing import Optional
import ephem


def calculate_moon_age(dt: datetime.datetime) -> float:
    """
    指定日時の月齢（直前の朔・新月からの経過日数）を計算して返します。
    dt がタイムゾーン情報を持たない場合は JST (UTC+9) として扱います。
    """
    if dt.tzinfo is None:
        # naive datetime は JST とみなして UTC に変換
        dt_utc = dt - datetime.timedelta(hours=9)
    else:
        dt_utc = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    ed = ephem.Date(dt_utc)
    prev_nm = ephem.previous_new_moon(ed)
    age = float(ed - prev_nm)
    return age


def get_moon_age_int(dt: datetime.datetime) -> int:
    """
    指定日時の月齢を四捨五入した整数値で返します。
    """
    try:
        age = calculate_moon_age(dt)
        return int(round(age))
    except Exception:
        # 万が一の計算失敗時は 0 等を返すかフォールバック
        return 0
