"""
Pagina 3 — Vendas
Historico mensal por empresa com grafico de linhas (2 eixos: qtd + volume).
Filtro de Ano Fiscal. Energy em kWh, demais em R$.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Auth check
if not st.session_state.get("authenticated", False):
    st.warning("Acesse pela pagina principal para fazer login.")
    st.stop()
from styles import inject_css
inject_css()
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, MESES_PT, get_logo_b64,
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
<h1 style="color:white;margin:0;font-size:1.8rem">🏆 VENDAS</h1>
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
<div style="display:flex;align-items:center;gap:12px"><img src="{get_logo_b64(emp)}" style="height:38px;border-radius:6px" alt="{label}"/><span style="font-weight:700;color:{cor};font-size:1.05rem">{label} \u2014 {af}</span></div>
<div style="display:flex;gap:20px">
<div style="text-align:center"><span style="font-size:1.3rem;font-weight:700;color:#2E7D32">{_fmt(total_v)}</span><div style="font-size:0.55rem;color:#888;text-transform:uppercase">vendas no ano</div></div>
<div style="text-align:center"><span style="font-size:1.3rem;font-weight:700;color:{cor}">{vol_total_fmt}</span><div style="font-size:0.55rem;color:#888;text-transform:uppercase">{unid} no ano</div></div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

        # 2 graficos lado a lado: Volume (barras grandes) + Vendas (barras)
        from plotly.subplots import make_subplots
        vol_label = "Energia (kWh)" if ie else "Valor Vendido (R$)"

        fig = make_subplots(rows=1, cols=2, subplot_titles=[vol_label, "Vendas (qtd)"], horizontal_spacing=0.08)

        # Barras Volume — COR DA EMPRESA, valor dentro
        fig.add_trace(go.Bar(
            x=meses_label, y=vendas_vol, name=vol_label,
            marker_color=cor, opacity=0.9,
            text=[_fk(v) if ie else _fv(v) for v in vendas_vol],
            textposition="inside", textangle=0,
            textfont=dict(size=12, color="white", family="Arial Black"),
            showlegend=False,
        ), row=1, col=1)

        # Barras Vendas — VERDE, qtd dentro
        fig.add_trace(go.Bar(
            x=meses_label, y=vendas_qtd, name="Vendas",
            marker_color="#2E7D32", opacity=0.9,
            text=[str(v) for v in vendas_qtd],
            textposition="inside", textangle=0,
            textfont=dict(size=14, color="white", family="Arial Black"),
            showlegend=False,
        ), row=1, col=2)

        fig.update_layout(
            height=340,
            margin=dict(t=40, b=20, l=30, r=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Inter, Arial, sans-serif"),
        )
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False)
        st.plotly_chart(fig, use_container_width=True)

        # Tabela HTML atrativa
        col_vol = "Energia" if ie else "Valor"
        rows_html = ""
        for i, (ano, mes) in enumerate(meses_af):
            du = dias_uteis_no_mes(ano, mes)
            vol_fmt = _fk(vendas_vol[i]) if ie else _fv(vendas_vol[i])
            vdu = f"{vendas_qtd[i]/du:.1f}" if du > 0 else "\u2014"
            bg = "#fff" if i % 2 == 0 else "#F8F9FA"
            rows_html += f'<tr style="background:{bg}"><td style="font-weight:600;color:#1a1a2e">{MESES_PT[mes]}</td><td style="text-align:center;color:#888">{du}</td><td style="text-align:center;font-weight:700;color:#2E7D32;font-size:1.05rem">{vendas_qtd[i]}</td><td style="text-align:center;color:#888">{vdu}</td><td style="text-align:right;font-weight:700;color:{cor};font-size:1.05rem">{vol_fmt}</td></tr>'

        hdr = f'<tr style="background:#1a1a2e"><th style="color:white;padding:10px 12px;font-size:0.8rem">Mes</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.8rem">DU</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.8rem">Vendas</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.75rem">Vendas/DU</th><th style="color:white;text-align:right;padding:10px 12px;font-size:0.8rem">{col_vol}</th></tr>'

        st.markdown(f'<table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-top:8px">{hdr}{rows_html}</table>', unsafe_allow_html=True)
        st.markdown("---")

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
