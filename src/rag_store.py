from __future__ import annotations

import os

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from .spark_store import _TTLCache


class SparkRAGStore:
    SCHEMA_COLLECTION = "spark_schema"
    POLICY_COLLECTION = "spark_policy"

    def __init__(
        self,
        chroma_path: str = ".chroma",
        embed_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434",
        schema_k: int = 6,
        policy_k: int = 4,
    ) -> None:
        self._schema_k = schema_k
        self._policy_k = policy_k
        embeddings = OllamaEmbeddings(
            model=embed_model,
            base_url=ollama_base_url,
        )
        self._schema_vs = Chroma(
            collection_name=self.SCHEMA_COLLECTION,
            embedding_function=embeddings,
            persist_directory=chroma_path,
        )
        self._policy_vs = Chroma(
            collection_name=self.POLICY_COLLECTION,
            embedding_function=embeddings,
            persist_directory=chroma_path,
        )
        rag_ttl = int(os.environ.get("RAG_CACHE_TTL", "3600"))
        self._cache = _TTLCache(ttl=rag_ttl, maxsize=256)

    def schema_collection(self) -> Chroma:
        return self._schema_vs

    def policy_collection(self) -> Chroma:
        return self._policy_vs

    def _retrieve(self, prefix: str, vs, k: int, not_found: str, query: str) -> str:
        key    = f"{prefix}:{hash(query)}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        docs   = vs.similarity_search(query, k=k)
        result = not_found if not docs else "\n\n---\n\n".join(d.page_content for d in docs)
        self._cache.set(key, result)
        return result

    def retrieve_schema(self, query: str) -> str:
        return self._retrieve("schema", self._schema_vs, self._schema_k, "No schema information found.", query)

    def retrieve_policy(self, query: str) -> str:
        return self._retrieve("policy", self._policy_vs, self._policy_k, "No policy information found.", query)
