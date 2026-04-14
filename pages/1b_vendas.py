"""
Pagina 1b — Vendas
Historico mes a mes de vendas de cada empresa.
Filtro de ano fiscal (AF) para facilitar visualizacao.
Energy em kWh, demais em R$.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, MESES_PT,
)
from salesforce_client import (
    get_opps_ganhas_mensal_por_empresa,
    get_energy_kwh_mensal,
)

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

st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.5rem">Vendas</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Historico mensal de vendas por empresa — Energy em kWh, demais em R$</p>
</div>
""", unsafe_allow_html=True)

# Filtro de Ano Fiscal
hoje = date.today()
anos_disp = list(range(hoje.year, 2024, -1))
af = st.selectbox("Ano Fiscal", anos_disp, index=0, key="filtro_af_vendas")

try:
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()

    # Dicts
    ganhas_q = {}; ganhas_v = {}
    if not df_ganhas.empty:
        for _, r in df_ganhas.iterrows():
            k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
            ganhas_q[k] = ganhas_q.get(k,0) + int(r["total"])
            ganhas_v[k] = ganhas_v.get(k,0) + (float(r["valor"]) if r["valor"] else 0)
    kwh_m = {}
    if not df_kwh.empty:
        for _, r in df_kwh.iterrows():
            kwh_m[(int(r["ano"]),int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0

    # Meses do ano selecionado
    meses_af = [(af, mx) for mx in range(1, 13) if af < hoje.year or mx <= hoje.month]

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
        ie = (emp == "Flex Energy")

        tab = []
        total_vendas = 0
        total_vol = 0
        for (ano, mes) in meses_af:
            du = dias_uteis_no_mes(ano, mes)
            gq = ganhas_q.get((emp, ano, mes), 0)
            gv = ganhas_v.get((emp, ano, mes), 0)
            total_vendas += gq
            if ie:
                kh = kwh_m.get((ano, mes), 0)
                total_vol += kh
                vol = _fk(kh)
            else:
                total_vol += gv
                vol = _fv(gv)
            tab.append({
                "Mes": MESES_PT[mes],
                "DU": du,
                "Vendas": int(gq),
                "Vendas/DU": f"{gq/du:.1f}" if du > 0 else "\u2014",
                "Volume": vol,
            })

        # Linha total
        vol_total = _fk(total_vol) if ie else _fv(total_vol)

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
<span style="font-weight:700;color:{cor};font-size:1.05rem">{label} — {af}</span>
<div style="display:flex;gap:16px">
<span style="font-size:0.85rem;font-weight:600;color:#2E7D32">{_fmt(total_vendas)} vendas</span>
<span style="font-size:0.85rem;font-weight:600;color:{cor}">{vol_total}</span>
</div>
</div>
</div>
""", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)

        # Mini grafico de barras
        if tab:
            df_ch = pd.DataFrame(tab)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_ch["Mes"], y=df_ch["Vendas"], marker_color=cor, text=df_ch["Vendas"], textposition="outside"))
            fig.update_layout(height=250, margin=dict(t=10,b=10,l=40,r=20), showlegend=False, yaxis_title="Vendas")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
