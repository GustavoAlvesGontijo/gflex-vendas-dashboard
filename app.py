"""
Dashboard de Vendas GFlex — App Principal
Streamlit multipage com filtros globais na sidebar.
"""
import streamlit as st
from config import EMPRESAS, EMPRESA_LABELS, CORES, get_periodo

# --- Page config ---
st.set_page_config(
    page_title="GFlex Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS customizado (identidade visual GFlex + mobile) ---
st.markdown("""
<style>
    /* Header GFlex azul escuro */
    [data-testid="stHeader"] {
        background-color: #1a1a2e;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        color: #1a1a2e;
        font-size: 1.4rem;
    }
    /* Metricas maiores */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Tabelas */
    .stDataFrame thead tr th {
        background-color: #1a1a2e !important;
        color: white !important;
        font-weight: 600;
    }
    /* Cards de empresa */
    .empresa-card {
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        border-left: 5px solid;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .empresa-card h3 {
        margin: 0 0 8px 0;
        font-size: 1.1rem;
    }
    .empresa-card .kpi-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
    }
    .empresa-card .kpi-item {
        text-align: center;
        min-width: 80px;
    }
    .empresa-card .kpi-valor {
        font-size: 1.3rem;
        font-weight: 700;
    }
    .empresa-card .kpi-label {
        font-size: 0.7rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    /* Mobile responsivo */
    @media (max-width: 768px) {
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }
        .empresa-card .kpi-valor {
            font-size: 1rem;
        }
        .empresa-card .kpi-row {
            gap: 8px;
        }
        .empresa-card {
            padding: 12px 14px;
        }
    }
    /* Ocultar footer do Streamlit */
    footer {visibility: hidden;}
    /* Logo area */
    .logo-gflex {
        text-align: center;
        padding: 8px 0 16px 0;
    }
    .logo-gflex h1 {
        color: #1a1a2e;
        font-size: 1.6rem;
        margin: 0;
    }
    .logo-gflex .subtitle {
        color: #EC8500;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar: Filtros Globais ---
with st.sidebar:
    st.markdown("""
    <div class="logo-gflex">
        <h1>📊 GFlex</h1>
        <div class="subtitle">Painel de Vendas</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Filtro de empresa
    opcoes_empresa = ["Todas"] + list(EMPRESA_LABELS.values())
    empresa_label = st.selectbox(
        "Empresa",
        opcoes_empresa,
        index=0,
        key="filtro_empresa",
    )

    # Converter label de volta para valor SF
    empresa_sf = None
    if empresa_label != "Todas":
        for sf_val, label in EMPRESA_LABELS.items():
            if label == empresa_label:
                empresa_sf = sf_val
                break
    st.session_state["empresa_filtro"] = empresa_sf if empresa_sf else "Todas"

    # Mostrar cor da empresa selecionada
    if empresa_sf and empresa_sf in CORES:
        cor = CORES[empresa_sf]["primaria"]
        st.markdown(f'<div style="width:100%;height:4px;background:{cor};border-radius:2px;margin-bottom:8px"></div>', unsafe_allow_html=True)

    # Filtro de periodo
    st.markdown("### Periodo")
    periodo_nome = st.selectbox(
        "Periodo",
        ["Ultimo mes", "Ultimo trimestre", "Ultimo semestre", "Ano atual", "Tudo", "Personalizado"],
        index=1,
        key="filtro_periodo",
        label_visibility="collapsed",
    )

    if periodo_nome == "Personalizado":
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("De", key="data_inicio")
        with col2:
            data_fim = st.date_input("Ate", key="data_fim")
    else:
        data_inicio, data_fim = get_periodo(periodo_nome)

    st.session_state["data_inicio"] = data_inicio
    st.session_state["data_fim"] = data_fim

    st.markdown("---")
    st.caption("Dados ao vivo via Salesforce API")
    st.caption("Cache: 5 min | Org: gflex-empresas")

# --- Pagina principal ---
st.markdown("""
<div style="background:#1a1a2e;padding:20px 24px;border-radius:12px;margin-bottom:24px">
    <h1 style="color:white;margin:0;font-size:1.8rem">Dashboard de Vendas</h1>
    <p style="color:#EC8500;margin:4px 0 0 0;font-size:0.9rem;font-weight:600">GFlex Empresas — Todas as 6 empresas em tempo real</p>
</div>
""", unsafe_allow_html=True)

st.markdown("Navegue pelas paginas no menu lateral para acessar cada area.")

cols = st.columns(3)
paginas = [
    ("📊 Visao Geral", "KPIs consolidados, cards por empresa"),
    ("👥 Leads", "Funil, origens, conversao, temperatura"),
    ("💼 Oportunidades", "Pipeline, fases, win rate, engajamento"),
    ("📦 Ordens de Servico", "Status por empresa, expedicao"),
    ("💰 Pagamentos", "Financeiro GF2/Tendas, inadimplencia"),
    ("🏆 Vendedores", "Ranking, performance individual"),
]
for i, (titulo, desc) in enumerate(paginas):
    with cols[i % 3]:
        st.markdown(f"""
        <div style="background:white;border-radius:10px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);border-top:3px solid #EC8500">
            <strong>{titulo}</strong><br>
            <span style="color:#666;font-size:0.8rem">{desc}</span>
        </div>
        """, unsafe_allow_html=True)
