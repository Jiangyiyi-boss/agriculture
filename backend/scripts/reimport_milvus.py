"""一键重新导入 Milvus 向量数据。

首次部署或更换 Milvus 版本后运行此脚本导入 RAG 知识库：
    python scripts/reimport_milvus.py

数据来源是 MySQL（不会丢失），向量化后写入 Milvus 并 flush 落盘，
重启 Docker / 关机后数据持久保留，无需再次运行。
"""

from __future__ import annotations

import os

# 批量导入强制 CPU：GPU 被大量桌面进程占用时，加载 bge-m3 易触发
# ACCESS_VIOLATION / CUDA OOM 崩溃。CPU 模式稳定，慢但可靠。
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)


def wait_for_milvus(timeout: int = 60) -> bool:
    """等待 Milvus 就绪。"""
    from pymilvus import MilvusClient
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = MilvusClient(uri="http://127.0.0.1:19530")
            c.list_collections()
            return True
        except Exception:
            print("  等待 Milvus 启动...", flush=True)
            time.sleep(3)
    return False


def main() -> None:
    print("=" * 50)
    print("Milvus 向量数据导入（支持断点续传）")
    print("=" * 50)

    if not wait_for_milvus():
        print("❌ Milvus 未就绪，请先启动 Docker Milvus 容器")
        sys.exit(1)
    print("✅ Milvus 已连接\n")

    import gc
    from app.rag.embedding_service import embedding_service
    from app.rag.milvus_client import (
        flush_pest_vectors,
        get_pest_collection,
        insert_pest_vectors,
        list_pest_knowledge_ids,
    )
    from app.rag.pest_retriever import compose_pest_vector_text
    from app.core.database import SessionLocal
    from app.models import PestKnowledge

    print(">>> 1/5 确保集合存在 / 检查已导入数据...")
    get_pest_collection(create=True, load=True)
    existing_ids = list_pest_knowledge_ids()
    print(f"    集合已有 {len(existing_ids)} 条向量\n")

    print(">>> 2/5 加载 bge-m3 模型（CPU 模式）...")
    embedding_service.embed_text("warmup")
    print("    OK\n")

    db = SessionLocal()
    items = db.query(PestKnowledge).all()
    db.close()
    todo = [it for it in items if it.id not in existing_ids]
    total = len(items)
    remain = len(todo)
    print(f">>> 3/5 向量化写入：{remain}/{total} 条待导入（跳过 {total - remain} 条已存在）...")

    if remain == 0:
        print("    全部已存在，无需导入")
    else:
        batch_size = 32
        for start in range(0, remain, batch_size):
            batch = todo[start : start + batch_size]
            texts = [compose_pest_vector_text(item) for item in batch]
            vectors = embedding_service.embed_texts(texts)
            rows = [
                {
                    "knowledge_id": item.id,
                    "vector": vec,
                    "crop_name": item.crop_name,
                    "pest_name": item.pest_name,
                    "category": item.category,
                }
                for item, vec in zip(batch, vectors, strict=True)
            ]
            insert_pest_vectors(rows, flush=False)
            done = len(existing_ids) + min(start + len(batch), remain)
            print(f"    已写入 {done}/{total} 条", flush=True)
            del texts, vectors, rows
            gc.collect()

    print(f"\n>>> 4/5 落盘到磁盘（持久化，重启不丢失）...")
    flush_pest_vectors()
    print("    OK\n")

    print(f">>> 5/5 验证搜索...")
    from app.rag.milvus_client import search_pest_vectors
    vec = embedding_service.embed_text("水稻稻瘟病")
    matches = search_pest_vectors(vec, top_k=3)
    if matches:
        print(f"    ✅ 搜索正常，返回 {len(matches)} 条结果")
        for m in matches:
            print(f"       score={m['score']:.4f} {m['crop_name']} {m['pest_name']}")
    else:
        print("    ⚠️ 搜索返回空，请检查")

    print("\n" + "=" * 50)
    print("✅ 导入完成！RAG 知识库已就绪")
    print("=" * 50)


if __name__ == "__main__":
    main()
