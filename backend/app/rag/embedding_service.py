"""Embedding service backed by a local bge-m3 model."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from app.core.config import settings


class EmbeddingError(RuntimeError):
    pass


class BgeM3EmbeddingService:
    def __init__(self) -> None:
        self._model = None
        self._lock = Lock()

    def _model_path(self) -> str:
        path = settings.BGE_M3_MODEL_PATH.strip()
        if not path:
            return "BAAI/bge-m3"
        local_path = Path(path)
        if local_path.exists():
            return str(local_path.resolve())
        return "BAAI/bge-m3"

    def _load_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as error:
                raise EmbeddingError("未安装 FlagEmbedding，请先安装 bge-m3 向量化依赖") from error

            # device 默认按 CUDA 可用性自动选择，可用 BGE_M3_DEVICE 覆盖。
            # 传 devices=[device]（复数参数）强制单设备路径，避免 FlagEmbedding
            # 在 GPU 不可用时误走多进程池导致 ZeroDivisionError。
            # 批量导入时设 CUDA_VISIBLE_DEVICES='' 强制 CPU，避免 GPU 竞争崩溃。
            device = settings.BGE_M3_DEVICE.strip().lower()
            if not device or device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            use_fp16 = device == "cuda"  # CPU 不支持 fp16
            self._model = BGEM3FlagModel(
                self._model_path(), use_fp16=use_fp16, devices=[device]
            )
            return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        clean_texts = [text.strip() for text in texts if text and text.strip()]
        if not clean_texts:
            return []
        model = self._load_model()
        result = model.encode(
            clean_texts,
            batch_size=settings.BGE_M3_BATCH_SIZE,
            max_length=settings.BGE_M3_MAX_LENGTH,
        )
        dense_vectors = result.get("dense_vecs") if isinstance(result, dict) else result
        return [list(map(float, vector)) for vector in dense_vectors]

    def embed_text(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        if not vectors:
            raise EmbeddingError("向量化文本不能为空")
        return vectors[0]


embedding_service = BgeM3EmbeddingService()
