"""
Pagina 6 — Vendedores
Ranking por empresa, performance individual, leads atribuidos.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from config import EMPRESAS, EMPRESA_LABELS, CORES
from salesforce_client import get_ranking_vendedores, get_opps_por_vendedor, get_leads_por_proprietario

def _fmt(v):
    return f"{int(v):,}".replace(",", ".") if v else "0"

def _fmt_valor(v):
    if not v or pd.isna(v) or v == 0: return "\u2014"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"

# --- Header ---
st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.5rem">Vendedores</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Ranking de performance, oportunidades ganhas e leads atribuidos</p>
</div>
""", unsafe_allow_html=True)

empresa = st.session_state.get("empresa_filtro", "Todas")
data_inicio = st.session_state.get("data_inicio")
data_fim = st.session_state.get("data_fim")

if empresa != "Todas":
    cor = CORES.get(empresa, {}).get("primaria", "#1a1a2e")
    st.markdown(f'<div style="border-left:5px solid {cor};padding-left:12px;margin-bottom:16px"><h3 style="color:{cor};margin:0">{EMPRESA_LABELS.get(empresa, empresa)}</h3></div>', unsafe_allow_html=True)

try:
    # ========================================
    # RANKING POR OPPS GANHAS
    # ========================================
    st.markdown("#### Ranking — Oportunidades Ganhas")
    df_rank = get_ranking_vendedores(empresa, data_inicio, data_fim)

    if not df_rank.empty:
        total_vend = df_rank["Owner.Name"].nunique()
        total_ganhas = int(df_rank["ganhas"].sum())
        total_valor = df_rank["valor"].sum()

        cols = st.columns(3)
        cols[0].metric("Vendedores Ativos", _fmt(total_vend))
        cols[1].metric("Opps Ganhas", _fmt(total_ganhas))
        cols[2].metric("Valor Total", _fmt_valor(total_valor))

        st.markdown("---")

        # Top 15 grafico
        df_top = df_rank.groupby("Owner.Name").agg({"ganhas": "sum", "valor": "sum"}).reset_index()
        df_top = df_top.sort_values("ganhas", ascending=True).tail(15)

        fig = px.bar(df_top, x="ganhas", y="Owner.Name", orientation="h", text="ganhas", color_discrete_sequence=["#2E7D32"])
        fig.update_layout(yaxis_title="", xaxis_title="Oportunidades Ganhas", height=480, showlegend=False, margin=dict(l=0, r=40, t=10, b=10))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela completa
        st.markdown("#### Tabela Completa")
        df_tab = df_rank.copy()
        df_tab["Empresa"] = df_tab["Empresa_Proprietaria__c"].map(EMPRESA_LABELS).fillna(df_tab["Empresa_Proprietaria__c"])
        df_tab["Valor"] = df_tab["valor"].apply(_fmt_valor)
        df_tab = df_tab.sort_values("ganhas", ascending=False)
        st.dataframe(
            df_tab[["Owner.Name", "Empresa", "ganhas", "Valor"]].rename(columns={"Owner.Name": "Vendedor", "ganhas": "Ganhas"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Nenhuma oportunidade ganha no periodo selecionado.")

    st.markdown("---")

    # ========================================
    # PERFORMANCE DETALHADA
    # ========================================
    st.markdown("#### Performance Detalhada")
    df_vend = get_opps_por_vendedor(empresa, data_inicio, data_fim)
    if not df_vend.empty:
        pivot = df_vend.pivot_table(index="Owner.Name", columns="StageName", values="total", fill_value=0, aggfunc="sum").reset_index()
        pivot["Total"] = pivot.select_dtypes(include="number").sum(axis=1)
        if "Fechado Ganho" in pivot.columns and "Fechado Perdido" in pivot.columns:
            pivot["Fechadas"] = pivot["Fechado Ganho"] + pivot["Fechado Perdido"]
            pivot["Win Rate"] = pivot.apply(lambda r: f"{(r['Fechado Ganho']/r['Fechadas']*100):.0f}%" if r["Fechadas"] > 0 else "\u2014", axis=1)
        pivot = pivot.sort_values("Total", ascending=False).head(30)
        st.dataframe(pivot, width="stretch", hide_index=True)

    st.markdown("---")

    # ========================================
    # LEADS ATRIBUIDOS
    # ========================================
    st.markdown("#### Leads Atribuidos (Top 20)")
    df_leads = get_leads_por_proprietario(empresa, data_inicio, data_fim)
    if not df_leads.empty:
        agg = df_leads.groupby("Owner.Name")["total"].sum().reset_index()
        agg = agg.sort_values("total", ascending=True).tail(20)
        fig2 = px.bar(agg, x="total", y="Owner.Name", orientation="h", text="total", color_discrete_sequence=["#1a1a2e"])
        fig2.update_layout(yaxis_title="", xaxis_title="Leads", height=500, showlegend=False, margin=dict(l=0, r=40, t=10, b=10))
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    import traceback
    st.code(traceback.format_exc())
