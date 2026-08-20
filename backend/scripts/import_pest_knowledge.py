"""Import pest/disease Excel files into MySQL and Milvus.

Example:
    uv run python scripts/import_pest_knowledge.py --source D:/plant/insect
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import Base, SessionLocal, engine
from app.models import PestKnowledge
from app.rag.embedding_service import embedding_service
from app.rag.milvus_client import drop_pest_collection, flush_pest_vectors, insert_pest_vectors
from app.rag.pest_retriever import compose_pest_vector_text


COLUMN_MAP = {
    "中文名称": "pest_name",
    "简介": "intro",
    "危害症状": "symptoms",
    "发生因素": "cause",
    "生活习性": "habit",
    "形态特征": "morphology",
    "防治方法": "control_method",
}

EXCEL_SUFFIXES = {".xls", ".xlsx"}

IMPORT_CATEGORIES = ("病害", "虫害", "检疫性物种")
CROP_CATEGORIES = {"病害", "虫害"}


def infer_crop_name(path: Path) -> str:
    name = path.stem
    for suffix in ("病虫害", "虫害", "病害"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def clean(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def deduplicate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            row["crop_name"],
            row["pest_name"],
            row["category"],
            row["source_file"],
        )
        unique.setdefault(key, row)
    return list(unique.values())


def read_knowledge_rows(path: Path, category: str) -> list[dict[str, str]]:
    # 病害和虫害文件通常按“作物+类别”命名；检疫性物种和入侵动植物不强行推断作物名。
    crop_name = infer_crop_name(path) if category in CROP_CATEGORIES else ""
    rows: list[dict[str, str]] = []
    workbook = pd.ExcelFile(path)
    for sheet in workbook.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        for _, row in df.iterrows():
            data = {field: clean(row.get(column)) for column, field in COLUMN_MAP.items()}
            pest_name = data.pop("pest_name", "")
            if not pest_name:
                continue
            rows.append({
                "crop_name": crop_name,
                "pest_name": pest_name,
                "category": category,
                "source_file": path.name,
                **data,
            })
    return rows


def upsert_mysql(rows: list[dict[str, str]]) -> list[PestKnowledge]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    saved: list[PestKnowledge] = []
    try:
        for row in rows:
            knowledge = db.query(PestKnowledge).filter(
                PestKnowledge.crop_name == row["crop_name"],
                PestKnowledge.pest_name == row["pest_name"],
                PestKnowledge.category == row["category"],
                PestKnowledge.source_file == row["source_file"],
            ).first()
            if not knowledge:
                knowledge = PestKnowledge(**row, vector_text="")
                db.add(knowledge)
            else:
                for key, value in row.items():
                    setattr(knowledge, key, value)
            knowledge.vector_text = compose_pest_vector_text(knowledge)
            saved.append(knowledge)
        db.commit()
        for item in saved:
            db.refresh(item)
        return saved
    finally:
        db.close()


def sync_milvus(items: list[PestKnowledge], batch_size: int) -> None:
    unique_items: dict[int, PestKnowledge] = {}
    for item in items:
        if item.id is not None:
            unique_items[item.id] = item
    items = list(unique_items.values())
    total = len(items)
    for start in range(0, total, batch_size):
        batch = items[start : start + batch_size]
        vectors = embedding_service.embed_texts([item.vector_text for item in batch])
        rows = []
        for item, vector in zip(batch, vectors, strict=True):
            rows.append({
                "knowledge_id": item.id,
                "vector": vector,
                "crop_name": item.crop_name,
                "pest_name": item.pest_name,
                "category": item.category,
            })
        insert_pest_vectors(rows, flush=False)
        print(f"Milvus 已写入 {min(start + len(batch), total)}/{total} 条", flush=True)
    if total:
        flush_pest_vectors()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import pest/disease Excel knowledge.")
    parser.add_argument("--source", required=True, help="Excel file or directory path")
    parser.add_argument(
        "--category",
        required=True,
        choices=IMPORT_CATEGORIES,
        help="Category applied to every Excel row in the source path",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit imported rows for quick verification")
    parser.add_argument("--batch-size", type=int, default=16, help="Embedding and Milvus write batch size")
    parser.add_argument("--skip-milvus", action="store_true", help="Only import MySQL, skip vector sync")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop and recreate the Milvus collection before importing; MySQL data is kept",
    )
    args = parser.parse_args()

    if args.rebuild and args.skip_milvus:
        raise SystemExit("--rebuild 不能与 --skip-milvus 同时使用")
    if args.rebuild:
        print("正在重建 Milvus 集合（不会删除 MySQL 数据）...", flush=True)
        drop_pest_collection()

    source = Path(args.source)
    files = (
        [source]
        if source.is_file()
        else sorted(
            file
            for file in source.iterdir()
            if file.is_file()
            and file.suffix.lower() in EXCEL_SUFFIXES
            and not file.name.startswith("~$")
        )
    )
    if not files:
        raise SystemExit(f"未找到 Excel 文件：{source}")

    rows: list[dict[str, str]] = []
    for file in files:
        rows.extend(read_knowledge_rows(file, args.category))
    if args.limit > 0:
        rows = rows[: args.limit]
    raw_count = len(rows)
    rows = deduplicate_rows(rows)
    if len(rows) != raw_count:
        print(f"已跳过重复 Excel 行：{raw_count - len(rows)} 条", flush=True)
    items = upsert_mysql(rows)
    if not args.skip_milvus:
        sync_milvus(items, max(1, args.batch_size))
    print(f"导入完成：{len(items)} 条，文件数：{len(files)}")


if __name__ == "__main__":
    main()
