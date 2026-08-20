"""种植计划规则引擎

基于 MySQL 结构化查询的种植推荐引擎，不走向量检索。
核心功能：
  1. 地区解析：用户 region 字符串 → province/city/county
  2. 土壤查询：逐级降级 county → city → province
  3. 作物筛选：pH + 土壤质地 + 地域适配
  4. 目标打分：经济效益 / 自己吃 / 兼顾
  5. 意图识别：作物推荐 / 种植方案 / 轮作推荐
  6. 面积提取：从问题文本 / FarmLand
  7. 合理性判断：指定作物是否适合当地
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.location import geocode_address_sync
from app.models import (
    AdminDistrict,
    CropManagement,
    CropSuitability,
    FarmLand,
    SoilData,
    User,
)


logger = logging.getLogger("planting_retriever")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class RegionInfo:
    """解析后的地区信息"""
    province: str = ""
    city: str = ""
    county: str = ""
    raw: str = ""
    ambiguous: bool = False            # 地点被检测到但无法解析到县级
    mentioned_location: str = ""       # 用户提到的原始地点文本（如"石塘镇"）
    geocoded: bool = False             # 是否经高德 geocode 解析（用于 prompt 提示归属）


@dataclass
class SoilInfo:
    """土壤查询结果"""
    province: str = ""
    city: str = ""
    county: str = ""
    texture: str = ""        # 质地，如 "壤土" / "轻粘土"
    organic_matter: float | None = None
    ph_min: float | None = None
    ph_max: float | None = None
    ph_value: str = ""       # 原文，如 "5.5-6.5"
    source_level: str = ""   # county / city / province（实际命中的级别）
    found: bool = False


@dataclass
class CropCandidate:
    """打分后的作物候选"""
    crop: CropSuitability
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass
class SuitabilityResult:
    """指定作物合理性判断结果（意图②用）"""
    crop: CropSuitability | None
    is_suitable: bool
    reasons: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 地区解析
# ---------------------------------------------------------------------------

def resolve_region(db: Session, region_str: str) -> RegionInfo:
    """从用户 region 字符串解析出 province/city/county。

    用户 region 格式可能是 "湖南省 长沙市 岳麓区" 或 "湖南 长沙 岳麓" 等。
    优先用 admin_district 表精确匹配，匹配失败则按空格/省市区后缀拆分。
    """
    info = RegionInfo(raw=region_str or "")
    if not region_str:
        return info

    text = region_str.strip()
    # 去掉省市区后缀后按空格拆分
    cleaned = re.sub(r"[省市县区]+", "", text)
    parts = [p.strip() for p in re.split(r"[\s,，、]+", cleaned) if p.strip()]

    # 按从具体到粗略的顺序搜索（county → city → province）
    # parts 通常为 [province, city, county]，倒序搜索避免 "湖南" 误匹配 county
    parts_reversed = list(reversed(parts))

    # 策略1：用 county 匹配（最精确）
    for part in parts_reversed:
        records = db.query(AdminDistrict).filter(
            AdminDistrict.county.like(f"%{part}%")
        ).limit(5).all()
        if records:
            r = records[0]
            info.province = r.province or ""
            info.city = r.city or ""
            info.county = r.county or ""
            return info

    # 策略2：用 city 匹配
    for part in parts_reversed:
        records = db.query(AdminDistrict).filter(
            AdminDistrict.city.like(f"%{part}%")
        ).limit(5).all()
        if records:
            r = records[0]
            info.province = r.province or ""
            info.city = r.city or ""
            return info

    # 策略3：用 province 匹配
    for part in parts_reversed:
        records = db.query(AdminDistrict).filter(
            AdminDistrict.province.like(f"%{part}%")
        ).limit(5).all()
        if records:
            info.province = records[0].province or ""
            return info

    # 策略4：兜底，按位置赋值
    if len(parts) >= 3:
        info.province, info.city, info.county = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        info.province, info.city = parts[0], parts[1]
    elif len(parts) == 1:
        info.province = parts[0]

    return info


# ---------------------------------------------------------------------------
# 土壤查询（逐级降级）
# ---------------------------------------------------------------------------

def _avg_soil(records: list[SoilData]) -> SoilInfo:
    """对多条土壤记录取均值，返回 SoilInfo。"""
    if not records:
        return SoilInfo()
    ph_mins = [r.ph_min for r in records if r.ph_min is not None]
    ph_maxs = [r.ph_max for r in records if r.ph_max is not None]
    organics = [r.organic_matter for r in records if r.organic_matter is not None]
    textures = [r.texture for r in records if r.texture]

    info = SoilInfo(
        province=records[0].province or "",
        city=records[0].city or "",
        county=records[0].county or "",
        texture=textures[0] if textures else "",
        organic_matter=round(sum(organics) / len(organics), 1) if organics else None,
        ph_min=round(sum(ph_mins) / len(ph_mins), 1) if ph_mins else None,
        ph_max=round(sum(ph_maxs) / len(ph_maxs), 1) if ph_maxs else None,
        ph_value=records[0].ph_value or "",
        found=True,
    )
    return info


def _normalize_province(name: str) -> str:
    """省名归一化：去掉自治区/省/市等后缀，便于跨表匹配。
    如 '广西壮族自治区' → '广西', '广西壮族' → '广西', '内蒙古自治区' → '内蒙古'
    """
    if not name:
        return ""
    # 按长度倒序匹配，避免短名先替换
    suffixes = [
        "壮族自治区", "回族自治区", "维吾尔自治区", "自治区",
        "特别行政区", "省", "市",
        # admin_district 表中可能存储的不完整后缀
        "壮族", "回族", "维吾尔",
    ]
    result = name
    for suffix in suffixes:
        if result.endswith(suffix):
            result = result[: -len(suffix)]
            break
    return result


def resolve_soil(db: Session, region: RegionInfo) -> SoilInfo:
    """逐级降级查土壤数据：county → city → province。"""
    province_short = _normalize_province(region.province)

    # ① county 级别
    if region.county:
        county_core = re.sub(r"[县区市]+$", "", region.county)
        records = db.query(SoilData).filter(
            or_(
                SoilData.province.like(f"%{region.province}%"),
                SoilData.province.like(f"%{province_short}%"),
            ),
            or_(
                SoilData.county.like(f"%{region.county}%"),
                SoilData.county.like(f"%{county_core}%"),
            ),
        ).limit(50).all()
        if records:
            info = _avg_soil(records)
            info.source_level = "county"
            logger.info("土壤查询命中 county 级: %s %s (%d条)", region.city, region.county, len(records))
            return info

    # ② city 级别
    if region.city:
        city_core = re.sub(r"[州市区县]+$", "", region.city)
        records = db.query(SoilData).filter(
            or_(
                SoilData.province.like(f"%{region.province}%"),
                SoilData.province.like(f"%{province_short}%"),
            ),
            or_(
                SoilData.city.like(f"%{region.city}%"),
                SoilData.city.like(f"%{city_core}%"),
            ),
        ).limit(50).all()
        if records:
            info = _avg_soil(records)
            info.source_level = "city"
            logger.info("土壤查询降级到 city 级: %s (%d条)", region.city, len(records))
            return info

    # ③ province 级别
    if region.province:
        records = db.query(SoilData).filter(
            or_(
                SoilData.province.like(f"%{region.province}%"),
                SoilData.province.like(f"%{province_short}%"),
            ),
        ).limit(100).all()
        if records:
            info = _avg_soil(records)
            info.source_level = "province"
            logger.info("土壤查询降级到 province 级: %s/%s (%d条)", region.province, province_short, len(records))
            return info

    logger.warning("土壤查询未命中任何级别: %s", region.raw)
    return SoilInfo()


# ---------------------------------------------------------------------------
# 作物筛选
# ---------------------------------------------------------------------------

def _texture_match(crop_soil_types: str, local_texture: str) -> bool:
    """检查当地土壤质地是否在作物适宜土壤类型中。

    作物的 soil_types 可能是 "壤土、黏土" 或 "沙壤土、壤土"。
    当地质地可能是 "壤土" / "轻粘土" / "粘土" / "沙壤土" 等。
    匹配策略：
      1. 去掉轻重中前缀后精确匹配（"轻粘土" → "粘土" 匹配 "黏土"）
      2. 宽松匹配：当地含"粘"且作物含"粘/黏" → 匹配
      3. 宽松匹配：轻粘土/粘壤土 与 壤土 互相兼容（实际农业中可改良）
    """
    if not crop_soil_types or not local_texture:
        return True  # 缺数据时不作为过滤条件

    # 归一化：黏→粘
    crop_types = crop_soil_types.replace("黏", "粘")
    local = local_texture.replace("黏", "粘")

    # 去掉轻重中前缀，得到核心质地
    local_core = re.sub(r"^[轻重中]", "", local)
    # 提取作物要求的质地关键词（按顿号/逗号分割）
    crop_keywords = [kw.strip() for kw in re.split(r"[、,，/]+", crop_types) if kw.strip()]

    # 策略1：核心质地精确匹配
    for kw in crop_keywords:
        kw_core = re.sub(r"^[轻重中]", "", kw)
        if kw_core == local_core or kw_core in local_core or local_core in kw_core:
            return True

    # 策略2：粘土类匹配
    if "粘" in local_core:
        for kw in crop_keywords:
            if "粘" in kw:
                return True

    # 策略3：壤土类宽松匹配（轻粘土/粘壤土 可种植要求壤土的作物，实际可改良）
    if "壤" in local_core or "粘" in local_core:
        for kw in crop_keywords:
            if "壤土" in kw:
                return True

    # 策略4：沙土类匹配
    if "沙" in local_core:
        for kw in crop_keywords:
            if "沙" in kw:
                return True

    return False


def _region_match(crop_region_fit: str, region: RegionInfo) -> bool:
    """检查作物的地域适配是否与用户所在地区匹配。"""
    if not crop_region_fit:
        return True
    if "全国通用" in crop_region_fit:
        return True

    # 判断用户是南方还是北方
    south_provinces = (
        "湖南", "湖北", "广东", "广西", "海南", "福建", "江西", "浙江",
        "云南", "贵州", "四川", "重庆", "上海", "江苏", "安徽", "西藏",
    )
    north_provinces = (
        "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
        "山东", "河南", "陕西", "甘肃", "青海", "宁夏", "新疆",
    )
    is_south = any(region.province.startswith(p) for p in south_provinces) if region.province else None
    is_north = any(region.province.startswith(p) for p in north_provinces) if region.province else None

    if "南方" in crop_region_fit and is_south:
        return True
    if "北方" in crop_region_fit and is_north:
        return True
    # 无法判断南北时，不过滤
    if is_south is None and is_north is None:
        return True
    return False


def filter_crops(
    db: Session,
    soil: SoilInfo,
    region: RegionInfo,
    seasons: list[str] | None = None,
) -> list[CropSuitability]:
    """根据土壤 pH、质地、地域适配、季节筛选作物。"""
    query = db.query(CropSuitability)

    # pH 过滤：当地 pH 需在作物适宜范围内
    if soil.ph_min is not None and soil.ph_max is not None:
        # 用 ph_min/ph_max 做 SQL 过滤可能有精度问题，先拉全量再 Python 过滤
        pass

    all_crops = query.all()
    results: list[CropSuitability] = []

    for crop in all_crops:
        # pH 匹配：当地 pH 需在作物 [ph_min, ph_max] 范围内
        if soil.ph_min is not None and crop.ph_min is not None and crop.ph_max is not None:
            # 用当地 pH 范围的中值判断
            local_ph = (soil.ph_min + soil.ph_max) / 2
            if not (crop.ph_min <= local_ph <= crop.ph_max):
                continue

        # 土壤质地匹配
        if soil.texture and not _texture_match(crop.soil_types or "", soil.texture):
            continue

        # 地域适配匹配
        if region.province and not _region_match(crop.region_fit or "", region):
            continue

        # 季节匹配（如果用户指定了月份）
        if seasons:
            crop_seasons = crop.sow_seasons or ""
            if not any(s in crop_seasons for s in seasons):
                continue

        results.append(crop)

    logger.info("作物筛选: %d/%d 通过 (pH=%s, 质地=%s, 季节=%s)", len(results), len(all_crops),
                f"{soil.ph_min}-{soil.ph_max}" if soil.ph_min else "未知", soil.texture or "未知",
                "/".join(seasons) if seasons else "无")
    return results


# ---------------------------------------------------------------------------
# 目标打分
# ---------------------------------------------------------------------------

# 类别优先级（按目标）
GOAL_PRIORITY: dict[str, dict[str, int]] = {
    "经济效益": {"经济作物": 5, "水果": 4, "蔬菜": 3, "粮食作物": 2},
    "自己吃": {"蔬菜": 5, "粮食作物": 4, "水果": 3, "经济作物": 1},
    "兼顾": {"蔬菜": 4, "粮食作物": 4, "水果": 3, "经济作物": 3},
}


def score_crops(
    candidates: list[CropSuitability],
    goal: str,
    area: float | None = None,
) -> list[CropCandidate]:
    """按目标对候选作物打分排序。"""
    priority = GOAL_PRIORITY.get(goal, GOAL_PRIORITY["兼顾"])
    scored: list[CropCandidate] = []

    for crop in candidates:
        score = 0.0
        reasons: list[str] = []

        # ① 类别优先级
        cat_score = priority.get(crop.category, 2)
        score += cat_score * 10
        reasons.append(f"{crop.category}类")

        # ② 亩产（经济效益时权重更高）
        if crop.yield_max and crop.yield_max > 0:
            yield_score = min(crop.yield_max / 1000, 10)  # 每1000kg得1分，上限10分
            if goal == "经济效益":
                yield_score *= 1.5
            score += yield_score
            if goal == "经济效益":
                reasons.append(f"亩产高({crop.yield_ref})")

        # ③ 生长周期（自己吃时短周期加分）
        if not crop.is_perennial and crop.cycle_max and crop.cycle_max > 0:
            if goal == "自己吃":
                cycle_score = max(0, (150 - crop.cycle_max) / 10)  # 越短分越高
                score += cycle_score
                if crop.cycle_max <= 90:
                    reasons.append(f"短周期({crop.cycle_max}天)")
        elif crop.is_perennial:
            if goal == "经济效益":
                score += 3  # 多年生长期收益
                reasons.append("多年生长期收益")
            elif goal == "自己吃":
                score -= 2  # 自己吃不太需要多年生

        # ④ 耐旱/耐寒（降低种植难度）
        if crop.drought_resistance == "高":
            score += 1
        if crop.cold_resistance == "高":
            score += 1

        scored.append(CropCandidate(crop=crop, score=round(score, 1), reasons=reasons))

    scored.sort(key=lambda x: x.score, reverse=True)
    logger.info("作物打分完成: goal=%s, top3=%s", goal,
                [(c.crop.crop_name, c.score) for c in scored[:3]])
    return scored


# ---------------------------------------------------------------------------
# 合理性判断（意图②用）
# ---------------------------------------------------------------------------

def check_crop_suitability(
    db: Session,
    crop_name: str,
    soil: SoilInfo,
    region: RegionInfo,
) -> SuitabilityResult:
    """判断指定作物在当前地区是否适合种植。"""
    # 查找该作物
    crop = db.query(CropSuitability).filter(
        CropSuitability.crop_name.like(f"%{crop_name}%")
    ).first()

    if not crop:
        return SuitabilityResult(crop=None, is_suitable=False, reasons=[], mismatches=[f"知识库中无'{crop_name}'的适宜性数据"])

    mismatches: list[str] = []
    reasons: list[str] = []

    # pH 判断
    if soil.ph_min is not None and crop.ph_min is not None and crop.ph_max is not None:
        local_ph = (soil.ph_min + soil.ph_max) / 2
        if crop.ph_min <= local_ph <= crop.ph_max:
            reasons.append(f"pH适配(当地{soil.ph_min}-{soil.ph_max}，作物需{crop.ph_range})")
        else:
            mismatches.append(f"pH不匹配(当地{soil.ph_min}-{soil.ph_max}，作物需{crop.ph_range})")

    # 土壤质地判断
    if soil.texture and crop.soil_types:
        if _texture_match(crop.soil_types, soil.texture):
            reasons.append(f"土壤质地适配(当地{soil.texture}，作物宜{crop.soil_types})")
        else:
            mismatches.append(f"土壤质地不匹配(当地{soil.texture}，作物宜{crop.soil_types})")

    # 地域判断
    if region.province and crop.region_fit:
        if _region_match(crop.region_fit, region):
            reasons.append(f"地域适配({crop.region_fit})")
        else:
            mismatches.append(f"地域不匹配(作物适宜{crop.region_fit}，当地为{region.province})")

    is_suitable = len(mismatches) == 0
    return SuitabilityResult(crop=crop, is_suitable=is_suitable, reasons=reasons, mismatches=mismatches)


# ---------------------------------------------------------------------------
# 意图识别 + 目标检测 + 面积提取
# ---------------------------------------------------------------------------

INTENT_KEYWORDS = {
    "rotation": ("轮作", "换茬", "下季种什么", "下茬", "接茬", "倒茬", "连作"),
    "plan": ("我想种", "要种", "种XX", "怎么种", "能种吗", "可以种", "种植方案",
             "几月种", "什么时候种", "种多少", "种植时间", "XX怎么种", "种番茄", "种水稻"),
}
GOAL_KEYWORDS = {
    "经济效益": ("赚钱", "卖", "收入", "利润", "经济效益", "挣钱", "变现", "经济作物"),
    "自己吃": ("自己吃", "家里吃", "自给", "自己种来吃", "吃的"),
}

CROP_NAMES_CACHE: list[str] | None = None


def _load_crop_names(db: Session) -> list[str]:
    """加载所有作物名称，用于从问题中识别指定作物。"""
    global CROP_NAMES_CACHE
    if CROP_NAMES_CACHE is None:
        crops = db.query(CropSuitability.crop_name).all()
        CROP_NAMES_CACHE = [c[0] for c in crops if c[0]]
    return CROP_NAMES_CACHE


# ---------------------------------------------------------------------------
# 从问题文本提取地点 / 月份 / 目标
# ---------------------------------------------------------------------------

# 常见城市/县名缓存（避免每次查库）
_CITY_COUNTY_CACHE: list[tuple[str, str, str]] | None = None  # [(province, city, county), ...]


def _load_city_county_cache(db: Session) -> list[tuple[str, str, str]]:
    """加载所有城市/县名，用于从问题文本中匹配地点。"""
    global _CITY_COUNTY_CACHE
    if _CITY_COUNTY_CACHE is None:
        records = db.query(AdminDistrict.province, AdminDistrict.city, AdminDistrict.county).all()
        _CITY_COUNTY_CACHE = [(r[0] or "", r[1] or "", r[2] or "") for r in records]
    return _CITY_COUNTY_CACHE


# 排除的常见干扰词（可能被误识别为地名）
_LOCATION_STOPWORDS = {"全国", "中国", "本地", "当地", "这里", "那里", "我家", "我家地", "一块地"}


# 三级地名匹配配置：差异集中在此表（后缀正则、tuple 索引、填充字段）
_LEVEL_CONFIG: dict[str, dict] = {
    "county":   {"suffix": r"[县区市]+$",                 "idx": 2, "fields": ("province", "city", "county")},
    "city":     {"suffix": r"[州市区县]+$",               "idx": 1, "fields": ("province", "city")},
    "province": {"suffix": r"[省自治区壮族回族维吾尔]+$", "idx": 0, "fields": ("province",)},
}


def _match_admin_level(question: str, cache: list[tuple[str, str, str]], level: str) -> RegionInfo | None:
    """在某一级（county/city/province）里找 question 中出现过的地名。

    cache 元组结构：(province, city, county)。
    按地名长度倒序匹配（长名优先，避免"州"误匹配"全州"的"州"）。
    """
    cfg = _LEVEL_CONFIG[level]
    idx = cfg["idx"]
    fields = cfg["fields"]

    # 收集该级候选 + 用前缀去重 + 按长度倒序
    seen: set[tuple] = set()
    candidates: list[tuple[tuple[str, str, str], str]] = []
    for row in cache:
        value = row[idx]
        if not value or value in _LOCATION_STOPWORDS:
            continue
        key = row[: idx + 1]  # (p,) / (p, c) / (p, c, co)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((row, value))
    candidates.sort(key=lambda x: len(x[1]), reverse=True)

    for row, value in candidates:
        core = re.sub(cfg["suffix"], "", value)
        if core and len(core) >= 2 and core in question:
            # county 级特殊处理：避免"衡阳市"误匹配"衡阳县"（去后缀后 core="衡阳" 都能命中）
            # 若 question 里 core 后面紧跟"市"，说明用户指的是地级市，应交给 city 级处理，跳过此 county
            if level == "county":
                pos = question.find(core)
                after_char = question[pos + len(core):pos + len(core) + 1]
                if after_char == "市":
                    continue
            return RegionInfo(
                province=row[0] if "province" in fields else "",
                city=row[1] if "city" in fields else "",
                county=row[2] if "county" in fields else "",
                raw=question,
            )
        if value in question:
            return RegionInfo(
                province=row[0] if "province" in fields else "",
                city=row[1] if "city" in fields else "",
                county=row[2] if "county" in fields else "",
                raw=question,
            )
    return None


def extract_region_from_question(
    question: str, db: Session, user: User | None = None,
) -> RegionInfo | None:
    """从问题文本中提取地点，返回 RegionInfo 或 None。

    流程：
      1. county → city → province 三级匹配（admin_district 表内存查表，0ms、零外部依赖）
      2. 都没命中 → 检测镇/乡/村 → 高德 geocode 解析所属县
      3. geocode 失败 → ambiguous 兜底（让 Agent 引导用户补充县名）
    """
    if not question:
        return None

    cache = _load_city_county_cache(db)

    # 策略1-3：三级已知地名快速通道（表里已有标准化数据，无需 geocode）
    for level in ("county", "city", "province"):
        hit = _match_admin_level(question, cache, level)
        if hit:
            return hit

    # 策略4：检测镇/乡/村（行政区划表只到县级）→ 高德 geocode 解析所属县
    town_match = re.search(r"([\u4e00-\u9fa5]{2,6}(?:镇|乡|村|街道))", question)
    if town_match:
        town_name = town_match.group(1)
        # 去掉常见前缀（我在石塘镇 → 石塘镇）
        for prefix in ("我在", "你在", "他在", "她在", "住在", "在", "有", "的", "去", "到"):
            if town_name.startswith(prefix) and len(town_name) > len(prefix) + 1:
                town_name = town_name[len(prefix):]
                break

        # 用高德 geocode 解析镇所属的县；user.region 作为 bias 消歧义（如"湖南 石塘镇"）
        bias = (user.region if user and user.region else "") or ""
        geocoded = geocode_address_sync(town_name, bias=bias)
        if geocoded and (geocoded["province"] or geocoded["city"] or geocoded["district"]):
            logger.info("geocode 解析镇级地名: %s → %s/%s/%s",
                        town_name, geocoded["province"], geocoded["city"], geocoded["district"])
            return RegionInfo(
                province=geocoded["province"],
                city=geocoded["city"],
                county=geocoded["district"],
                raw=question,
                ambiguous=False,
                mentioned_location=town_name,
                geocoded=True,
            )
        logger.info("geocode 无法解析镇级地名: %s，回退 ambiguous", town_name)
        return RegionInfo(
            province="", city="", county="", raw=question,
            ambiguous=True, mentioned_location=town_name,
        )

    return None


def extract_month_from_question(question: str) -> int | None:
    """从问题文本提取月份（1-12）。"""
    if not question:
        return None
    # "八月份" / "8月" / "八月"
    m = re.search(r"(\d{1,2})\s*月", question)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return month
    # 中文数字月份
    cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
              "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}
    m = re.search(r"(十一|十二|一|二|三|四|五|六|七|八|九|十)\s*月", question)
    if m:
        return cn_map.get(m.group(1))
    return None


def month_to_seasons(month: int) -> list[str]:
    """月份转季节列表（可能有跨季节）。"""
    if month in (3, 4, 5):
        return ["春季"]
    if month in (6, 7):
        return ["夏季"]
    if month == 8:
        return ["夏季", "秋季"]  # 8月是夏末秋初
    if month in (9, 10, 11):
        return ["秋季"]
    if month in (12, 1, 2):
        return ["冬季", "春季"]  # 冬播春收
    return []


def detect_intent(question: str, db: Session | None = None) -> str:
    """识别用户意图：recommend（作物推荐）/ plan（种植方案）/ rotation（轮作推荐）。"""
    if not question:
        return "recommend"

    # ③ 轮作
    if any(kw in question for kw in INTENT_KEYWORDS["rotation"]):
        return "rotation"

    # ② 种植方案：用户指定了具体作物 + 种植相关问题
    if db and any(kw in question for kw in INTENT_KEYWORDS["plan"]):
        crop_names = _load_crop_names(db)
        for name in crop_names:
            if name in question:
                return "plan"
        # 问题里有"种"字+2字以上作物名，也判定为plan
        if re.search(r"种[\u4e00-\u9fa5]{1,6}", question):
            return "plan"

    # ① 默认：作物推荐
    return "recommend"


def detect_goal(question: str) -> str:
    """检测用户目标：经济效益 / 自己吃 / 兼顾。"""
    if not question:
        return "兼顾"
    # 经济效益：精确关键词
    for kw in GOAL_KEYWORDS["经济效益"]:
        if kw in question:
            return "经济效益"
    # 自己吃：精确关键词
    for kw in GOAL_KEYWORDS["自己吃"]:
        if kw in question:
            return "自己吃"
    # 自己吃：宽松模式 "自己...吃" / "自己...可以吃" / "家里...吃"
    if re.search(r"自己.{0,8}吃", question) or re.search(r"家里.{0,8}吃", question):
        return "自己吃"
    return "兼顾"


def extract_area_from_question(question: str) -> float | None:
    """从问题文本提取面积（亩）。"""
    if not question:
        return None
    # "2亩" / "两亩" / "2.5亩" / "3亩地"
    m = re.search(r"(\d+\.?\d*)\s*亩", question)
    if m:
        return float(m.group(1))
    # 中文数字
    cn_map = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    m = re.search(r"([一二两三四五六七八九十]+)\s*亩", question)
    if m:
        cn = m.group(1)
        if cn == "十":
            return 10.0
        if cn.startswith("十"):
            return 10.0 + cn_map.get(cn[1], 0)
        if "十" in cn:
            parts = cn.split("十")
            tens = cn_map.get(parts[0], 1) if parts[0] else 1
            ones = cn_map.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return float(tens * 10 + ones)
        if cn in cn_map:
            return float(cn_map[cn])
    return None


def get_user_area(db: Session, user: User, question: str = "") -> float | None:
    """获取用户面积：问题文本 → FarmLand → None。"""
    # ① 从问题提取
    area = extract_area_from_question(question)
    if area:
        return area

    # ② 查 FarmLand 表
    lands = db.query(FarmLand).filter(FarmLand.user_id == user.id).all()
    if lands:
        total = sum(land.area for land in lands if land.area)
        if total > 0:
            return total

    return None


def extract_specified_crop(question: str, db: Session) -> str | None:
    """从问题中提取用户指定的作物名称（意图②用）。"""
    crop_names = _load_crop_names(db)
    for name in crop_names:
        if name in question:
            return name
    return None


# ---------------------------------------------------------------------------
# 组装规则引擎结果
# ---------------------------------------------------------------------------

@dataclass
class RuleEngineResult:
    """规则引擎整体输出"""
    intent: str = "recommend"       # recommend / plan / rotation
    goal: str = "兼顾"              # 经济效益 / 自己吃 / 兼顾
    area: float | None = None
    region: RegionInfo | None = None
    soil: SoilInfo | None = None
    month: int | None = None        # 用户提到的月份
    seasons: list[str] = field(default_factory=list)  # 月份对应的季节
    region_from_question: bool = False  # 地点是否来自问题文本
    # 意图①：作物推荐
    candidates: list[CropCandidate] = field(default_factory=list)
    # 意图②：种植方案
    specified_crop: str | None = None
    suitability: SuitabilityResult | None = None
    # 意图③：轮作推荐
    rotation_by_season: dict[str, list[CropSuitability]] = field(default_factory=dict)


def run_rule_engine(
    db: Session,
    user: User,
    question: str,
) -> RuleEngineResult:
    """执行规则引擎，返回结构化结果。"""
    result = RuleEngineResult()

    # 意图 + 目标
    result.intent = detect_intent(question, db)
    result.goal = detect_goal(question)

    # 面积
    result.area = get_user_area(db, user, question)

    # 月份 + 季节
    result.month = extract_month_from_question(question)
    if result.month:
        result.seasons = month_to_seasons(result.month)

    # 地区：优先从问题文本提取，提取不到再用 user.region
    question_region = extract_region_from_question(question, db, user=user)
    if question_region and question_region.ambiguous:
        # 用户提到了镇/乡/村，但无法解析到县级 → 不回退到 user.region
        result.region = question_region
        result.region_from_question = True
        result.soil = SoilInfo()  # 无法查土壤
        logger.info("地区不明确(镇/乡/村): %s，跳过土壤查询", question_region.mentioned_location)

        logger.info("规则引擎: intent=%s, goal=%s, area=%s, month=%s, region=不明确(%s), soil_found=False",
                    result.intent, result.goal, result.area, result.month,
                    question_region.mentioned_location)

        # 地点不明确时仍可按全国通用作物推荐（不过滤地域和土壤）
        if result.intent == "recommend":
            all_crops = db.query(CropSuitability).filter(
                CropSuitability.region_fit.like("%全国%")
            ).all()
            # 如果全国通用的太少，放宽到全部作物
            if len(all_crops) < 3:
                all_crops = db.query(CropSuitability).all()
            # 按季节筛选（如有月份）
            if result.seasons:
                all_crops = [c for c in all_crops if c.sow_seasons and any(s in c.sow_seasons for s in result.seasons)]
            scored = score_crops(all_crops, result.goal, result.area)
            result.candidates = scored[:8]
        return result

    if question_region and question_region.province:
        result.region = question_region
        result.region_from_question = True
        logger.info("地区来自问题文本: %s/%s/%s", question_region.province, question_region.city, question_region.county)
    else:
        region_str = user.region or ""
        result.region = resolve_region(db, region_str)
        logger.info("地区来自用户资料: %s", region_str)

    # 土壤
    result.soil = resolve_soil(db, result.region)

    logger.info("规则引擎: intent=%s, goal=%s, area=%s, month=%s, region=%s/%s/%s(from_q=%s), soil_found=%s",
                result.intent, result.goal, result.area, result.month,
                result.region.province, result.region.city, result.region.county,
                result.region_from_question, result.soil.found)

    if result.intent == "recommend":
        # ① 作物推荐（如有月份则按季节筛选）
        filtered = filter_crops(db, result.soil, result.region, result.seasons or None)
        scored = score_crops(filtered, result.goal, result.area)
        result.candidates = scored[:8]  # 给 LLM 前8个，让它选Top3

    elif result.intent == "plan":
        # ② 种植方案
        result.specified_crop = extract_specified_crop(question, db)
        if result.specified_crop:
            result.suitability = check_crop_suitability(
                db, result.specified_crop, result.soil, result.region
            )

    elif result.intent == "rotation":
        # ③ 轮作推荐
        filtered = filter_crops(db, result.soil, result.region)
        # 按播种季节分组
        by_season: dict[str, list[CropSuitability]] = {}
        for crop in filtered:
            seasons = crop.sow_seasons or ""
            for season in ["春季", "夏季", "秋季", "冬季"]:
                if season in seasons:
                    by_season.setdefault(season, []).append(crop)
        result.rotation_by_season = by_season

    return result


__all__ = [
    "RegionInfo",
    "SoilInfo",
    "CropCandidate",
    "SuitabilityResult",
    "RuleEngineResult",
    "resolve_region",
    "resolve_soil",
    "filter_crops",
    "score_crops",
    "check_crop_suitability",
    "detect_intent",
    "detect_goal",
    "extract_area_from_question",
    "get_user_area",
    "extract_specified_crop",
    "extract_region_from_question",
    "extract_month_from_question",
    "month_to_seasons",
    "run_rule_engine",
]
