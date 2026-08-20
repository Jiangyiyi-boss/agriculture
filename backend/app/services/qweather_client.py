"""和风天气 API 客户端 — 推送 Agent 专用

提供气象预警查询能力：
- 气象预警 /weatheralert/v1/current → 暴雨/高温/大风/寒潮等官方预警（按预警 ID 去重）

注：分钟级降水 /v7/minutely/5m 接口已移除（对微量降水过于敏感，容易误报）。
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from app.core.config import settings

_logger = logging.getLogger("qweather")


def _host() -> str:
    """返回和风 API Host（去前后空白和斜杠）。

    和风 API Key 绑定专属 API Host（控制台分配的 *.qweatherapi.com 域名），
    不能用 devapi.qweather.com / api.qweather.com 兜底，否则返回 403 Invalid Host。
    """
    return (settings.QWEATHER_API_HOST or "").strip().rstrip("/")


def _key() -> str:
    return (settings.QWEATHER_API_KEY or "").strip()


def _is_configured() -> bool:
    return bool(_key()) and bool(_host())


def _get(path: str, params: dict[str, str], timeout: float = 8.0, expect_code: bool = True) -> dict[str, Any] | None:
    """GET 调和风 API，返回 JSON dict；失败返回 None。

    Args:
        expect_code: True（v7 旧接口）检查响应 code=="200"；False（v1 新接口）不检查，
                     新接口用 metadata.zeroResult 判断有无数据。
    """
    if not _is_configured():
        _logger.warning("[和风] API Key 或 Host 未配置，跳过调用")
        return None

    url = f"https://{_host()}/{path.lstrip('/')}"
    params = {**params, "key": _key()}

    try:
        r = httpx.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        _logger.warning(f"[和风] 调用失败 {path}: {e}")
        return None

    if expect_code and str(data.get("code", "")) != "200":
        _logger.warning(f"[和风] {path} 返回错误码: {data.get('code')}")
        return None
    return data


# ============================================================
# 1. 气象预警
# ============================================================

# 预警类型中文 → 推送配置
# 关注的预警类型（其他类型如沙尘、大雾暂不推，避免刷屏）
WARNING_TYPES: dict[str, dict[str, str]] = {
    "暴雨": {"code": "warning_rain", "priority": "1"},
    "暴雪": {"code": "warning_snow", "priority": "1"},
    "寒潮": {"code": "warning_cold", "priority": "2"},
    "大风": {"code": "warning_wind", "priority": "2"},
    "高温": {"code": "warning_heat", "priority": "2"},
    "台风": {"code": "warning_typhoon", "priority": "1"},
    "雷电": {"code": "warning_thunder", "priority": "3"},
    "冰雹": {"code": "warning_hail", "priority": "1"},
    "霜冻": {"code": "warning_frost", "priority": "3"},
    "道路结冰": {"code": "warning_ice", "priority": "3"},
}

# 和风 v1 预警 API color.code 英文 → 中文颜色（用于显示"暴雨黄色预警"）
_COLOR_CN: dict[str, str] = {
    "white": "白", "gray": "灰", "green": "绿",
    "blue": "蓝", "yellow": "黄", "amber": "橙", "orange": "橙",
    "red": "红", "purple": "紫", "black": "黑",
}


def _split_lat_lon(location: str) -> tuple[str, str] | None:
    """把 "经度,纬度" 拆成 (lat, lon) 字符串，用于和风 v1 path 参数。

    和风 v1 路径 /weatheralert/v1/current/{lat}/{lon} 是 纬度在前、经度在后，
    与 v7 query 参数 location=经度,纬度 顺序相反，必须显式拆分。
    小数点后保留两位（和风 API 要求）。
    """
    if not location or "," not in location:
        return None
    parts = location.split(",")
    if len(parts) != 2:
        return None
    try:
        lon_v = round(float(parts[0].strip()), 2)
        lat_v = round(float(parts[1].strip()), 2)
    except (ValueError, TypeError):
        return None
    return f"{lat_v:.2f}", f"{lon_v:.2f}"


def fetch_warnings(location: str) -> list[dict[str, str]]:
    """查询某地的当前气象预警（和风新版 /weatheralert/v1/current/ API）。

    旧版 /v7/warning/now 自 2026-09-01 起停止服务，已切换到新版 v1。
    新版要求经纬度直接放 path（lat/lon 顺序），且响应结构完全不同（alerts 数组）。

    Args:
        location: "经度,纬度" 字符串（如 "112.982,28.194"）。
                  由 app.api.location.adcode_to_location_sync() 转换得到。

    Returns:
        预警列表，每条含 id/title/type/level/text 等（level 已转中文颜色如"黄"）。
        无预警返回空列表；API 失败返回空列表。
    """
    lat_lon = _split_lat_lon(location)
    if not lat_lon:
        _logger.warning(f"[和风] fetch_warnings 无法解析 location={location!r}")
        return []
    lat, lon = lat_lon

    # 新版 v1 API：path 参数 lat/lon；expect_code=False 因为 v1 响应无 code 字段
    data = _get(f"/weatheralert/v1/current/{lat}/{lon}", {"lang": "zh"}, expect_code=False)
    if not data:
        return []

    alerts = data.get("alerts") or []
    result = []
    for w in alerts:
        wtype = (w.get("eventType") or {}).get("name", "")  # 如 "暴雨"
        if wtype not in WARNING_TYPES:
            continue

        # 预警 ID：用和风返回的 id（保证唯一）
        wid = w.get("id") or hashlib.md5(
            f"{w.get('headline','')}-{w.get('effectiveTime','')}-{wtype}".encode("utf-8")
        ).hexdigest()

        color_code = (w.get("color") or {}).get("code", "")
        level_cn = _COLOR_CN.get(color_code, color_code)  # 英文→中文，未知则原样

        # 详细描述：优先 description，其次 instruction（防御指南）
        text = w.get("description") or w.get("instruction") or ""

        result.append({
            "id": wid,
            "title": w.get("headline", ""),
            "type": wtype,
            "level": level_cn,         # 中文颜色（如 "黄"）
            "text": text,
            "start_time": w.get("effectiveTime", ""),
            "end_time": w.get("expireTime", ""),
        })

    return result
