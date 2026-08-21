"""Location and weather APIs backed by AMap Web Service."""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings

logger = logging.getLogger("location")

router = APIRouter(prefix="/api/location", tags=["定位天气"])

AMAP_BASE_URL = "https://restapi.amap.com/v3"


def _signed_params(params: dict[str, Any]) -> dict[str, Any]:
    # 优先用 Web 服务平台的 key（前端 JS key 调 restapi.amap.com 会返回 10009 USERKEY_PLAT_NOMATCH）
    api_key = settings.AMAP_WEB_SERVICE_KEY or settings.AMAP_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="未配置高德地图 Key")

    data = {**params, "key": api_key, "output": "json"}
    # Web 服务 key 的数字签名需该 key 对应的安全密钥；AMAP_SECURITY_KEY 是前端 JS securityJsCode，不能用于 Web 服务签名。
    # 当前未配置 Web 服务安全密钥，不带签名调用（如控制台对该 key 强制数字签名，需新增配置并在此计算 sig）。
    return data


async def _amap_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"{AMAP_BASE_URL}{path}", params=_signed_params(params))
            response.raise_for_status()
            payload = response.json()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail="高德地图服务暂时不可用") from error

    if payload.get("status") != "1":
        message = payload.get("info") or "高德地图服务返回失败"
        raise HTTPException(status_code=502, detail=message)
    return payload


def _compact_region(address: dict[str, Any]) -> str:
    province = address.get("province") or ""
    city = address.get("city") or ""
    district = address.get("district") or ""
    if isinstance(city, list):
        city = ""
    if isinstance(district, list):
        district = ""
    return " ".join(part for part in [province, city, district] if part)


async def _fetch_weather_by_adcode(adcode: str, region: str = "") -> dict[str, Any]:
    """用 adcode 查实时天气 + 预报，region 为展示用地区名。"""
    live_payload = await _amap_get("/weather/weatherInfo", {"city": adcode, "extensions": "base"})
    forecast_payload = await _amap_get("/weather/weatherInfo", {"city": adcode, "extensions": "all"})

    lives = live_payload.get("lives") or []
    forecasts = forecast_payload.get("forecasts") or []
    live = lives[0] if lives else {}
    casts = (forecasts[0].get("casts") if forecasts else []) or []

    return {
        "province": "",
        "city": "",
        "district": "",
        "adcode": adcode,
        "region": region or adcode,
        "formatted_address": region or adcode,
        "live": {
            "weather": live.get("weather") or "",
            "temperature": live.get("temperature") or "",
            "humidity": live.get("humidity") or "",
            "winddirection": live.get("winddirection") or "",
            "windpower": live.get("windpower") or "",
            "reporttime": live.get("reporttime") or "",
        },
        "forecast": [
            {
                "date": cast.get("date") or "",
                "week": cast.get("week") or "",
                "dayweather": cast.get("dayweather") or "",
                "nightweather": cast.get("nightweather") or "",
                "daytemp": cast.get("daytemp") or "",
                "nighttemp": cast.get("nighttemp") or "",
                "daywind": cast.get("daywind") or "",
                "daypower": cast.get("daypower") or "",
            }
            for cast in casts[:4]
        ],
    }


@router.get("/weather")
async def get_location_weather(
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
):
    """Return reverse-geocoded region plus live weather and forecast."""
    location = f"{longitude:.6f},{latitude:.6f}"
    regeo = await _amap_get(
        "/geocode/regeo",
        {"location": location, "radius": 1000, "extensions": "base"},
    )
    address = regeo.get("regeocode", {}).get("addressComponent", {})
    adcode = str(address.get("adcode") or "")
    region = _compact_region(address)

    if not adcode:
        raise HTTPException(status_code=502, detail="无法解析当前位置")

    payload = await _fetch_weather_by_adcode(adcode, region)
    payload["province"] = address.get("province") or ""
    payload["city"] = "" if isinstance(address.get("city"), list) else (address.get("city") or "")
    payload["district"] = "" if isinstance(address.get("district"), list) else (address.get("district") or "")
    payload["formatted_address"] = regeo.get("regeocode", {}).get("formatted_address") or region
    return payload


@router.get("/weather/by-region")
async def get_weather_by_region(
    region: str = Query(..., min_length=1, max_length=100),
):
    """按地区名查天气（用于 HTTP 环境下浏览器定位不可用时，回退到用户资料中的地区）。"""
    geo = geocode_address_sync(region)
    if not geo or not geo.get("adcode"):
        raise HTTPException(status_code=502, detail="无法解析该地区")

    payload = await _fetch_weather_by_adcode(geo["adcode"], region)
    payload["province"] = geo.get("province") or ""
    payload["city"] = geo.get("city") or ""
    payload["district"] = geo.get("district") or ""
    payload["formatted_address"] = region
    return payload


def geocode_address_sync(address: str, bias: str = "") -> dict[str, Any] | None:
    """同步地理编码：地名 → {province, city, district, adcode}。

    供规则引擎（在 run_in_executor 线程中同步执行）调用。
    bias: 用户所在省/市/区（如"湖南省 长沙市 岳麓区"），用于从多个候选中
          优先选同省的，消歧义（"石塘镇"全国有多个）。
    失败返回 None，调用方自行回退。
    """
    if not address:
        return None
    try:
        params = _signed_params({"address": address})
    except HTTPException:
        return None  # 未配置 Key

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{AMAP_BASE_URL}/geocode/geo", params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as error:
        logger.warning("geocode 调用失败 address=%s: %s", address, error)
        return None

    if payload.get("status") != "1":
        return None
    geocodes = payload.get("geocodes") or []
    if not geocodes:
        return None

    # 多候选时，优先选与 bias 同省的（消歧义，如"石塘镇"全国多个）
    picked = geocodes[0]
    if bias and len(geocodes) > 1:
        bias_province = _extract_province_short(bias)
        if bias_province:
            for g in geocodes:
                if bias_province in (g.get("province") or ""):
                    picked = g
                    logger.info("geocode 消歧义: %s 命中 %s", address, picked.get("province"))
                    break

    province = picked.get("province") or ""
    city = picked.get("city") or ""
    if isinstance(city, list):
        city = ""  # 直辖市时高德返回 []
    district = picked.get("district") or ""
    if isinstance(district, list):
        district = ""
    if not (province or city or district):
        return None
    return {
        "province": province,
        "city": city,
        "district": district,
        "adcode": str(picked.get("adcode") or ""),
    }


def _extract_province_short(region: str) -> str:
    """从 '湖南省 长沙市 岳麓区' 提取省名简称 '湖南'（用于 geocode 候选消歧义）。"""
    if not region:
        return ""
    parts = region.split()
    first = parts[0] if parts else region
    for suffix in ("壮族自治区", "回族自治区", "维吾尔自治区", "自治区", "特别行政区", "省", "市"):
        if first.endswith(suffix):
            return first[:-len(suffix)]
    return first


@lru_cache(maxsize=4096)
def adcode_to_location_sync(adcode: str) -> str | None:
    """高德 adcode → 中心点经纬度字符串 "经度,纬度"（用于和风天气 API 调用）。

    通过高德 /config/district 接口用 adcode 查询行政区划，取返回的中心点坐标。
    adcode→坐标固定不变，故用 lru_cache 永久缓存（全国县级不足 3000 个，maxsize=4096 足够）。

    Args:
        adcode: 高德 6 位行政区划代码，如 "430102"。

    Returns:
        "经度,纬度" 字符串（如 "112.982270,28.194480"），失败返回 None。
    """
    if not adcode:
        return None

    try:
        params = _signed_params({
            "keywords": str(adcode),
            "subdistrict": "0",   # 不返回下级行政区
            "extensions": "base",  # base 即可，不需要 polylines
        })
    except HTTPException:
        return None  # 未配置高德 Key

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{AMAP_BASE_URL}/config/district", params=params)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as error:
        logger.warning("district 调用失败 adcode=%s: %s", adcode, error)
        return None

    if payload.get("status") != "1":
        logger.warning("district 返回失败 adcode=%s: %s", adcode, payload.get("info"))
        return None

    districts = payload.get("districts") or []
    if not districts:
        return None

    # 高德 district 接口返回的中心点字段为 center（"经度,纬度"），不是 location
    center = districts[0].get("center") or ""
    if "," not in center:
        return None
    return center
