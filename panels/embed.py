"""
panels/embed.py
────────────────
Tab 2: Configure splitter / embeddings / storage, then embed with live log.
"""
import time
import streamlit as st
from core.splitter   import SPLITTER_INFO
from core.embedder   import HUGGINGFACE_MODELS
from core.vectorstore import submit_job, poll_job
from ui.components   import section, stat_row, terminal_log, card


def panel():
    pdf_bytes = st.session_state.get("pdf_bytes")
    if not pdf_bytes:
        st.info("Upload a PDF in the **Documents** tab first.")
        return

    status = st.session_state.embed_status

    # ══════════════════════════════════════════
    # RUNNING — poll + show live log
    # ══════════════════════════════════════════
    if status == "running":
        job_id = st.session_state.embed_job_id
        state, payload = poll_job(job_id)

        if state == "done":
            chunks, _vs_thread, count = payload
            st.session_state.lc_docs     = chunks
            st.session_state.embed_count = count
            # Reload vectorstore from disk on the main thread — avoids PyTorch/
            # HuggingFace thread-safety issues when the model was created on the
            # worker thread. Critical for Semantic chunking strategy.
            try:
                from core.vectorstore import load_vectorstore
                from core.embedder    import load_embeddings
                _emb = load_embeddings(
                    provider   = st.session_state.embed_provider,
                    model_name = st.session_state.embed_model,
                    ollama_url = st.session_state.ollama_url,
                    device     = st.session_state.device,
                )
                st.session_state.vectorstore = load_vectorstore(
                    collection_name = st.session_state.collection_name,
                    persist_dir     = st.session_state.persist_dir,
                    embeddings      = _emb,
                )
            except Exception:
                st.session_state.vectorstore = _vs_thread  # fallback
            st.session_state.embed_status = "done"
            from core.vectorstore import get_logs
            st.session_state.embed_logs = get_logs(job_id)
            st.rerun(); return

        if state == "error":
            st.session_state.embed_status = "error"
            st.session_state.embed_error  = payload[-1] if payload else "Unknown"
            st.session_state.embed_logs   = payload
            st.rerun(); return

        # Still running
        elapsed = time.time() - st.session_state.embed_start_time
        st.markdown(f"""
        <div class="card card-teal" style="text-align:center;padding:1.2rem">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:1rem;
                      font-weight:600;color:#00d4aa;margin-bottom:4px">
            ⬡ Embedding in progress…
          </div>
          <div style="font-size:0.72rem;color:#4a5a7a">
            Running on background thread · {elapsed:.0f}s elapsed
          </div>
        </div>
        """, unsafe_allow_html=True)
        terminal_log(payload, title="embed.log")
        time.sleep(1); st.rerun(); return

    # ══════════════════════════════════════════
    # DONE
    # ══════════════════════════════════════════
    if status == "done":
        count = st.session_state.embed_count
        stat_row([
            (count,                              "Chunks stored"),
            (st.session_state.collection_name,   "Collection"),
            (st.session_state.persist_dir,        "Path"),
        ])
        card(
            f'<span style="color:#34d399;font-weight:600">✅ Embedding complete.</span>'
            f'<span style="color:#94a3c0"> Switch to the <b>Search</b> tab.</span>',
            variant="success",
        )
        logs = st.session_state.get("embed_logs", [])
        if logs:
            with st.expander("📋  Full embed log"):
                terminal_log(logs)
        # Streamlit has no API for programmatic tab switching —
        # point the user to click the tab themselves.
        st.markdown(
            '<div style="font-size:0.78rem;color:#4a5a7a;margin:0.3rem 0 0.8rem">'
            '→ Click the <b style="color:#e2e8f8">Search</b> tab above to start querying.</div>',
            unsafe_allow_html=True,
        )
        if st.button("↺ Re-embed", key="re_embed"):
            st.session_state.embed_status = "idle"
            st.rerun()
        return

    # ══════════════════════════════════════════
    # ERROR
    # ══════════════════════════════════════════
    if status == "error":
        st.error(f"Embedding failed: {st.session_state.embed_error}")
        with st.expander("Error log"):
            terminal_log(st.session_state.get("embed_logs", []))
        if st.button("↺ Retry"):
            st.session_state.embed_status = "idle"; st.rerun()
        return

    # ══════════════════════════════════════════
    # IDLE — show config summary + launch button
    # ══════════════════════════════════════════
    section("Configuration Summary")

    splitter_method = st.session_state.splitter_method
    chunk_size      = st.session_state.chunk_size
    chunk_overlap   = st.session_state.chunk_overlap
    embed_provider  = st.session_state.embed_provider
    embed_model     = st.session_state.embed_model
    collection_name = st.session_state.collection_name
    persist_dir     = st.session_state.persist_dir
    device          = st.session_state.device

    sp_info = SPLITTER_INFO.get(splitter_method, {})
    hf_info = HUGGINGFACE_MODELS.get(embed_model, {})

    st.markdown(f"""
    <div class="card card-teal">
      <div style="font-size:0.8rem;color:#94a3c0;line-height:2.2">
        ✂️ <b style="color:#e2e8f8">Splitter</b> &nbsp;
           <code>{splitter_method}</code> &nbsp;·&nbsp;
           size <code>{chunk_size}</code> &nbsp;·&nbsp;
           overlap <code>{chunk_overlap}</code><br>
        🧠 <b style="color:#e2e8f8">Embeddings</b> &nbsp;
           <code>{embed_provider}</code> &nbsp;·&nbsp;
           <code>{embed_model}</code>
           {"&nbsp;·&nbsp;" + hf_info.get("size","") if hf_info else ""}<br>
        💾 <b style="color:#e2e8f8">Store</b> &nbsp;
           <code>{persist_dir}</code> &nbsp;/&nbsp; <code>{collection_name}</code><br>
        ⚙️ <b style="color:#e2e8f8">Device</b> &nbsp; <code>{device}</code>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="font-size:0.75rem;color:#94a3c0;margin-bottom:1rem">
      <b style="color:#e2e8f8">What happens when you click Embed:</b><br>
      1 · PDF is loaded page-by-page via LangChain PyPDFLoader<br>
      2 · Text is split with LangChain RecursiveCharacterTextSplitter<br>
      3 · Embedding model downloads from HuggingFace Hub (first run)<br>
      4 · Chunks are embedded in batches and stored in ChromaDB<br>
      <span style="color:#4a5a7a;margin-top:4px;display:block">
        Progress streams live in the terminal below.
      </span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⬡  Embed & Store", key="do_embed"):
        from core.vectorstore import submit_job
        job_id = submit_job(
            pdf_bytes       = pdf_bytes,
            pdf_name        = st.session_state.pdf_name,
            splitter_method = splitter_method,
            chunk_size      = chunk_size,
            chunk_overlap   = chunk_overlap,
            embed_provider  = embed_provider,
            embed_model     = embed_model,
            ollama_url      = st.session_state.ollama_url,
            device          = device,
            collection_name = collection_name,
            persist_dir     = persist_dir,
        )
        st.session_state.embed_job_id    = job_id
        st.session_state.embed_status    = "running"
        st.session_state.embed_start_time = time.time()
        st.rerun()