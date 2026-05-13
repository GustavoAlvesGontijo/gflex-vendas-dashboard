"""
CSS compartilhado — importar em todas as paginas.
Estilo Hub-like: Inter, CSS vars (light/dark aware), cards modernos,
tabular-nums, sombras suaves, dataframes premium.
"""
import streamlit as st

# Paleta unica usada em todos os lugares
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ===== Tokens (light) ===== */
:root {
  --bg: #fafafa;
  --bg-card: #ffffff;
  --bg-subtle: #f4f4f5;
  --bg-overlay: rgba(0,0,0,0.03);
  --border: #e4e4e7;
  --border-strong: #d4d4d8;
  --text: #18181b;
  --text-secondary: #52525b;
  --text-muted: #a1a1aa;
  --accent: #EC8500;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 2px 6px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
  --shadow-lg: 0 4px 14px rgba(0,0,0,0.08);
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
}

/* ===== Tokens (dark) — Streamlit injeta data-theme em vários selectores ===== */
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #09090b;
    --bg-card: #18181b;
    --bg-subtle: #27272a;
    --bg-overlay: rgba(255,255,255,0.04);
    --border: #27272a;
    --border-strong: #3f3f46;
    --text: #fafafa;
    --text-secondary: #d4d4d8;
    --text-muted: #71717a;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
    --shadow-md: 0 2px 6px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
    --shadow-lg: 0 4px 14px rgba(0,0,0,0.5);
  }
}
.stApp[data-theme="dark"], html[data-theme="dark"] {
  --bg: #09090b;
  --bg-card: #18181b;
  --bg-subtle: #27272a;
  --bg-overlay: rgba(255,255,255,0.04);
  --border: #27272a;
  --border-strong: #3f3f46;
  --text: #fafafa;
  --text-secondary: #d4d4d8;
  --text-muted: #71717a;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 2px 6px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
  --shadow-lg: 0 4px 14px rgba(0,0,0,0.5);
}

/* ===== Tipografia global ===== */
html, body, [class*="css"], .stApp, [data-testid="stMarkdownContainer"], button {
  font-family: 'Inter', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}
.gx-num, [data-testid="stMetricValue"], .stDataFrame td {
  font-feature-settings: "tnum", "lnum" !important;
  font-variant-numeric: tabular-nums lining-nums;
}

/* ===== Header escuro (toolbar) ===== */
[data-testid="stHeader"]{background-color:#1a1a2e;border-bottom:1px solid var(--border)}

/* ===== Sidebar ===== */
[data-testid="stSidebar"]{
  background:var(--bg-card);
  border-right:1px solid var(--border);
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {color:var(--text);font-size:1.3rem}
[data-testid="stSidebarNav"]{padding-top:8px}
[data-testid="stSidebarNav"] a{
  font-size:0.92rem!important;font-weight:500;padding:9px 14px!important;
  border-radius:8px;margin:2px 8px;transition:all 0.18s ease;
  color:var(--text-secondary)!important;text-decoration:none!important;
  display:flex;align-items:center;gap:8px;
}
[data-testid="stSidebarNav"] a:hover{
  background:#EC850012;color:var(--accent)!important;transform:translateX(2px);
}
[data-testid="stSidebarNav"] a[aria-selected="true"]{
  background:linear-gradient(90deg,#EC850020,#EC850008)!important;
  border-left:3px solid var(--accent)!important;font-weight:700!important;
  color:var(--text)!important;
}

/* Inputs da sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] input {
  border-radius:8px!important;
  border-color:var(--border)!important;
}

/* ===== Métricas nativas Streamlit ===== */
[data-testid="stMetricValue"]{
  font-size:1.55rem;font-weight:700;color:var(--text);
  font-feature-settings:"tnum"!important;
}
[data-testid="stMetricLabel"]{
  font-size:0.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:0.5px;color:var(--text-muted);
}
[data-testid="stMetricDelta"]{
  font-size:0.75rem!important;font-weight:600;
}

/* ===== DataFrames ===== */
[data-testid="stDataFrame"] {
  border-radius:var(--radius-md);
  overflow:hidden;
  box-shadow:var(--shadow-sm);
  border:1px solid var(--border);
}
[data-testid="stDataFrame"] table{border-collapse:collapse;width:100%}
[data-testid="stDataFrame"] th{
  background:#1a1a2e!important;color:white!important;
  font-weight:600;font-size:0.78rem!important;text-transform:uppercase;
  letter-spacing:0.4px;padding:11px 14px!important;
  border:none!important;
}
[data-testid="stDataFrame"] td{
  padding:9px 14px!important;font-size:0.92rem!important;
  border-bottom:1px solid var(--border)!important;color:var(--text)!important;
  font-feature-settings:"tnum"!important;
}
[data-testid="stDataFrame"] tr:nth-child(even) td{background:var(--bg-overlay)!important}
[data-testid="stDataFrame"] tr:hover td{background:#EC850014!important;transition:background 0.12s}

/* ===== Tabs nativos (caso usemos) ===== */
.stTabs [data-baseweb="tab-list"]{
  gap:6px;border-bottom:1px solid var(--border);
}
.stTabs [data-baseweb="tab"]{
  background:transparent;border-radius:8px 8px 0 0;
  padding:8px 16px;font-size:0.85rem;font-weight:600;
  color:var(--text-secondary);
}
.stTabs [aria-selected="true"]{
  color:var(--accent)!important;border-bottom:2px solid var(--accent)!important;
}

/* ===== Botões ===== */
.stButton > button{
  border-radius:8px;font-weight:600;font-size:0.88rem;
  border:1px solid var(--border);transition:all 0.15s;
}
.stButton > button:hover{
  border-color:var(--accent);color:var(--accent);
}

/* ===== Cards Hub-like (utilitarios) ===== */
.gx-card{
  background:var(--bg-card);
  border-radius:var(--radius-lg);
  padding:18px 22px;
  margin-bottom:14px;
  box-shadow:var(--shadow-md);
  border:1px solid var(--border);
  transition:box-shadow 0.18s;
}
.gx-card:hover{box-shadow:var(--shadow-lg)}
.gx-card-accent{border-left:4px solid var(--accent)!important;border-left-width:4px!important}
.gx-tint{border-radius:var(--radius-md);padding:13px 16px}

.gx-h3{font-size:1.25rem;color:var(--text);font-weight:700;margin:24px 0 6px 0;letter-spacing:-0.3px}
.gx-subtle{color:var(--text-muted);font-size:0.85rem;margin-top:-4px;margin-bottom:14px}

/* ===== Footer / scrollbar ===== */
footer{visibility:hidden}
::-webkit-scrollbar{width:7px;height:7px}
::-webkit-scrollbar-thumb{background:var(--border-strong);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:var(--text-muted)}

/* ===== Compactar espaçamento do Streamlit ===== */
.block-container{padding-top:1.5rem;padding-bottom:2rem;max-width:1400px}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)
