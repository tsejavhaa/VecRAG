"""
ui/styles.py — VecRAG theme
Space Grotesk headers · IBM Plex Mono body · Navy + Teal palette
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap');

/* ═══════════════════════════════════════════
   TOKENS
═══════════════════════════════════════════ */
:root {
  --bg:          #080c18;
  --bg2:         #0d1225;
  --surface:     #111827;
  --surface2:    #1a2235;
  --surface3:    #212d42;
  --border:      #1e2d45;
  --border-lt:   #2a3f5f;
  --teal:        #00d4aa;
  --teal-dim:    rgba(0,212,170,0.12);
  --teal-glow:   rgba(0,212,170,0.25);
  --blue:        #3b82f6;
  --blue-dim:    rgba(59,130,246,0.12);
  --text:        #e2e8f8;
  --text-body:   #94a3c0;
  --text-dim:    #4a5a7a;
  --text-code:   #7dd3c8;
  --success:     #34d399;
  --warn:        #fbbf24;
  --danger:      #f87171;
  --radius:      8px;
}

/* ═══════════════════════════════════════════
   GLOBAL
═══════════════════════════════════════════ */
html, body, [class*="css"] {
  font-family: 'IBM Plex Mono', monospace !important;
  background-color: var(--bg) !important;
  color: var(--text-body) !important;
}
#MainMenu, footer { visibility: hidden; }
.stDeployButton   { display: none !important; }
header[data-testid="stHeader"] {
  background: var(--bg) !important;
  border-bottom: 1px solid var(--border) !important;
}
[data-testid="collapsedControl"] {
  background: var(--teal) !important;
  border-radius: 0 8px 8px 0 !important;
  border: none !important;
  display: flex !important; align-items: center !important;
  justify-content: center !important;
  visibility: visible !important; opacity: 1 !important;
  min-width: 30px !important; height: 34px !important;
}
[data-testid="collapsedControl"] svg { fill: #000 !important; color: #000 !important; }
[data-testid="collapsedControl"]:hover { background: #00f0c2 !important; }

/* ═══════════════════════════════════════════
   LAYOUT WRAPPERS
═══════════════════════════════════════════ */
.v2-header {
  display: flex; align-items: baseline; gap: 12px;
  padding: 0.8rem 0 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.4rem;
}
.v2-logo {
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 700; font-size: 1.55rem;
  letter-spacing: -0.03em; color: var(--teal) !important;
}
.v2-tagline {
  font-size: 0.72rem; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.1em;
}
.v2-badge {
  margin-left: auto;
  font-size: 0.6rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--teal); border: 1px solid var(--teal-glow);
  background: var(--teal-dim);
  padding: 3px 10px; border-radius: 999px;
}

/* ═══════════════════════════════════════════
   CONFIG SIDEBAR PANELS
═══════════════════════════════════════════ */
.cfg-section {
  margin-bottom: 1.2rem;
}
.cfg-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.62rem; font-weight: 600;
  letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--teal);
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.7rem;
}
.cfg-hint {
  font-size: 0.68rem; color: var(--text-dim);
  line-height: 1.6; margin-top: 0.3rem;
}

/* ═══════════════════════════════════════════
   STATUS DOTS
═══════════════════════════════════════════ */
.status-row {
  display: flex; align-items: center; gap: 8px;
  padding: 0.5rem 0.7rem;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; margin-bottom: 0.5rem;
  font-size: 0.72rem; color: var(--text-body);
}
.dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.dot-ok    { background: var(--success); box-shadow: 0 0 6px var(--success); }
.dot-warn  { background: var(--warn); }
.dot-off   { background: var(--border-lt); }
.dot-pulse {
  background: var(--teal);
  box-shadow: 0 0 6px var(--teal);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.7); }
}

/* ═══════════════════════════════════════════
   CARDS
═══════════════════════════════════════════ */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.2rem; margin-bottom: 0.8rem;
  color: var(--text-body);
}
.card-teal    { border-left: 3px solid var(--teal); }
.card-blue    { border-left: 3px solid var(--blue); }
.card-success { border-left: 3px solid var(--success); }
.card-warn    { border-left: 3px solid var(--warn); }
.card-danger  { border-left: 3px solid var(--danger); }
.card b, .card strong { color: var(--text) !important; }
.card code {
  background: var(--teal-dim); color: var(--text-code) !important;
  padding: 1px 6px; border-radius: 4px; font-size: 0.85em;
}

/* ═══════════════════════════════════════════
   STAT BOXES
═══════════════════════════════════════════ */
.stat-row  { display: flex; gap: 0.7rem; flex-wrap: wrap; margin-bottom: 1rem; }
.stat-box  {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 0.6rem 1rem;
  flex: 1; min-width: 90px;
}
.stat-val  {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 1.4rem; font-weight: 700; color: var(--teal);
}
.stat-lbl  {
  font-size: 0.62rem; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px;
}

/* ═══════════════════════════════════════════
   TERMINAL LOG
═══════════════════════════════════════════ */
.terminal {
  background: #030508;
  border: 1px solid var(--border-lt);
  border-top: 3px solid var(--teal);
  border-radius: 0 0 8px 8px;
  padding: 1rem 1.1rem;
  font-size: 0.73rem; line-height: 2;
  max-height: 340px; overflow-y: auto;
  color: #8fbcbb;
  font-family: 'IBM Plex Mono', monospace;
  white-space: pre-wrap;
}
.terminal-header {
  background: var(--surface3);
  border: 1px solid var(--border-lt);
  border-bottom: none; border-radius: 8px 8px 0 0;
  padding: 0.4rem 0.8rem;
  display: flex; align-items: center; gap: 6px;
}
.term-dot { width: 10px; height: 10px; border-radius: 50%; }
.term-dot-r { background: #ff5f57; }
.term-dot-y { background: #febc2e; }
.term-dot-g { background: #28c840; }
.term-title {
  margin-left: auto; font-size: 0.62rem; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: 0.1em;
  font-family: 'IBM Plex Mono', monospace;
}
.terminal::-webkit-scrollbar { width: 4px; }
.terminal::-webkit-scrollbar-thumb { background: var(--border-lt); border-radius: 4px; }
/* blinking cursor on last line */
.terminal::after {
  content: "█";
  color: var(--teal);
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* ═══════════════════════════════════════════
   PAGE PREVIEW
═══════════════════════════════════════════ */
.page-viewer {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  max-width: 700px; margin: 0 auto;
}
.page-viewer img { width: 100%; display: block; border-radius: 4px; }
.page-caption {
  text-align: center; font-size: 0.62rem;
  color: var(--text-dim); margin-top: 6px; padding-bottom: 2px;
}

/* ═══════════════════════════════════════════
   SECTION HEADER
═══════════════════════════════════════════ */
.sh {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.65rem; font-weight: 600;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--text-dim);
  margin: 1.1rem 0 0.5rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid var(--border);
}

/* ═══════════════════════════════════════════
   RESULT CARD
═══════════════════════════════════════════ */
.result-card {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--teal);
  border-radius: var(--radius);
  padding: 1.2rem 1.4rem 1.4rem; margin-bottom: 0.8rem;
  position: relative; transition: border-color 0.2s;
}
.result-card:hover { border-color: var(--teal); border-left-color: var(--teal); }
.result-score {
  position: absolute; top: 0.9rem; right: 0.9rem;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.68rem; font-weight: 700;
  padding: 2px 9px; border-radius: 4px;
}
.score-hi  { background: rgba(52,211,153,0.18); color: #34d399; }
.score-mid { background: rgba(251,191,36,0.18);  color: #fbbf24; }
.score-lo  { background: rgba(248,113,113,0.18); color: #f87171; }
.result-meta {
  font-size: 0.68rem; color: var(--text-dim);
  margin-bottom: 0.7rem; padding-right: 3.5rem; /* don't overlap score badge */
}
.result-text {
  font-size: 0.82rem; line-height: 1.85;
  color: #c8d4f0;        /* brighter than text-body so text is easy to read */
  white-space: pre-wrap; /* preserve paragraph breaks in chunk text */
}

/* ═══════════════════════════════════════════
   BUTTONS
═══════════════════════════════════════════ */
.stButton > button {
  background: var(--teal) !important; color: #000 !important;
  border: none !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 600 !important; letter-spacing: 0.03em !important;
  border-radius: var(--radius) !important;
  padding: 0.45rem 1.2rem !important;
  transition: box-shadow 0.15s, opacity 0.15s !important;
}
.stButton > button:hover {
  box-shadow: 0 0 18px var(--teal-glow) !important;
  opacity: 0.88 !important;
}
.stButton > button:disabled {
  background: var(--surface3) !important;
  color: var(--text-dim) !important;
  box-shadow: none !important; opacity: 0.5 !important;
}
.stDownloadButton > button {
  background: var(--surface2) !important;
  color: var(--text-body) !important;
  border: 1px solid var(--border-lt) !important;
  font-size: 0.78rem !important;
}
.stDownloadButton > button:hover {
  border-color: var(--teal) !important; color: var(--teal) !important;
}

/* ═══════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════ */
div[data-testid="stSelectbox"] > div,
div[data-testid="stNumberInput"] > div input,
div[data-testid="stTextInput"] > div input,
div[data-testid="stTextArea"] textarea {
  background: var(--surface2) !important;
  border-color: var(--border-lt) !important;
  color: var(--text) !important;
  border-radius: 6px !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 0.82rem !important;
}
/* Placeholder text — was near-invisible dark gray, now clearly readable */
div[data-testid="stTextInput"] > div input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
  color: #5a7090 !important;   /* muted teal-gray, clearly visible but distinct from typed text */
  opacity: 1 !important;
}
/* Typed / active text — full brightness */
div[data-testid="stTextInput"] > div input:not(:placeholder-shown),
div[data-testid="stTextArea"] textarea:not(:placeholder-shown) {
  color: #e2e8f8 !important;
}
/* Focus ring */
div[data-testid="stTextInput"] > div input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: var(--teal) !important;
  box-shadow: 0 0 0 2px var(--teal-dim) !important;
  outline: none !important;
}

/* ═══════════════════════════════════════════
   SLIDER — SURGICAL FIX
═══════════════════════════════════════════ */
div[data-testid="stSlider"] [data-baseweb="slider"] * {
  background: transparent !important; box-shadow: none !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child {
  background: var(--surface3) !important;
  height: 4px !important; border-radius: 4px !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child > div:first-child {
  background: var(--teal) !important;
  height: 4px !important; border-radius: 4px !important;
}
div[data-testid="stSlider"] [role="slider"] {
  background: var(--teal) !important;
  border: 2px solid var(--bg) !important;
  border-radius: 50% !important;
  width: 16px !important; height: 16px !important; top: -6px !important;
  box-shadow: 0 0 0 3px var(--teal-glow) !important;
}
div[data-testid="stSlider"] span,
div[data-testid="stSlider"] p { color: var(--text-body) !important; font-size: 0.72rem !important; }

/* ═══════════════════════════════════════════
   LABELS / TABS / MISC
═══════════════════════════════════════════ */
label, .stSelectbox label, .stTextInput label,
.stSlider label, .stNumberInput label {
  color: var(--text-dim) !important;
  font-size: 0.68rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important; gap: 0;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: var(--text-dim) !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 0.8rem !important; font-weight: 600 !important;
  border-radius: 0 !important; padding: 0.55rem 1.3rem !important;
}
.stTabs [aria-selected="true"] {
  color: var(--teal) !important;
  border-bottom: 2px solid var(--teal) !important;
}
div[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
}
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p {
  color: var(--text-body) !important; font-size: 0.8rem !important;
}
div[data-testid="stFileUploader"] {
  background: var(--surface2) !important;
  border: 2px dashed var(--border-lt) !important;
  border-radius: var(--radius) !important;
}
div[data-testid="stFileUploader"]:hover { border-color: var(--teal) !important; }

/* ── Drop zone interior (cloud icon + "Drag and drop" text) ──────
   The drop zone sits on a LIGHT surface so text must be DARK/DIM.
   var(--text-body)=#94a3c0 appears too teal-bright on the light bg.  */
div[data-testid="stFileUploader"] > div:first-child p,
div[data-testid="stFileUploader"] > div:first-child span,
div[data-testid="stFileUploader"] > div:first-child small,
div[data-testid="stFileUploader"] [data-testid="stFileDropzoneInstructions"] *,
div[data-testid="stFileUploader"] [class*="instructions"] * {
  color: #4a6080 !important;   /* dim blue-gray — readable on light surface */
}
/* Browse files button inside drop zone */
div[data-testid="stFileUploader"] > div:first-child button {
  color: #4a6080 !important;
  border-color: #8aabb0 !important;
}

/* ── Uploaded file row ───────────────────────────────────────────
   This sits on a DARK surface — text must be BRIGHT.             */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
div[data-testid="stFileUploader"] li,
div[data-testid="stFileUploader"] .uploadedFile {
  background: var(--surface3) !important;
  border: 1px solid var(--border-lt) !important;
  border-radius: 6px !important;
}
/* Filename: bright white */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *,
div[data-testid="stFileUploader"] li *,
div[data-testid="stFileUploader"] .uploadedFile * {
  color: #dde6f8 !important;
}
/* File size: teal accent so it's visually distinct from filename */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] small,
div[data-testid="stFileUploader"] [class*="fileSize"],
div[data-testid="stFileUploader"] li small {
  color: #7dd3c8 !important;
}
/* Delete (×) button */
div[data-testid="stFileUploader"] button[title="Remove file"],
div[data-testid="stFileUploader"] button[aria-label="Remove file"] {
  color: #94a3c0 !important;
}
div[data-testid="stFileUploader"] button[title="Remove file"]:hover,
div[data-testid="stFileUploader"] button[aria-label="Remove file"]:hover {
  color: #f87171 !important;
}
div.stAlert { background: var(--surface2) !important; border-radius: 8px !important; }
div.stAlert p { color: var(--text-body) !important; }
.stProgress > div > div > div { background: var(--teal) !important; }

/* ═══════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════ */
section[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label { color: var(--text-body) !important; }
section[data-testid="stSidebar"] .stButton > button {
  width: 100% !important;
}
section[data-testid="stSidebar"] button[kind="header"],
section[data-testid="stSidebar"] [data-testid="baseButton-header"] {
  background: var(--surface3) !important; color: var(--text-body) !important;
  border-radius: 6px !important; border: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] button[kind="header"]:hover {
  background: var(--teal-dim) !important; color: var(--teal) !important;
  border-color: var(--teal) !important;
}
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)