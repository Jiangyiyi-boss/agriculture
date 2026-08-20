"""种植计划数据导入脚本

从本地数据文件导入到 MySQL：
  - data/soil/作物适宜性数据.csv  → crop_suitability 表
  - data/soil/土壤数据汇总表.xlsx → soil_data 表
  - data/soil/行政区划映射表.xlsx  → admin_district 表

用法：
  cd d:\\agriculture\\backend
  uv run python scripts/import_planting_data.py
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

import pandas as pd

# 确保能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.models import CropSuitability, SoilData, AdminDistrict


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------

def parse_range(text: str) -> tuple[float | None, float | None]:
    """解析 "6.0-7.5" / "20-30°C" / "120-150" 等范围字符串，返回 (min, max)。"""
    if not text or not isinstance(text, str):
        return None, None
    # 提取所有数字（含小数）
    numbers = re.findall(r"(\d+\.?\d*)", str(text))
    if len(numbers) >= 2:
        return float(numbers[0]), float(numbers[1])
    if len(numbers) == 1:
        val = float(numbers[0])
        return val, val
    return None, None


def normalize_dash(text: str | None) -> str | None:
    """把 Unicode 连字符（‑ U+2011、– U+2013、— U+2014）统一为 ASCII '-'。

    新增的 CSV 数据可能混用不同类型的连字符，统一后保证字符串字段一致性。
    """
    if text is None:
        return None
    return text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")


def parse_yield(text: str) -> tuple[float | None, float | None]:
    """解析亩产参考 "500-600公斤" / "2000-3000公斤(鲜薯)" → (min, max) kg。"""
    return parse_range(text)


def parse_cycle(text: str) -> tuple[int | None, int | None, bool]:
    """解析生长周期 "120-150" / "多年生" / "多年生(12-15个月)" → (min, max, is_perennial)。"""
    if not text or not isinstance(text, str):
        return None, None, False
    is_perennial = "多年" in str(text) or "年生" in str(text)
    numbers = re.findall(r"(\d+\.?\d*)", str(text))
    if len(numbers) >= 2:
        return int(float(numbers[0])), int(float(numbers[1])), is_perennial
    if len(numbers) == 1:
        val = int(float(numbers[0]))
        return val, val, is_perennial
    return None, None, is_perennial


# ---------------------------------------------------------------------------
# 导入：作物适宜性数据 CSV
# ---------------------------------------------------------------------------

def import_crop_suitability(db) -> int:
    csv_path = Path("d:/agriculture/data/soil/作物适宜性数据.csv")
    if not csv_path.exists():
        print(f"[SKIP] 文件不存在: {csv_path}")
        return 0

    # 先清空旧数据（重复导入幂等）
    deleted = db.query(CropSuitability).delete()
    if deleted:
        print(f"[CLEAN] 清空 crop_suitability 旧数据 {deleted} 条")

    count = 0
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 统一连字符：把 Unicode ‑/–/— 替换为 ASCII -
            norm = {k: normalize_dash(v) if isinstance(v, str) else v for k, v in row.items()}

            ph_min, ph_max = parse_range(norm.get("适宜pH范围", ""))
            temp_min, temp_max = parse_range(norm.get("适宜温度范围", ""))
            cycle_min, cycle_max, is_perennial = parse_cycle(norm.get("生长周期(天)", ""))
            yield_min, yield_max = parse_yield(norm.get("亩产参考", ""))

            record = CropSuitability(
                crop_name=norm.get("作物名称", "").strip(),
                category=norm.get("类别", "").strip(),
                varieties=norm.get("代表品种", "").strip(),
                temp_range=norm.get("适宜温度范围", "").strip(),
                temp_min=temp_min,
                temp_max=temp_max,
                soil_types=norm.get("适宜土壤类型", "").strip(),
                ph_range=norm.get("适宜pH范围", "").strip(),
                ph_min=ph_min,
                ph_max=ph_max,
                growth_cycle=norm.get("生长周期(天)", "").strip(),
                cycle_min=cycle_min,
                cycle_max=cycle_max,
                is_perennial=is_perennial,
                water_demand=norm.get("需水量", "").strip(),
                light_requirement=norm.get("光照要求", "").strip(),
                main_diseases=norm.get("主要病害", "").strip(),
                sow_seasons=norm.get("适宜播种季节", "").strip(),
                cold_resistance=norm.get("耐寒性", "").strip(),
                drought_resistance=norm.get("耐旱性", "").strip(),
                region_fit=norm.get("地域适配", "").strip(),
                yield_ref=norm.get("亩产参考", "").strip(),
                yield_min=yield_min,
                yield_max=yield_max,
            )
            db.add(record)
            count += 1

    db.commit()
    print(f"[OK] crop_suitability 导入 {count} 条")
    return count


# ---------------------------------------------------------------------------
# 导入：土壤数据 Excel
# ---------------------------------------------------------------------------

def import_soil_data(db) -> int:
    xlsx_path = Path("d:/agriculture/data/soil/土壤数据汇总表.xlsx")
    if not xlsx_path.exists():
        print(f"[SKIP] 文件不存在: {xlsx_path}")
        return 0

    deleted = db.query(SoilData).delete()
    if deleted:
        print(f"[CLEAN] 清空 soil_data 旧数据 {deleted} 条")

    df = pd.read_excel(xlsx_path)
    count = 0
    for _, row in df.iterrows():
        province = str(row.get("省名", "")).strip()
        if not province or province == "nan":
            continue
        ph_str = str(row.get("pH值", "")).strip()
        ph_min, ph_max = parse_range(ph_str)
        organic_raw = row.get("有机质(g/kg)", None)
        organic_matter = float(organic_raw) if pd.notna(organic_raw) else None

        record = SoilData(
            province=province,
            city=str(row.get("地级市名", "")).strip() if pd.notna(row.get("地级市名")) else None,
            county=str(row.get("县市名", "")).strip() if pd.notna(row.get("县市名")) else None,
            soil_group=str(row.get("土纲名", "")).strip() if pd.notna(row.get("土纲名")) else None,
            subgroup=str(row.get("亚类名", "")).strip() if pd.notna(row.get("亚类名")) else None,
            soil_species=str(row.get("土种名", "")).strip() if pd.notna(row.get("土种名")) else None,
            texture=str(row.get("质地", "")).strip() if pd.notna(row.get("质地")) else None,
            organic_matter=organic_matter,
            ph_value=ph_str,
            ph_min=ph_min,
            ph_max=ph_max,
        )
        db.add(record)
        count += 1

    db.commit()
    print(f"[OK] soil_data 导入 {count} 条")
    return count


# ---------------------------------------------------------------------------
# 导入：行政区划 Excel
# ---------------------------------------------------------------------------

def import_admin_district(db) -> int:
    xlsx_path = Path("d:/agriculture/data/soil/行政区划映射表.xlsx")
    if not xlsx_path.exists():
        print(f"[SKIP] 文件不存在: {xlsx_path}")
        return 0

    deleted = db.query(AdminDistrict).delete()
    if deleted:
        print(f"[CLEAN] 清空 admin_district 旧数据 {deleted} 条")

    df = pd.read_excel(xlsx_path)
    count = 0
    for _, row in df.iterrows():
        province = str(row.get("省份", "")).strip()
        if not province or province == "nan":
            continue

        record = AdminDistrict(
            province=province,
            city=str(row.get("地级市", "")).strip() if pd.notna(row.get("地级市")) else None,
            county=str(row.get("区县", "")).strip() if pd.notna(row.get("区县")) else None,
            level=str(row.get("级别", "")).strip() if pd.notna(row.get("级别")) else None,
            aliases=str(row.get("别名", "")).strip() if pd.notna(row.get("别名")) else None,
        )
        db.add(record)
        count += 1

    db.commit()
    print(f"[OK] admin_district 导入 {count} 条")
    return count


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("种植计划数据导入脚本")
    print("=" * 60)

    # 确保表存在
    Base.metadata.create_all(bind=engine)
    print("[INFO] 确认数据库表已创建")

    db = SessionLocal()
    try:
        total = 0
        total += import_crop_suitability(db)
        total += import_soil_data(db)
        total += import_admin_district(db)
        print("-" * 60)
        print(f"[DONE] 总计导入 {total} 条记录")
    finally:
        db.close()


if __name__ == "__main__":
    main()
