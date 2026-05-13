"""
Dashboard de Vendas GFlex — Pagina Inicial
Autenticacao + Sidebar com filtros globais.
"""
import streamlit as st
from config import EMPRESAS, EMPRESA_LABELS, CORES, get_periodo
from styles import inject_css
from components import page_header, icon

st.set_page_config(page_title="GFlex Vendas", page_icon="\U0001f4ca", layout="wide", initial_sidebar_state="expanded")

# ========================================
# AUTENTICACAO — acesso por senha
# ========================================
def check_password():
    """Verifica se o usuario digitou a senha correta."""
    try:
        correct = st.secrets["app"]["password"]
    except Exception:
        # Fallback para desenvolvimento local apenas — usa env var, nao hardcode
        import os as _os
        correct = _os.getenv("APP_PASSWORD", "")
        if not correct:
            st.error("Senha nao configurada. Configure st.secrets ou APP_PASSWORD.")
            st.stop()
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

# CSS unificado (Hub-like: Inter, vars, dark-mode aware, cards premium)
inject_css()

# Sidebar
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:12px 0 16px 0;border-bottom:1px solid var(--border);margin-bottom:14px">'
        '<div style="font-size:1.5rem;font-weight:800;color:var(--text);letter-spacing:-0.5px">GFlex</div>'
        '<div style="color:var(--accent);font-size:0.7rem;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;margin-top:2px">Painel de Vendas</div>'
        '</div>',
        unsafe_allow_html=True,
    )

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
    st.markdown(
        '<div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);'
        'font-size:0.7rem;color:var(--text-muted);text-align:center">'
        'Salesforce API \u00b7 Cache 5 min</div>',
        unsafe_allow_html=True,
    )

# Pagina principal - banner Hub-like
st.markdown(page_header(
    title="Dashboard de Vendas",
    subtitle="GFlex Empresas - 6 empresas em tempo real",
), unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center;padding:24px;color:var(--text-secondary);font-size:0.95rem">'
    'Selecione uma secao no menu lateral para comecar a analise.'
    '</div>',
    unsafe_allow_html=True,
)
