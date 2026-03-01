"""
core/splitter.py
────────────────
LangChain text splitter wrappers — 6 strategies.

  recursive   RecursiveCharacterTextSplitter  (default, general-purpose)
  semantic    SemanticChunker                 (meaning-aware, needs embeddings)
  sentence    SentenceTransformersTokenTextSplitter
  paragraph   CharacterTextSplitter on double-newline
  token       TokenTextSplitter               (tiktoken-based)
  markdown    MarkdownHeaderTextSplitter      (for markdown/structured PDFs)
"""

from typing import Optional


SPLITTER_INFO = {
    "recursive": {
        "label": "Recursive Character",
        "tag":   "GENERAL",
        "desc":  (
            "Tries separators in order: paragraph → sentence → word → char. "
            "Best all-round choice for most PDFs."
        ),
        "needs_embeddings": False,
        "has_size_control":  True,
    },
    "semantic": {
        "label": "Semantic  ✦",
        "tag":   "BEST QUALITY",
        "desc":  (
            "Uses an embedding model to detect topic shifts and split at meaning "
            "boundaries. Chunks are coherent units of thought — not arbitrary character "
            "windows. Slower but produces the most meaningful results. "
            "Uses the same embedding model you selected on the left."
        ),
        "needs_embeddings": True,
        "has_size_control":  False,   # SemanticChunker controls its own size
    },
    "sentence": {
        "label": "Sentence Transformer Tokens",
        "tag":   "TOKEN-AWARE",
        "desc":  (
            "Splits using the same tokenizer as the embedding model — guarantees "
            "chunks never exceed the model's context window."
        ),
        "needs_embeddings": False,
        "has_size_control":  True,
    },
    "paragraph": {
        "label": "Paragraph",
        "tag":   "STRUCTURE",
        "desc":  (
            "Splits strictly on double-newlines (paragraph breaks). "
            "Preserves document structure. Good for well-formatted PDFs."
        ),
        "needs_embeddings": False,
        "has_size_control":  True,
    },
    "token": {
        "label": "Token (tiktoken)",
        "tag":   "LLM-READY",
        "desc":  (
            "Splits by GPT-compatible token count via tiktoken. "
            "Ideal when you plan to feed chunks directly to an LLM."
        ),
        "needs_embeddings": False,
        "has_size_control":  True,
    },
    "markdown": {
        "label": "Markdown Header",
        "tag":   "STRUCTURED",
        "desc":  (
            "Splits on Markdown headers (#, ##, ###). "
            "Best for PDFs exported with heading structure or README-style documents."
        ),
        "needs_embeddings": False,
        "has_size_control":  False,   # Markdown splitter is header-driven
    },
}


def build_splitter(
    method:        str            = "recursive",
    chunk_size:    int            = 1000,
    chunk_overlap: int            = 150,
    embeddings                    = None,    # required for "semantic"
    separators:    Optional[list] = None,
):
    """
    Build and return a LangChain text splitter.

    Args:
        method:         one of SPLITTER_INFO keys
        chunk_size:     target characters (or tokens) per chunk
        chunk_overlap:  overlap between consecutive chunks
        embeddings:     LangChain Embeddings — required for 'semantic' method
        separators:     override default separators for 'recursive'

    Returns:
        A LangChain TextSplitter instance
    """
    if method == "recursive":
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        seps = separators or ["\n\n", "\n", ". ", "! ", "? ", "։ ", " ", ""]
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=seps,
            length_function=len,
        )

    elif method == "semantic":
        if embeddings is None:
            raise ValueError(
                "SemanticChunker requires an embeddings model. "
                "Ensure an embedding model is configured before embedding."
            )
        from langchain_experimental.text_splitter import SemanticChunker
        # breakpoint_threshold_type options:
        #   'percentile'     — split where similarity drops below Nth percentile (default)
        #   'standard_deviation' — split at > 1 std dev below mean
        #   'interquartile'  — split using IQR outlier detection
        return SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=85,   # top 15% dissimilarity = split point
        )

    elif method == "sentence":
        from langchain_text_splitters import SentenceTransformersTokenTextSplitter
        return SentenceTransformersTokenTextSplitter(
            chunk_size=min(chunk_size, 256),  # most ST models cap at 256–512 tokens
            chunk_overlap=chunk_overlap,
        )

    elif method == "paragraph":
        from langchain_text_splitters import CharacterTextSplitter
        return CharacterTextSplitter(
            separator="\n\n",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    elif method == "token":
        from langchain_text_splitters import TokenTextSplitter
        return TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    elif method == "markdown":
        from langchain_text_splitters import MarkdownHeaderTextSplitter
        headers = [
            ("#",   "Header 1"),
            ("##",  "Header 2"),
            ("###", "Header 3"),
        ]
        return MarkdownHeaderTextSplitter(headers_to_split_on=headers)

    else:
        raise ValueError(f"Unknown splitter method: {method!r}")


def split_documents(docs: list, splitter) -> list:
    """
    Split a list of LangChain Documents using the given splitter.
    Handles MarkdownHeaderTextSplitter which has a different API.
    """
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    if isinstance(splitter, MarkdownHeaderTextSplitter):
        # This splitter operates on raw text, not Document objects
        result = []
        for doc in docs:
            splits = splitter.split_text(doc.page_content)
            for split in splits:
                # Merge parent metadata into each split
                split.metadata.update(doc.metadata)
            result.extend(splits)
        return result

    return splitter.split_documents(docs)