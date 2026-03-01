"""
core/embedder.py
────────────────
LangChain embedding model factories.
Models kept: multilingual-focused (Mongolian + English) + one fast English fallback.
Provider: HuggingFace (local) or Ollama (local server).
"""


# ── Embedding models ──────────────────────────────────────────────
# Trimmed to models that work well for Mongolian + English.
# English-only models (MiniLM-L12, mpnet, bge-small-en) removed.

HUGGINGFACE_MODELS = {
    "paraphrase-multilingual-MiniLM-L12-v2": {
        "size":  "~470 MB",
        "dims":  384,
        "langs": "50+ languages incl. Mongolian",
        "note":  "⭐ Recommended — great Mongolian + English balance",
    },
    "intfloat/multilingual-e5-small": {
        "size":  "~470 MB",
        "dims":  384,
        "langs": "100 languages",
        "note":  "Strong multilingual retrieval benchmarks",
    },
    "intfloat/multilingual-e5-base": {
        "size":  "~1.1 GB",
        "dims":  768,
        "langs": "100 languages",
        "note":  "Best quality · larger · 768-dim",
    },
    "all-MiniLM-L6-v2": {
        "size":  "~90 MB",
        "dims":  384,
        "langs": "English only",
        "note":  "Fast English fallback — not ideal for Mongolian",
    },
}

OLLAMA_EMBED_MODELS = [
    "nomic-embed-text",
    "mxbai-embed-large",
]

DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def load_embeddings(
    provider:   str = "huggingface",
    model_name: str = DEFAULT_EMBED_MODEL,
    ollama_url: str = "http://localhost:11434",
    device:     str = "cpu",
    log_fn=None,
):
    """
    Load and return a LangChain Embeddings object.

    Args:
        provider:   'huggingface' | 'ollama'
        model_name: model identifier
        ollama_url: Ollama server base URL
        device:     'cpu' | 'cuda' | 'mps'
        log_fn:     callable(str) for progress messages
    """
    def _log(msg):
        if log_fn: log_fn(msg)

    if provider == "huggingface":
        info = HUGGINGFACE_MODELS.get(model_name, {})
        _log("📦  Loading HuggingFace embeddings…")
        _log(f"     Model : {model_name}")
        _log(f"     Size  : {info.get('size', 'unknown')}")
        _log(f"     Dims  : {info.get('dims', '?')}")
        _log(f"     Langs : {info.get('langs', '?')}")
        _log(f"     Device: {device}")
        _log("⬇️   Downloading from HuggingFace Hub (cached after first run)…")

        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
        _log("✅  Embeddings ready.")
        return embeddings

    elif provider == "ollama":
        _log("🦙  Connecting to Ollama embeddings…")
        _log(f"     URL  : {ollama_url}")
        _log(f"     Model: {model_name}")
        from langchain_community.embeddings import OllamaEmbeddings
        embeddings = OllamaEmbeddings(base_url=ollama_url, model=model_name)
        _log("✅  Ollama embeddings ready.")
        return embeddings

    raise ValueError(f"Unknown embedding provider: {provider!r}")