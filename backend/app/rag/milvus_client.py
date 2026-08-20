"""Milvus collection helpers for pest knowledge retrieval.

使用 pymilvus 3.x 推荐的 MilvusClient API（替代不稳定的 ORM 风格 Collection API），
避免 insert/search/load 时触发 ACCESS_VIOLATION 崩溃导致集合数据损坏。
"""

from __future__ import annotations

from app.core.config import settings


class MilvusError(RuntimeError):
    pass


_client = None
_loaded_collections: set[str] = set()


def _get_client():
    """单例 MilvusClient，懒加载。"""
    global _client
    if _client is not None:
        return _client
    try:
        from pymilvus import MilvusClient
    except ImportError as error:
        raise MilvusError("未安装 pymilvus，请先安装 Milvus Python 依赖") from error
    _client = MilvusClient(uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    return _client


def _ensure_loaded(name: str) -> None:
    """确保集合已加载到内存（幂等，避免每次 search 重复加载）。"""
    if name in _loaded_collections:
        return
    client = _get_client()
    client.load_collection(collection_name=name)
    _loaded_collections.add(name)


def _collection_name() -> str:
    return settings.MILVUS_COLLECTION_PEST


def create_pest_collection() -> None:
    """创建病虫害向量集合并建立 HNSW 索引。"""
    from pymilvus import DataType, MilvusClient

    client = _get_client()
    name = _collection_name()

    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("knowledge_id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM)
    schema.add_field("crop_name", DataType.VARCHAR, max_length=80)
    schema.add_field("pest_name", DataType.VARCHAR, max_length=120)
    schema.add_field("category", DataType.VARCHAR, max_length=20)
    client.create_collection(collection_name=name, schema=schema)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="HNSW",
        metric_type="COSINE",
        params={"M": 16, "efConstruction": 200},
    )
    client.create_index(collection_name=name, index_params=index_params)


def get_pest_collection(create: bool = False, load: bool = True):
    """确保集合存在，返回集合名。保留签名兼容旧调用。"""
    client = _get_client()
    name = _collection_name()
    if not client.has_collection(collection_name=name):
        if not create:
            raise MilvusError(f"Milvus 集合 {name} 不存在，请先导入病虫害知识库")
        create_pest_collection()
    if load:
        _ensure_loaded(name)
    return name


def upsert_pest_vectors(rows: list[dict], *, flush: bool = True) -> None:
    if not rows:
        return
    name = get_pest_collection(create=True, load=False)
    _get_client().upsert(collection_name=name, data=rows)
    if flush:
        flush_pest_vectors()


def insert_pest_vectors(rows: list[dict], *, flush: bool = True) -> None:
    """Insert a batch and flush to sealed segment (persistent on disk).

    Milvus v2.6.16 稳定版：flush 后数据落盘到 sealed segment，重启不丢失，
    bloom filter 正常持久化、集合可正常加载。无需像 v3.0-beta 那样绕过 flush。
    """
    if not rows:
        return
    name = get_pest_collection(create=True, load=True)
    _get_client().insert(collection_name=name, data=rows)
    if flush:
        flush_pest_vectors()


def drop_pest_collection() -> None:
    """Drop only the Milvus vector collection; MySQL knowledge stays intact."""
    client = _get_client()
    name = _collection_name()
    if client.has_collection(collection_name=name):
        client.drop_collection(collection_name=name)
    _loaded_collections.discard(name)


def list_pest_knowledge_ids() -> set[int]:
    """返回集合中已存在的 knowledge_id（用于断点续传，避免重复导入）。"""
    client = _get_client()
    name = _collection_name()
    if not client.has_collection(collection_name=name):
        return set()
    _ensure_loaded(name)
    res = client.query(
        collection_name=name,
        filter="",
        output_fields=["knowledge_id"],
        limit=16384,
    )
    return {int(r["knowledge_id"]) for r in res}


def flush_pest_vectors() -> None:
    """Flush inserts to sealed segment, persisting data to disk.

    Milvus v2.6.16 稳定版：flush 正常落盘，重启后数据完整保留。
    """
    _get_client().flush(collection_name=_collection_name())


def search_pest_vectors(vector: list[float], top_k: int | None = None) -> list[dict]:
    name = get_pest_collection(create=False)
    results = _get_client().search(
        collection_name=name,
        data=[vector],
        anns_field="vector",
        limit=top_k or settings.PEST_RAG_TOP_K,
        output_fields=["knowledge_id", "crop_name", "pest_name", "category"],
        search_params={"metric_type": "COSINE", "params": {"ef": 64}},
    )
    matches: list[dict] = []
    for hit in results[0]:
        entity = hit.get("entity", {}) or {}
        matches.append({
            "knowledge_id": int(entity.get("knowledge_id", 0)),
            "score": float(hit.get("distance", 0.0)),
            "crop_name": entity.get("crop_name", ""),
            "pest_name": entity.get("pest_name", ""),
            "category": entity.get("category", ""),
        })
    return matches
