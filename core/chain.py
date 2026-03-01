"""
core/chain.py
─────────────
LCEL RAG chain + background thread worker.
Compatible with LangChain v0.2+ / v0.3+. No deprecated imports.
"""
import time
import concurrent.futures

LLM_MODELS = {
    "llama3.2:3b": {
        "label": "Llama 3.2  3B  ⭐",
        "note":  "Fast · good Mongolian + English",
        "size":  "~2 GB",
    },
    "lfm2.5-thinking": {
        "label": "LFM 2.5 Thinking  ⚡",
        "note":  "Reasoning model · fast · efficient",
        "size":  "~2 GB",
    },
    "qwen2.5:3b": {
        "label": "Qwen 2.5  3B",
        "note":  "Strong Mongolian / Cyrillic quality",
        "size":  "~2 GB",
    },
    "llama3.2:1b": {
        "label": "Llama 3.2  1B",
        "note":  "Lightest · CPU-only friendly",
        "size":  "~1 GB",
    },
    "tinyllama:latest": {
        "label": "TinyLlama  1.1B",
        "note":  "Very small · fastest response",
        "size":  "~637 MB",
    },
    "qwen2.5:7b": {
        "label": "Qwen 2.5  7B",
        "note":  "Best multilingual quality",
        "size":  "~5 GB",
    },
}

DEFAULT_LLM = "lfm2.5-thinking"

_LANG_HINTS = {
    "mongolian": "IMPORTANT: Answer in Mongolian (Монгол хэлээр хариул).",
    "english":   "IMPORTANT: Answer in English.",
    "auto":      "Answer in the same language as the context.",
}

# ── Module-level thread pool ──────────────────────────────────────
_executor   = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_ask_jobs:  dict[str, concurrent.futures.Future] = {}
_ask_logs:  dict[str, list[str]] = {}


def build_llm(model_name=DEFAULT_LLM, ollama_url="http://localhost:11434",
              temperature=0.1):
    from langchain_ollama import OllamaLLM
    return OllamaLLM(model=model_name, base_url=ollama_url,
                     temperature=temperature)


def run_rag(vectorstore, llm, question, top_k=5, language="auto"):
    """
    LCEL RAG: retrieve → format → prompt → LLM → parse.
    No deprecated langchain.chains / langchain.prompts imports.
    """
    from langchain_core.prompts        import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    retriever   = vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": top_k}
    )
    source_docs = retriever.invoke(question)

    context = "\n\n---\n\n".join(
        f"[Page {d.metadata.get('page','?')}]\n{d.page_content}"
        for d in source_docs
    )

    lang_hint = _LANG_HINTS.get(language, _LANG_HINTS["auto"])
    template  = (
        "You are a helpful assistant. Answer using ONLY the context below.\n"
        f"{lang_hint}\n"
        "If the answer is not in the context, say so — do not invent facts.\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}\n\nAnswer:"
    )
    prompt = PromptTemplate(template=template,
                            input_variables=["context", "question"])
    chain  = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    sources = [
        {
            "text": d.page_content,
            "page": d.metadata.get("page", "?"),
            "pdf":  d.metadata.get("pdf_name", d.metadata.get("source", "?")),
        }
        for d in source_docs
    ]
    return {"answer": answer.strip(), "sources": sources}


# ── Background worker ─────────────────────────────────────────────

def _worker(job_id, vectorstore, model_name, ollama_url, temperature,
            question, top_k, language):
    _ask_logs[job_id] = []
    def log(msg): _ask_logs[job_id].append(msg)
    try:
        log(f"🦙  Loading {model_name}…")
        llm = build_llm(model_name, ollama_url, temperature)
        log("🔍  Retrieving relevant chunks…")
        result = run_rag(vectorstore, llm, question, top_k, language)
        log(f"✅  Done — {len(result['sources'])} chunks used.")
        return result
    except Exception as e:
        log(f"❌  {e}")
        raise


def submit_ask(vectorstore, model_name, ollama_url, temperature,
               question, top_k, language) -> str:
    import uuid
    job_id = str(uuid.uuid4())
    _ask_logs[job_id] = ["⏳  Queued…"]
    future = _executor.submit(
        _worker, job_id, vectorstore, model_name, ollama_url,
        temperature, question, top_k, language
    )
    _ask_jobs[job_id] = future
    return job_id


def poll_ask(job_id: str):
    """Returns ('running', logs) | ('done', result) | ('error', logs)"""
    future = _ask_jobs.get(job_id)
    logs   = list(_ask_logs.get(job_id, []))
    if future is None:
        return "error", ["Job not found."]
    if not future.done():
        return "running", logs
    try:
        result = future.result()
        _ask_jobs.pop(job_id, None)
        return "done", result
    except Exception as exc:
        _ask_jobs.pop(job_id, None)
        return "error", logs + [f"❌ {exc}"]


def cancel_ask(job_id: str):
    fut = _ask_jobs.pop(job_id, None)
    if fut: fut.cancel()
    _ask_logs.pop(job_id, None)