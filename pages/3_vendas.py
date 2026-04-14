"""
Pagina 3 — Vendas
Historico mensal por empresa com grafico de linhas (2 eixos: qtd + volume).
Filtro de Ano Fiscal. Energy em kWh, demais em R$.
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
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Historico mensal com grafico de evolucao — Energy em kWh, demais em R$</p>
</div>
""", unsafe_allow_html=True)

hoje = date.today()
anos_disp = list(range(hoje.year, 2024, -1))
af = st.selectbox("Ano Fiscal", anos_disp, index=0, key="af_vendas")
empresa = st.session_state.get("empresa_filtro", "Todas")

try:
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()

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

    meses_af = [(af, mx) for mx in range(1, 13) if af < hoje.year or mx <= hoje.month]
    empresas_ex = [empresa] if empresa != "Todas" and empresa in EMPRESAS else EMPRESAS

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        ie = (emp == "Flex Energy")

        # Coletar dados
        meses_label = []; vendas_qtd = []; vendas_vol = []
        total_v = 0; total_vol = 0
        for (ano, mes) in meses_af:
            meses_label.append(MESES_PT[mes])
            gq = ganhas_q.get((emp, ano, mes), 0)
            gv = ganhas_v.get((emp, ano, mes), 0)
            total_v += gq
            vendas_qtd.append(gq)
            if ie:
                kh = kwh_m.get((ano, mes), 0)
                total_vol += kh
                vendas_vol.append(kh)
            else:
                total_vol += gv
                vendas_vol.append(gv)

        vol_total_fmt = _fk(total_vol) if ie else _fv(total_vol)
        unid = "kWh" if ie else "R$"

        # Card resumo
        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center">
<span style="font-weight:700;color:{cor};font-size:1.05rem">{label} \u2014 {af}</span>
<div style="display:flex;gap:20px">
<div style="text-align:center"><span style="font-size:1.3rem;font-weight:700;color:#2E7D32">{_fmt(total_v)}</span><div style="font-size:0.55rem;color:#888;text-transform:uppercase">vendas no ano</div></div>
<div style="text-align:center"><span style="font-size:1.3rem;font-weight:700;color:{cor}">{vol_total_fmt}</span><div style="font-size:0.55rem;color:#888;text-transform:uppercase">{unid} no ano</div></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

        # Grafico de linhas com 2 eixos
        fig = go.Figure()

        # Linha 1: Quantidade de vendas (eixo esquerdo)
        fig.add_trace(go.Scatter(
            x=meses_label, y=vendas_qtd, name="Vendas (qtd)",
            mode="lines+markers+text",
            line=dict(color=cor, width=3),
            marker=dict(size=10, color=cor, symbol="circle"),
            text=[str(v) for v in vendas_qtd], textposition="top center",
            textfont=dict(size=11, color=cor, family="Arial Black"),
            yaxis="y",
        ))

        # Linha 2: Volume — valor ou kWh (eixo direito)
        fig.add_trace(go.Scatter(
            x=meses_label, y=vendas_vol, name=f"Volume ({unid})",
            mode="lines+markers+text",
            line=dict(color="#2E7D32", width=2, dash="dash"),
            marker=dict(size=8, color="#2E7D32", symbol="diamond"),
            text=[_fk(v) if ie else _fv(v) for v in vendas_vol], textposition="bottom center",
            textfont=dict(size=10, color="#2E7D32"),
            yaxis="y2",
        ))

        fig.update_layout(
            height=340,
            margin=dict(t=20, b=40, l=50, r=60),
            showlegend=True,
            legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", font=dict(size=11)),
            yaxis=dict(title="Vendas (qtd)", side="left", showgrid=True, gridcolor="#f0f0f0", zeroline=False),
            yaxis2=dict(title=f"Volume ({unid})", side="right", overlaying="y", showgrid=False, zeroline=False),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Inter, Arial, sans-serif"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabela compacta
        tab = []
        for i, (ano, mes) in enumerate(meses_af):
            du = dias_uteis_no_mes(ano, mes)
            vol_fmt = _fk(vendas_vol[i]) if ie else _fv(vendas_vol[i])
            vdu = f"{vendas_qtd[i]/du:.1f}" if du > 0 else "\u2014"
            tab.append({"Mes": MESES_PT[mes], "DU": du, "Vendas": vendas_qtd[i], "V/DU": vdu, "Volume": vol_fmt})
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)
        st.markdown("---")

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
