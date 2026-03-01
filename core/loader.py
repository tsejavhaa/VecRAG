"""
core/loader.py
──────────────
PDF loading via LangChain document loaders.
Also provides page count and single-page render (no LangChain equivalent).
"""

import io
import base64
from typing import Optional


# ── Page count ────────────────────────────────────────────────────

def get_page_count(pdf_bytes: bytes) -> int:
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n = len(doc); doc.close(); return n
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        pass
    return 0


# ── Single-page render ────────────────────────────────────────────

def render_page(pdf_bytes: bytes, page_num: int) -> Optional[str]:
    """Return base64 PNG of one page (1-based). None if no renderer."""
    try:
        import fitz
        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[page_num - 1]
        pix  = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        b64  = base64.b64encode(pix.tobytes("png")).decode()
        doc.close()
        return b64
    except ImportError:
        pass
    try:
        from pdf2image import convert_from_bytes
        imgs = convert_from_bytes(pdf_bytes, dpi=130,
                                  first_page=page_num, last_page=page_num)
        if imgs:
            buf = io.BytesIO()
            imgs[0].save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass
    return None


# ── LangChain document loading ────────────────────────────────────

def load_documents(pdf_bytes: bytes, pdf_name: str, log_fn=None) -> list:
    """
    Load a PDF with LangChain's PyPDFLoader.
    Returns list of LangChain Document objects (one per page).
    Falls back to PyMuPDFLoader if PyPDF fails.
    """
    def _log(msg):
        if log_fn: log_fn(msg)

    # Write bytes to a temp file — LangChain loaders need a file path
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    docs = []
    try:
        _log("📄  Loading PDF with LangChain PyPDFLoader…")
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(tmp_path)
        docs   = loader.load()
        _log(f"✅  Loaded {len(docs)} pages via PyPDFLoader.")
    except Exception as e:
        _log(f"⚠️   PyPDFLoader failed ({e}), trying PyMuPDFLoader…")
        try:
            from langchain_community.document_loaders import PyMuPDFLoader
            loader = PyMuPDFLoader(tmp_path)
            docs   = loader.load()
            _log(f"✅  Loaded {len(docs)} pages via PyMuPDFLoader.")
        except Exception as e2:
            _log(f"❌  Both loaders failed: {e2}")
    finally:
        os.unlink(tmp_path)

    # Enrich metadata
    for doc in docs:
        doc.metadata["pdf_name"] = pdf_name
        doc.metadata.setdefault("page", doc.metadata.get("page", 0))

    return docs