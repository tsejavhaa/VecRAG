"""
core/vectorstore.py
────────────────────
LangChain Chroma vector store: build, persist, search.
Background embed worker with live logging.
"""

import concurrent.futures
from typing import Optional

# Module-level thread pool and job tracking
_executor  = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_job_store: dict[str, concurrent.futures.Future] = {}
_job_logs:  dict[str, list[str]] = {}


def get_logs(job_id: str) -> list[str]:
    return list(_job_logs.get(job_id, []))


def cancel_job(job_id: str) -> None:
    fut = _job_store.pop(job_id, None)
    if fut:
        fut.cancel()
    _job_logs.pop(job_id, None)


# ── Build / load vector store ─────────────────────────────────────

def build_vectorstore(
    documents: list,
    embeddings,
    collection_name: str,
    persist_dir:     str,
    batch_size:      int = 64,
    log_fn=None,
):
    """
    Embed documents and persist to Chroma via LangChain.

    Args:
        documents:       list of LangChain Document objects (already split)
        embeddings:      LangChain Embeddings instance
        collection_name: Chroma collection name
        persist_dir:     directory for ChromaDB persistence
        batch_size:      documents per embed batch
        log_fn:          callable(str) for progress messages

    Returns:
        LangChain Chroma vectorstore instance
    """
    def _log(msg):
        if log_fn: log_fn(msg)

    from langchain_chroma import Chroma
    import chromadb

    _log(f"💾  Opening ChromaDB at '{persist_dir}'…")
    client = chromadb.PersistentClient(path=persist_dir)

    # Drop existing collection for a clean re-embed
    _log(f"🗑️   Clearing collection '{collection_name}'…")
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    total = len(documents)
    _log(f"🔢  Embedding {total} chunks in batches of {batch_size}…")

    # Embed in batches so progress can be logged
    vectorstore = None
    for i in range(0, total, batch_size):
        batch = documents[i: i + batch_size]
        pct   = int(min(i + batch_size, total) / total * 100)

        if vectorstore is None:
            # First batch — create the collection
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=collection_name,
                client=client,
            )
        else:
            # Subsequent batches — add to existing store
            vectorstore.add_documents(batch)

        _log(f"     [{pct:3d}%]  {min(i + batch_size, total)}/{total} chunks stored")

    _log(f"✅  All {total} chunks embedded and persisted.")
    return vectorstore


def load_vectorstore(
    embeddings,
    collection_name: str,
    persist_dir:     str,
):
    """Load an existing persisted Chroma collection."""
    from langchain_chroma import Chroma
    import chromadb
    client = chromadb.PersistentClient(path=persist_dir)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        client=client,
    )


# ── Search ────────────────────────────────────────────────────────

def search(
    vectorstore,
    query:       str,
    search_type: str  = "similarity",
    top_k:       int  = 5,
    filter_meta: Optional[dict] = None,
) -> list[dict]:
    """
    Run a search against the vector store.

    search_type: 'similarity' | 'mmr' | 'similarity_score_threshold'
    Returns list of {text, metadata, score} dicts.
    """
    kwargs = {"k": top_k}
    if filter_meta:
        kwargs["filter"] = filter_meta

    if search_type == "similarity":
        results = vectorstore.similarity_search_with_relevance_scores(
            query, **kwargs
        )
        return [
            {"text": doc.page_content, "metadata": doc.metadata, "score": round(score, 4)}
            for doc, score in results
        ]

    elif search_type == "mmr":
        # Maximal Marginal Relevance — diverse results
        docs = vectorstore.max_marginal_relevance_search(
            query, k=top_k, fetch_k=top_k * 3,
            **({k: v for k, v in kwargs.items() if k != "k"})
        )
        return [
            {"text": doc.page_content, "metadata": doc.metadata, "score": None}
            for doc in docs
        ]

    elif search_type == "similarity_score_threshold":
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.3, "k": top_k},
        )
        docs = retriever.get_relevant_documents(query)
        return [
            {"text": doc.page_content, "metadata": doc.metadata, "score": None}
            for doc in docs
        ]

    # Fallback
    docs = vectorstore.similarity_search(query, **kwargs)
    return [
        {"text": doc.page_content, "metadata": doc.metadata, "score": None}
        for doc in docs
    ]


# ── Background worker ─────────────────────────────────────────────

def _embed_worker(
    job_id:          str,
    pdf_bytes:       bytes,
    pdf_name:        str,
    splitter_method: str,
    chunk_size:      int,
    chunk_overlap:   int,
    embed_provider:  str,
    embed_model:     str,
    ollama_url:      str,
    device:          str,
    collection_name: str,
    persist_dir:     str,
) -> tuple:
    """Runs on ThreadPoolExecutor worker. Returns (documents, vectorstore, count)."""
    _job_logs[job_id] = []

    def log(msg: str):
        _job_logs[job_id].append(msg)

    try:
        from core.loader   import load_documents
        from core.splitter import build_splitter, split_documents
        from core.embedder import load_embeddings

        # 1. Load
        log("─── Loading PDF ─────────────────────────")
        docs = load_documents(pdf_bytes, pdf_name, log_fn=log)
        log(f"     {len(docs)} pages loaded")

        # 2. Embeddings (must come before splitting for semantic chunker)
        log("")
        log("─── Loading embedding model ─────────────")
        embeddings = load_embeddings(
            provider=embed_provider,
            model_name=embed_model,
            ollama_url=ollama_url,
            device=device,
            log_fn=log,
        )

        # 3. Split — pass embeddings so SemanticChunker can use them
        log("")
        log("─── Splitting text ──────────────────────")
        log(f"     Method: {splitter_method} | size={chunk_size} | overlap={chunk_overlap}")
        if splitter_method == "semantic":
            log("     SemanticChunker: detecting topic boundaries via embeddings…")
        splitter = build_splitter(splitter_method, chunk_size, chunk_overlap,
                                  embeddings=embeddings)
        chunks   = split_documents(docs, splitter)
        log(f"✅  {len(chunks)} chunks created")

        # 4. Vector store
        log("")
        log("─── Building vector store ───────────────")
        vs = build_vectorstore(
            documents=chunks,
            embeddings=embeddings,
            collection_name=collection_name,
            persist_dir=persist_dir,
            log_fn=log,
        )

        log("")
        log(f"🎉  Done! {len(chunks)} chunks in '{collection_name}'.")
        return chunks, vs, len(chunks)

    except Exception as exc:
        log(f"❌  Error: {exc}")
        raise


def submit_job(
    pdf_bytes:       bytes,
    pdf_name:        str,
    splitter_method: str,
    chunk_size:      int,
    chunk_overlap:   int,
    embed_provider:  str,
    embed_model:     str,
    ollama_url:      str,
    device:          str,
    collection_name: str,
    persist_dir:     str,
) -> str:
    import uuid
    job_id = str(uuid.uuid4())
    _job_logs[job_id] = ["⏳  Job queued…"]
    future = _executor.submit(
        _embed_worker,
        job_id, pdf_bytes, pdf_name,
        splitter_method, chunk_size, chunk_overlap,
        embed_provider, embed_model, ollama_url, device,
        collection_name, persist_dir,
    )
    _job_store[job_id] = future
    return job_id


def poll_job(job_id: str):
    """Returns ('running', logs) | ('done', result) | ('error', logs)"""
    future = _job_store.get(job_id)
    logs   = get_logs(job_id)

    if future is None:
        return "error", ["Job not found."]
    if not future.done():
        return "running", logs
    try:
        result = future.result()
        _job_store.pop(job_id, None)
        return "done", result
    except Exception as exc:
        _job_store.pop(job_id, None)
        return "error", logs + [f"❌ {exc}"]


# ── Background search worker ──────────────────────────────────────
import uuid as _uuid

_search_store: dict[str, concurrent.futures.Future] = {}
_search_logs:  dict[str, list[str]] = {}


def _search_worker(job_id, vectorstore, query, search_type, top_k, filter_meta):
    _search_logs[job_id] = []
    def log(msg): _search_logs[job_id].append(msg)
    import time
    t0 = time.time()
    try:
        log(f"🔍  Query: \"{query[:80]}{'…' if len(query)>80 else ''}\"")
        log(f"     Mode  : {search_type}  |  k={top_k}")
        if filter_meta:
            log(f"     Filter: {filter_meta}")
        log("")
        log("─── Embedding query ─────────────────────")
        log("     Loading query through embedding model…")

        kwargs = {"k": top_k}
        if filter_meta:
            kwargs["filter"] = filter_meta

        if search_type == "similarity":
            log("     Running cosine similarity search…")
            results = vectorstore.similarity_search_with_relevance_scores(query, **kwargs)
            out = [
                {"text": doc.page_content, "metadata": doc.metadata, "score": round(score, 4)}
                for doc, score in results
            ]

        elif search_type == "mmr":
            log("     Running MMR (Maximal Marginal Relevance) search…")
            log(f"     Fetching {top_k*3} candidates, selecting {top_k} diverse results…")
            docs = vectorstore.max_marginal_relevance_search(
                query, k=top_k, fetch_k=top_k * 3,
                **({k: v for k, v in kwargs.items() if k != "k"})
            )
            out = [
                {"text": doc.page_content, "metadata": doc.metadata, "score": None}
                for doc in docs
            ]

        elif search_type == "similarity_score_threshold":
            log("     Running score-threshold search (min score: 0.30)…")
            retriever = vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"score_threshold": 0.3, "k": top_k},
            )
            docs = retriever.invoke(query)
            out = [
                {"text": doc.page_content, "metadata": doc.metadata, "score": None}
                for doc in docs
            ]

        else:
            log("     Running similarity search (fallback)…")
            docs = vectorstore.similarity_search(query, **kwargs)
            out = [
                {"text": doc.page_content, "metadata": doc.metadata, "score": None}
                for doc in docs
            ]

        elapsed = time.time() - t0
        if out:
            scores = [r["score"] for r in out if r["score"] is not None]
            avg    = f"{int(sum(scores)/len(scores)*100)}%" if scores else "n/a"
            log("")
            log(f"✅  {len(out)} results in {elapsed:.2f}s  |  avg score: {avg}")
        else:
            log("")
            log(f"⚠  No results matched in {elapsed:.2f}s")
            log("     Try a broader query, lower threshold, or switch mode.")
        return out

    except Exception as exc:
        log(f"❌  Search error: {exc}")
        raise


def submit_search(vectorstore, query, search_type, top_k, filter_meta) -> str:
    job_id = str(_uuid.uuid4())
    _search_logs[job_id] = ["⏳  Queued…"]
    _search_store[job_id] = _executor.submit(
        _search_worker, job_id, vectorstore, query, search_type, top_k, filter_meta
    )
    return job_id


def poll_search(job_id: str):
    """Returns ('running', logs) | ('done', results) | ('error', logs)"""
    future = _search_store.get(job_id)
    logs   = list(_search_logs.get(job_id, []))
    if future is None:
        return "error", ["Job not found."]
    if not future.done():
        return "running", logs
    try:
        result = future.result()
        _search_store.pop(job_id, None)
        return "done", result
    except Exception as exc:
        _search_store.pop(job_id, None)
        return "error", logs + [f"❌ {exc}"]


def cancel_search(job_id: str):
    fut = _search_store.pop(job_id, None)
    if fut: fut.cancel()
    _search_logs.pop(job_id, None)


def get_search_logs(job_id: str) -> list[str]:
    return list(_search_logs.get(job_id, []))