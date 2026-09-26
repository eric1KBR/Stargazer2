# models.py
# データ構造モデル定義

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class Location:
    id: str
    name: str
    lat: float
    lng: float
    elevation: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "Location":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            lat=float(d.get("lat", 0.0)),
            lng=float(d.get("lng", 0.0)),
            elevation=float(d.get("elevation", 0.0))
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "elevation": self.elevation
        }


@dataclass
class CellPrecomputed:
    """描画高速化のために事前計算されたセル情報"""
    is_high_altitude: bool = False  # 標高考慮対象地点かどうか

    # 標高考慮モード用
    elevation_val: Optional[int] = None
    elevation_status: str = "none"  # "good", "fair", "poor", "none"

    # 総雲量モード用
    total_val: Optional[int] = None
    total_status: str = "none"      # "good", "fair", "poor", "none"

    # 警告テキスト
    wind_text: str = ""             # 設定値以上なら風速数値（例: "6"）、未満は空文字
    fog_text: str = ""              # 霧判定漢字（"高", "中", "露"、なしは空文字）

    # 詳細ポップアップ用生データ参照
    raw_data: Dict[str, Any] = field(default_factory=dict)
