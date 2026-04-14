"""
Dashboard de Vendas GFlex — Pagina Inicial
Resumo executivo rapido: KPIs do mes + snapshot de cada empresa.
"""
import streamlit as st
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    MESES_PT, MESES_PT_FULL,
)
from salesforce_client import (
    get_opps_ganhas_mensal_por_empresa,
    get_leads_mensal_por_empresa,
    get_energy_kwh_mensal,
)

st.set_page_config(page_title="GFlex Vendas", page_icon="\U0001f4ca", layout="wide", initial_sidebar_state="expanded")

# CSS
st.markdown("""
<style>
[data-testid="stHeader"]{background-color:#1a1a2e}
[data-testid="stSidebar"]{background-color:#f8f9fa}
[data-testid="stMetricValue"]{font-size:1.6rem;font-weight:700}
footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div style="text-align:center;padding:8px 0 16px 0"><h1 style="color:#1a1a2e;font-size:1.4rem;margin:0">\U0001f4ca GFlex</h1><div style="color:#EC8500;font-size:0.8rem;font-weight:600;letter-spacing:1px;text-transform:uppercase">Painel de Vendas</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    opcoes = ["Todas"] + [EMPRESA_LABELS[e] for e in EMPRESAS]
    emp_label = st.selectbox("Empresa", opcoes, index=0, key="filtro_empresa")
    emp_sf = None
    if emp_label != "Todas":
        for sv, lb in EMPRESA_LABELS.items():
            if lb == emp_label: emp_sf = sv; break
    st.session_state["empresa_filtro"] = emp_sf if emp_sf else "Todas"
    if emp_sf and emp_sf in CORES:
        st.markdown(f'<div style="width:100%;height:4px;background:{CORES[emp_sf]["primaria"]};border-radius:2px;margin-bottom:8px"></div>', unsafe_allow_html=True)
    st.markdown("### Periodo")
    from config import get_periodo
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
    st.caption("Dados ao vivo via Salesforce API")
    st.caption("Cache: 5 min | Org: gflex-empresas")

# ========================================
# PAGINA PRINCIPAL — Resumo Executivo
# ========================================
hoje = date.today()
m, a = hoje.month, hoje.year
m_a, a_a = (m-1, a) if m > 1 else (12, a-1)
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_a, m_a)

st.markdown(f"""
<div style="background:#1a1a2e;padding:20px 28px;border-radius:14px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.6rem;font-weight:700">GFlex Empresas — {MESES_PT_FULL.get(m,"")} {a}</h1>
<div style="display:flex;gap:24px;margin-top:8px">
<span style="color:#EC8500;font-size:0.85rem;font-weight:600">{du_h} de {du_t} dias uteis trabalhados</span>
<span style="color:rgba(255,255,255,0.5);font-size:0.85rem">{MESES_PT[m_a]} teve {du_ant} DU</span>
</div>
</div>
""", unsafe_allow_html=True)

pct = (du_h/du_t*100) if du_t > 0 else 0
st.markdown(f'<div style="background:#e8e8e8;border-radius:6px;height:6px;margin:-12px 0 24px 0"><div style="background:linear-gradient(90deg,#EC8500,#F7C42D);border-radius:6px;height:6px;width:{pct:.0f}%"></div></div>', unsafe_allow_html=True)

def _fmt(v): return f"{int(v):,}".replace(",",".") if v else "0"
def _fv(v):
    if not v or pd.isna(v) or v==0: return "\u2014"
    if v>=1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v>=1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    if not v or pd.isna(v) or v==0: return "\u2014"
    if v>=1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v>=1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"

try:
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_leads = get_leads_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()

    # Totais do mes
    g_total = 0; l_total = 0
    ganhas_emp = {}; leads_emp = {}
    if not df_ganhas.empty:
        for _, r in df_ganhas.iterrows():
            if int(r["ano"])==a and int(r["mes"])==m:
                e = r.get("Empresa_Proprietaria__c","")
                ganhas_emp[e] = ganhas_emp.get(e,0) + int(r["total"])
                g_total += int(r["total"])
    if not df_leads.empty:
        for _, r in df_leads.iterrows():
            if int(r["ano"])==a and int(r["mes"])==m:
                e = r.get("Empresa_Proprietaria__c","")
                leads_emp[e] = leads_emp.get(e,0) + int(r["total"])
                l_total += int(r["total"])

    # KPIs consolidados
    cols = st.columns(3)
    cols[0].metric("Vendas no Mes", _fmt(g_total))
    cols[1].metric("Leads no Mes", _fmt(l_total))
    cols[2].metric("Progresso", f"{pct:.0f}% do mes")

    st.markdown("---")

    # Snapshot por empresa — cards compactos
    st.markdown("### Snapshot por Empresa")

    icones = {"Flex Energy":"\u26a1","GF2 Solu\u00e7\u00f5es Integradas":"\U0001f529","Flex Tendas":"\u26fa","Flex Medi\u00e7\u00f5es":"\U0001f52c","MEC Estruturas Met\u00e1licas":"\U0001f3d7\ufe0f","Flex Solar":"\u2600\ufe0f"}

    for i in range(0, len(EMPRESAS), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(EMPRESAS): break
            emp = EMPRESAS[idx]
            cor = CORES[emp]["primaria"]
            label = EMPRESA_LABELS[emp]
            ic = icones.get(emp,"\U0001f4ca")
            gq = ganhas_emp.get(emp, 0)
            lq = leads_emp.get(emp, 0)
            with col:
                st.markdown(f"""
<div style="background:white;border-radius:12px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.06);border-top:4px solid {cor};height:120px">
<div style="font-weight:700;color:{cor};font-size:0.95rem;margin-bottom:8px">{ic} {label}</div>
<div style="display:flex;gap:20px">
<div><span style="font-size:1.4rem;font-weight:700;color:#2E7D32">{_fmt(gq)}</span><div style="font-size:0.6rem;color:#888;text-transform:uppercase">vendas</div></div>
<div><span style="font-size:1.4rem;font-weight:700;color:#555">{_fmt(lq)}</span><div style="font-size:0.6rem;color:#888;text-transform:uppercase">leads</div></div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Navegacao")
    st.markdown("""
| Secao | O que encontrar |
|-------|-----------------|
| **Visao Geral** | Vendido vs pipeline, combustiveis/origens, evolucao mensal por empresa |
| **Oportunidades** | Cards por empresa + pipeline detalhado por fase |
| **Vendas** | Historico mensal com grafico de linhas (qtd + volume), filtro de ano fiscal |
| **Leads** | %F1, origens por empresa, funil de status por empresa |
""")

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
