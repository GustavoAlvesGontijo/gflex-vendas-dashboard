"""
Pagina 3 — Oportunidades
Secoes: mes vigente por empresa, evolucao mensal, pipeline, detalhamento.
Energy em kWh. Dias uteis para variacao.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES, FASES_PIPELINE,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT,
)
from salesforce_client import (
    get_opps_pipeline, get_opps_motivo_perda, get_opps_por_vendedor,
    get_opps_engajamento, get_opps_tendencia,
    get_opps_mensal_por_empresa, get_opps_ganhas_mensal_por_empresa,
    get_energy_kwh_mensal,
)

def _fmt(v): return f"{int(v):,}".replace(",", ".") if v else "0"
def _fmt_valor(v):
    if not v or pd.isna(v) or v == 0: return "\u2014"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fmt_kwh(v):
    if not v or pd.isna(v) or v == 0: return "\u2014"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"
def _var_html(atual, du_a, anterior, du_b):
    if du_a == 0 or du_b == 0 or anterior == 0: return ""
    pct = ((atual/du_a - anterior/du_b) / (anterior/du_b)) * 100
    if pct > 5: return f'<span style="color:#2E7D32;font-weight:600;font-size:0.8rem">+{pct:.0f}%</span>'
    elif pct < -5: return f'<span style="color:#C62828;font-weight:600;font-size:0.8rem">{pct:.0f}%</span>'
    return f'<span style="color:#888;font-size:0.8rem">{pct:+.0f}%</span>'

def _build(df, val="total"):
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
        d[k] = d.get(k, 0) + (float(r[val]) if r[val] is not None and not pd.isna(r[val]) else 0)
    return d

# --- Header ---
st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.5rem">Oportunidades</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Orcamentos, vendas e pipeline — mes a mes por empresa</p>
</div>
""", unsafe_allow_html=True)

empresa = st.session_state.get("empresa_filtro", "Todas")
hoje = date.today()
m, a = hoje.month, hoje.year
m_ant, a_ant = (m-1, a) if m > 1 else (12, a-1)
du_atual = dias_uteis_ate_hoje(a, m)
du_total = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_ant, m_ant)
nome_ant = MESES_PT[m_ant]

try:
    df_opps = get_opps_mensal_por_empresa()
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()

    opps_qtd = _build(df_opps)
    opps_val = _build(df_opps, "valor")
    ganhas_qtd = _build(df_ganhas)
    ganhas_val = _build(df_ganhas, "valor")

    kwh_mes = {}
    if not df_kwh.empty:
        for _, r in df_kwh.iterrows():
            kwh_mes[(int(r["ano"]), int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0

    def _g(d, emp, ano, mes): return d.get((emp, ano, mes), 0)

    # ========================================
    # SECAO 1: MES VIGENTE por empresa
    # ========================================
    st.markdown(f"### Mes Vigente — {MESES_PT[m]}/{a}")
    st.caption(f"{du_atual} de {du_total} DU | vs {nome_ant} ({du_ant} DU)")

    empresas_exibir = [empresa] if empresa != "Todas" else EMPRESAS

    for emp in empresas_exibir:
        cor = CORES.get(emp, {}).get("primaria", "#1a1a2e")
        label = EMPRESA_LABELS.get(emp, emp)
        is_energy = (emp == "Flex Energy")

        oq = _g(opps_qtd, emp, a, m)
        oq_ant = _g(opps_qtd, emp, a_ant, m_ant)
        ov = _g(opps_val, emp, a, m)
        ov_ant = _g(opps_val, emp, a_ant, m_ant)
        gq = _g(ganhas_qtd, emp, a, m)
        gq_ant = _g(ganhas_qtd, emp, a_ant, m_ant)
        gv = _g(ganhas_val, emp, a, m)
        gv_ant = _g(ganhas_val, emp, a_ant, m_ant)

        if is_energy:
            kwh_a = kwh_mes.get((a, m), 0)
            kwh_b = kwh_mes.get((a_ant, m_ant), 0)
            vol_fmt = _fmt_kwh(kwh_a)
            vol_ant_fmt = _fmt_kwh(kwh_b)
            vol_label = "Energia Vendida"
            vol_var = _var_html(kwh_a, du_atual, kwh_b, du_ant)
            vol_color = "#EC8500"
            orc_fmt = _fmt_kwh(ov)
            orc_ant_fmt = _fmt_kwh(ov_ant)
            orc_label = "Energia Orcada"
        else:
            vol_fmt = _fmt_valor(gv)
            vol_ant_fmt = _fmt_valor(gv_ant)
            vol_label = "Valor Vendido"
            vol_var = _var_html(gv, du_atual, gv_ant, du_ant)
            vol_color = "#2E7D32"
            orc_fmt = _fmt_valor(ov)
            orc_ant_fmt = _fmt_valor(ov_ant)
            orc_label = "Valor Orcado"

        v_oq = _var_html(oq, du_atual, oq_ant, du_ant)
        v_gq = _var_html(gq, du_atual, gq_ant, du_ant)
        v_ov = _var_html(ov, du_atual, ov_ant, du_ant)

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
<span style="font-weight:700;color:{cor};font-size:1rem">{label}</span>
<span style="font-size:0.7rem;color:#999">vs {nome_ant} (por DU)</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:110px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#1565C0">{_fmt(oq)}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase;margin:2px 0">Orcamentos</div>
<div>{v_oq}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#555">{orc_fmt}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase;margin:2px 0">{orc_label}</div>
<div>{v_ov}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#2E7D32">{_fmt(gq)}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase;margin:2px 0">Vendas</div>
<div>{v_gq}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:6px 8px">
<div style="font-size:1.3rem;font-weight:700;color:{vol_color}">{vol_fmt}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase;margin:2px 0">{vol_label}</div>
<div>{vol_var}</div>
</div>
</div>
<div style="font-size:0.7rem;color:#999;margin-top:6px;padding-top:6px;border-top:1px solid #f5f5f5">
{nome_ant}: {_fmt(oq_ant)} orcamentos · {_fmt(gq_ant)} vendas · {vol_ant_fmt}
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SECAO 2: EVOLUCAO MES A MES
    # ========================================
    st.markdown("### Evolucao Mes a Mes")

    meses = []
    mx, ax = m, a
    for _ in range(6):
        meses.append((ax, mx))
        mx -= 1
        if mx == 0: mx, ax = 12, ax-1
    meses.reverse()

    if empresa == "Todas":
        tabela = []
        for (ano, mes) in meses:
            du = dias_uteis_no_mes(ano, mes)
            oq = sum(_g(opps_qtd, e, ano, mes) for e in EMPRESAS)
            gq = sum(_g(ganhas_qtd, e, ano, mes) for e in EMPRESAS)
            gv = sum(_g(ganhas_val, e, ano, mes) for e in EMPRESAS)
            wr = (gq/oq*100) if oq > 0 else 0
            tabela.append({"Mes": f"{MESES_PT[mes]}/{ano}", "DU": du, "Orcamentos": int(oq), "Vendas": int(gq), "Win%": f"{wr:.0f}%", "Valor Vendido": _fmt_valor(gv), "Opps/DU": f"{oq/du:.0f}" if du > 0 else "\u2014"})
        st.dataframe(pd.DataFrame(tabela), width="stretch", hide_index=True)
    else:
        emp = empresa
        is_energy = (emp == "Flex Energy")
        tabela = []
        for (ano, mes) in meses:
            du = dias_uteis_no_mes(ano, mes)
            oq = _g(opps_qtd, emp, ano, mes)
            gq = _g(ganhas_qtd, emp, ano, mes)
            gv = _g(ganhas_val, emp, ano, mes)
            wr = (gq/oq*100) if oq > 0 else 0
            vol = _fmt_kwh(kwh_mes.get((ano, mes), 0)) if is_energy else _fmt_valor(gv)
            tabela.append({"Mes": f"{MESES_PT[mes]}/{ano}", "DU": du, "Orcamentos": int(oq), "Vendas": int(gq), "Win%": f"{wr:.0f}%", "Volume": vol})
        st.dataframe(pd.DataFrame(tabela), width="stretch", hide_index=True)

    st.markdown("---")

    # ========================================
    # SECAO 3: DETALHAMENTO (pipeline, engajamento, motivos)
    # ========================================
    st.markdown("### Detalhamento do Periodo")
    data_inicio = st.session_state.get("data_inicio")
    data_fim = st.session_state.get("data_fim")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### Pipeline por Fase")
        df_pipe = get_opps_pipeline(empresa, data_inicio, data_fim)
        if not df_pipe.empty:
            ordem = {s:i for i,s in enumerate(FASES_PIPELINE)}
            df_pipe["ord"] = df_pipe["StageName"].map(ordem).fillna(99)
            df_pipe = df_pipe.sort_values("ord")
            cores_f = {"Novo":"#42A5F5","Em Analise":"#66BB6A","Contato Ativo":"#FFA726","Contato Passivo":"#FF7043","Negociacao":"#AB47BC","Contrato":"#26C6DA","Em Cotacao":"#78909C","Fechado Ganho":"#2E7D32","Fechado Perdido":"#C62828"}
            fig = px.bar(df_pipe, x="total", y="StageName", orientation="h", text="total", color="StageName", color_discrete_map=cores_f)
            fig.update_layout(yaxis_title="", xaxis_title="", height=400, showlegend=False, margin=dict(l=0,r=40,t=10,b=10))
            fig.update_traces(textposition="outside")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("#### Motivos de Perda")
        df_perda = get_opps_motivo_perda(empresa, data_inicio, data_fim)
        if not df_perda.empty:
            df_perda = df_perda.sort_values("total", ascending=True)
            fig2 = px.bar(df_perda, x="total", y="Motivo_da_Perda__c", orientation="h", text="total", color_discrete_sequence=["#C62828"])
            fig2.update_layout(yaxis_title="", xaxis_title="", height=400, showlegend=False, margin=dict(l=0,r=40,t=10,b=10))
            fig2.update_traces(textposition="outside")
            st.plotly_chart(fig2, use_container_width=True)

    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("#### Engajamento Comercial")
        st.caption("Tempo sem movimentacao — nivel alto = urgente")
        df_eng = get_opps_engajamento(empresa, data_inicio, data_fim)
        if not df_eng.empty:
            df_eng = df_eng[df_eng["Engajamento_Comercial__c"].notna()]
            cores_e = {"1o Nivel":"#4CAF50","2o Nivel":"#8BC34A","3o Nivel":"#FFC107","4o Nivel":"#FF9800","5o Nivel":"#FF5722","6o Nivel":"#D32F2F"}
            fig3 = px.pie(df_eng, names="Engajamento_Comercial__c", values="total", color="Engajamento_Comercial__c", color_discrete_map=cores_e)
            fig3.update_traces(textposition="inside", textinfo="percent+label+value")
            fig3.update_layout(height=350, margin=dict(t=10,b=10))
            st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        st.markdown("#### Tendencia Mensal")
        df_tend = get_opps_tendencia(empresa, data_inicio, data_fim)
        if not df_tend.empty:
            df_tend["periodo"] = df_tend.apply(lambda r: f"{MESES_PT.get(int(r['mes']),'?')}/{str(int(r['ano']))[2:]}", axis=1)
            fig4 = px.line(df_tend, x="periodo", y="total", markers=True, color_discrete_sequence=["#1a1a2e"])
            fig4.update_layout(xaxis_title="", yaxis_title="Opps Criadas", height=350, margin=dict(t=10,b=10))
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Ranking de Vendedores")
    df_vend = get_opps_por_vendedor(empresa, data_inicio, data_fim)
    if not df_vend.empty:
        pivot = df_vend.pivot_table(index="Owner.Name", columns="StageName", values="total", fill_value=0, aggfunc="sum").reset_index()
        pivot["Total"] = pivot.select_dtypes(include="number").sum(axis=1)
        if "Fechado Ganho" in pivot.columns and "Fechado Perdido" in pivot.columns:
            pivot["Fechadas"] = pivot["Fechado Ganho"] + pivot["Fechado Perdido"]
            pivot["Win%"] = pivot.apply(lambda r: f"{(r['Fechado Ganho']/r['Fechadas']*100):.0f}%" if r["Fechadas"] > 0 else "\u2014", axis=1)
        pivot = pivot.sort_values("Total", ascending=False).head(25)
        st.dataframe(pivot, width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
