"""
Dashboard de Vendas GFlex — Pagina Inicial
Autenticacao + Sidebar com filtros globais.
"""
import streamlit as st
from config import EMPRESAS, EMPRESA_LABELS, CORES, get_periodo

st.set_page_config(page_title="GFlex Vendas", page_icon="\U0001f4ca", layout="wide", initial_sidebar_state="expanded")

# ========================================
# AUTENTICACAO — acesso por senha
# ========================================
def check_password():
    """Verifica se o usuario digitou a senha correta."""
    try:
        correct = st.secrets["app"]["password"]
    except Exception:
        correct = "gflex2026"  # fallback local
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("""
<div style="max-width:400px;margin:80px auto;text-align:center">
<div style="background:#1a1a2e;padding:24px;border-radius:14px;margin-bottom:24px">
<h1 style="color:white;margin:0;font-size:1.6rem">\U0001f4ca GFlex Vendas</h1>
<p style="color:#EC8500;margin:6px 0 0 0;font-size:0.85rem">Painel de Vendas — Acesso Restrito</p>
</div>
</div>
""", unsafe_allow_html=True)
    pwd = st.text_input("Senha de acesso", type="password", key="pwd_input")
    if pwd:
        if pwd == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    return False

if not check_password():
    st.stop()

# CSS premium executivo
st.markdown("""
<style>
/* Header escuro */
[data-testid="stHeader"]{background-color:#1a1a2e}
/* Sidebar */
[data-testid="stSidebar"]{background:#f8f9fa}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1{color:#1a1a2e;font-size:1.3rem}
/* Sidebar NAV — icones e destaque */
[data-testid="stSidebarNav"]{padding-top:8px}
[data-testid="stSidebarNav"] a{
    font-size:0.95rem!important;font-weight:500;padding:10px 16px!important;
    border-radius:8px;margin:2px 8px;transition:all 0.2s;
    color:#333!important;text-decoration:none!important;
}
[data-testid="stSidebarNav"] a:hover{background:#EC850012;color:#EC8500!important}
[data-testid="stSidebarNav"] a[aria-selected="true"]{
    background:linear-gradient(90deg,#EC850018,#EC850008)!important;
    border-left:4px solid #EC8500!important;font-weight:700!important;
    color:#1a1a2e!important;
}
/* Metricas */
[data-testid="stMetricValue"]{font-size:1.5rem;font-weight:700;color:#1a1a2e}
[data-testid="stMetricLabel"]{font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#666}
/* Tabelas premium — fontes maiores, mais contraste */
[data-testid="stDataFrame"] table{border-collapse:collapse;width:100%}
[data-testid="stDataFrame"] th{
    background:#1a1a2e!important;color:white!important;
    font-weight:600;font-size:0.85rem!important;text-transform:uppercase;
    letter-spacing:0.3px;padding:12px 14px!important;
}
[data-testid="stDataFrame"] td{
    padding:10px 14px!important;font-size:0.95rem!important;
    border-bottom:1px solid #eee!important;color:#1a1a2e!important;
}
[data-testid="stDataFrame"] tr:nth-child(even){background:#F8F9FA!important}
[data-testid="stDataFrame"] tr:hover{background:#FFF3E0!important}
/* Footer */
footer{visibility:hidden}
/* Scrollbar */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div style="text-align:center;padding:8px 0 12px 0"><h1 style="margin:0;font-size:1.4rem">\U0001f4ca GFlex</h1><div style="color:#EC8500;font-size:0.75rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase">Painel de Vendas</div></div>', unsafe_allow_html=True)
    st.markdown("---")

    opcoes = ["Todas"] + [EMPRESA_LABELS[e] for e in EMPRESAS]
    emp_label = st.selectbox("Empresa", opcoes, index=0, key="filtro_empresa")
    emp_sf = None
    if emp_label != "Todas":
        for sv, lb in EMPRESA_LABELS.items():
            if lb == emp_label: emp_sf = sv; break
    st.session_state["empresa_filtro"] = emp_sf if emp_sf else "Todas"
    if emp_sf and emp_sf in CORES:
        st.markdown(f'<div style="width:100%;height:4px;background:{CORES[emp_sf]["primaria"]};border-radius:2px;margin:4px 0 12px 0"></div>', unsafe_allow_html=True)

    st.markdown("##### Periodo")
    periodo = st.selectbox("Periodo", ["Ultimo mes","Ultimo trimestre","Ultimo semestre","Ano atual","Tudo","Personalizado"], index=1, key="filtro_periodo", label_visibility="collapsed")
    if periodo == "Personalizado":
        c1, c2 = st.columns(2)
        with c1: di = st.date_input("De", key="data_inicio")
        with c2: df = st.date_input("Ate", key="data_fim")
    else:
        di, df = get_periodo(periodo)
    st.session_state["data_inicio"] = di
    st.session_state["data_fim"] = df
    st.markdown("---")
    st.caption("Salesforce API \u00b7 Cache 5 min")

# Pagina principal — redirecionamento visual
st.markdown("""
<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2d2d5e 100%);padding:40px 32px;border-radius:16px;margin-bottom:24px;text-align:center">
<h1 style="color:white;margin:0;font-size:2rem;font-weight:700">Dashboard de Vendas</h1>
<p style="color:#EC8500;margin:8px 0 0 0;font-size:1rem;font-weight:500">GFlex Empresas \u2014 6 empresas em tempo real</p>
</div>
""", unsafe_allow_html=True)

st.markdown("Selecione uma secao no menu lateral para comecar a analise.")
