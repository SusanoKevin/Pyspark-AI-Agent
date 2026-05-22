from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter

from .rag_store import SparkRAGStore

logger = logging.getLogger(__name__)

_CHUNK_SIZE    = 800
_CHUNK_OVERLAP = 80


def _doc_id(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _already_indexed(collection, doc_id: str) -> bool:
    result = collection.get(ids=[doc_id])
    return bool(result and result.get("ids"))


def ingest_schemas(
    store: SparkRAGStore,
    spark_store,
    force: bool = False,
) -> int:
    collection = store.schema_collection()
    added = 0

    for table_name in spark_store.get_table_names():
        try:
            columns = spark_store.get_schema_for_table(table_name)
        except Exception as e:
            logger.warning("Schema ingest skipped for %s: %s", table_name, e)
            continue

        if not columns:
            continue

        doc_id = _doc_id(f"spark::{table_name}")
        if not force and _already_indexed(collection, doc_id):
            continue

        lines = [f"Table: {table_name}", "Columns:"]
        for col in columns:
            lines.append(f"  {col['name']:<30} {col['dataType']}")

        doc = Document(
            page_content="\n".join(lines),
            metadata={"source": "schema", "table": table_name},
        )
        collection.add_documents([doc], ids=[doc_id])
        added += 1

    if added:
        logger.info("Schema ingest: added %d table documents", added)
    return added


def ingest_docs(
    store: ExcelsisRAGStore,
    docs_path: str = "docs",
    force: bool = False,
) -> int:
    collection = store.policy_collection()
    root = Path(docs_path)
    if not root.exists():
        logger.warning("Docs path %s does not exist — skipping policy ingest", docs_path)
        return 0

    md_splitter  = MarkdownTextSplitter(chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP)
    txt_splitter = RecursiveCharacterTextSplitter(chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP)
    added = 0

    all_files = sorted(root.glob("**/*.md")) + sorted(root.glob("**/*.pdf"))
    for path in all_files:
        if path.name.startswith("."):
            continue

        try:
            if path.suffix == ".pdf":
                raw_docs = PyPDFLoader(str(path)).load()
                chunks   = txt_splitter.split_documents(raw_docs)
            else:
                raw_docs = TextLoader(str(path), encoding="utf-8").load()
                chunks   = md_splitter.split_documents(raw_docs)
        except Exception as e:
            logger.warning("Could not load %s: %s", path, e)
            continue

        for i, chunk in enumerate(chunks):
            doc_id = _doc_id(f"{path}::{i}")
            if not force and _already_indexed(collection, doc_id):
                continue

            chunk.metadata.update({"source": "policy", "file": path.name, "chunk": i})
            collection.add_documents([chunk], ids=[doc_id])
            added += 1

    if added:
        logger.info("Policy ingest: added %d chunks from %s", added, docs_path)
    return added


def run_ingestion(
    store: SparkRAGStore,
    spark_store,
    docs_path: str = "docs",
) -> None:
    schema_n = ingest_schemas(store, spark_store)
    policy_n = ingest_docs(store, docs_path)
    logger.info("RAG ingestion complete — schemas: %d, policy chunks: %d", schema_n, policy_n)
