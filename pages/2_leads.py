"""
Pagina 2 — Leads
Organizado em secoes: mes vigente, evolucao mensal, detalhamento.
Cada empresa comparada consigo mesma. Dias uteis para variacao.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT,
)
from salesforce_client import (
    get_leads_por_status, get_leads_por_origem, get_leads_por_rating,
    get_leads_motivo_descarte, get_leads_por_proprietario,
    get_leads_mensal_por_empresa, get_contas_mensal_por_empresa,
    get_leads_convertidos_no_mes_por_empresa,
)

def _fmt(v): return f"{int(v):,}".replace(",", ".") if v else "0"

def _var_html(atual, du_a, anterior, du_b):
    if du_a == 0 or du_b == 0 or anterior == 0: return ""
    pct = ((atual/du_a - anterior/du_b) / (anterior/du_b)) * 100
    if pct > 5: return f'<span style="color:#2E7D32;font-weight:600;font-size:0.8rem">+{pct:.0f}%</span>'
    elif pct < -5: return f'<span style="color:#C62828;font-weight:600;font-size:0.8rem">{pct:.0f}%</span>'
    return f'<span style="color:#888;font-size:0.8rem">{pct:+.0f}%</span>'

def _build(df, val="total", filt_col=None, filt_val=None):
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        if filt_col and r.get(filt_col) != filt_val: continue
        k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
        d[k] = d.get(k, 0) + (float(r[val]) if r[val] is not None and not pd.isna(r[val]) else 0)
    return d

# --- Header ---
st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.5rem">Leads</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Geracao, conversao e qualidade — mes a mes por empresa</p>
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
    df_leads = get_leads_mensal_por_empresa()
    df_contas = get_contas_mensal_por_empresa()
    df_conv_mes = get_leads_convertidos_no_mes_por_empresa()

    leads_total = _build(df_leads)
    leads_criados_e_conv = _build(df_leads, filt_col="IsConverted", filt_val=True)  # criados no mes E convertidos
    contas_d = _build(df_contas)

    # Conversoes do mes (ConvertedDate) — leads convertidos naquele mes, independente de quando criados
    conv_no_mes = _build(df_conv_mes)

    def _g(d, emp, ano, mes): return d.get((emp, ano, mes), 0)

    # ========================================
    # SECAO 1: MES VIGENTE — cada empresa
    # ========================================
    st.markdown(f"### Mes Vigente — {MESES_PT[m]}/{a}")
    st.caption(f"{du_atual} de {du_total} dias uteis | vs {nome_ant} ({du_ant} DU) | variacao normalizada por dia util")

    empresas_exibir = [empresa] if empresa != "Todas" else EMPRESAS
    if empresa != "Todas" and empresa not in EMPRESAS:
        empresas_exibir = EMPRESAS

    for emp in empresas_exibir:
        cor = CORES.get(emp, {}).get("primaria", "#1a1a2e")
        label = EMPRESA_LABELS.get(emp, emp)

        l = _g(leads_total, emp, a, m)
        l_ant = _g(leads_total, emp, a_ant, m_ant)
        # Criados no mes E convertidos (mesmo mes)
        cc = _g(leads_criados_e_conv, emp, a, m)
        cc_ant = _g(leads_criados_e_conv, emp, a_ant, m_ant)
        # Conversoes gerais do mes (qualquer lead convertido nesse mes)
        cm = _g(conv_no_mes, emp, a, m)
        cm_ant = _g(conv_no_mes, emp, a_ant, m_ant)
        ct = _g(contas_d, emp, a, m)
        ct_ant = _g(contas_d, emp, a_ant, m_ant)

        proj_l = int(l / du_atual * du_total) if du_atual > 0 else 0
        proj_cm = int(cm / du_atual * du_total) if du_atual > 0 else 0

        v_l = _var_html(l, du_atual, l_ant, du_ant)
        v_cm = _var_html(cm, du_atual, cm_ant, du_ant)
        v_cc = _var_html(cc, du_atual, cc_ant, du_ant)
        v_ct = _var_html(ct, du_atual, ct_ant, du_ant)

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
<span style="font-weight:700;color:{cor};font-size:1rem">{label}</span>
<span style="font-size:0.7rem;color:#999">vs {nome_ant} (por DU)</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:100px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#1a1a2e">{_fmt(l)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Leads Gerados</div>
<div>{v_l}</div>
</div>
<div style="flex:1;min-width:100px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#2E7D32">{_fmt(cm)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Conversoes no Mes</div>
<div>{v_cm}</div>
</div>
<div style="flex:1;min-width:100px;text-align:center;padding:6px 8px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#1565C0">{_fmt(cc)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Criados+Conv no Mes</div>
<div>{v_cc}</div>
</div>
<div style="flex:1;min-width:100px;text-align:center;padding:6px 8px">
<div style="font-size:1.3rem;font-weight:700;color:#555">{_fmt(ct)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Contas Criadas</div>
<div>{v_ct}</div>
</div>
</div>
<div style="font-size:0.7rem;color:#999;margin-top:6px;padding-top:6px;border-top:1px solid #f5f5f5">
Projecao: {_fmt(proj_l)} leads · {_fmt(proj_cm)} conversoes &nbsp;|&nbsp; {nome_ant}: {_fmt(l_ant)} leads · {_fmt(cm_ant)} conversoes
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

    tabela = []
    for (ano, mes) in meses:
        du = dias_uteis_no_mes(ano, mes)
        if empresa == "Todas":
            tl = sum(_g(leads_total, e, ano, mes) for e in EMPRESAS)
            t_cm = sum(_g(conv_no_mes, e, ano, mes) for e in EMPRESAS)
            t_cc = sum(_g(leads_criados_e_conv, e, ano, mes) for e in EMPRESAS)
            tt = sum(_g(contas_d, e, ano, mes) for e in EMPRESAS)
        else:
            tl = _g(leads_total, empresa, ano, mes)
            t_cm = _g(conv_no_mes, empresa, ano, mes)
            t_cc = _g(leads_criados_e_conv, empresa, ano, mes)
            tt = _g(contas_d, empresa, ano, mes)
        tabela.append({
            "Mes": f"{MESES_PT[mes]}/{ano}", "DU": du,
            "Leads": int(tl),
            "Conv. no Mes": int(t_cm),
            "Criados+Conv": int(t_cc),
            "Contas": int(tt),
            "Leads/DU": f"{tl/du:.0f}" if du > 0 else "\u2014",
        })
    st.dataframe(pd.DataFrame(tabela), width="stretch", hide_index=True)

    st.markdown("---")

    # ========================================
    # SECAO 3: DETALHAMENTO (filtro por periodo global)
    # ========================================
    st.markdown("### Detalhamento do Periodo")
    data_inicio = st.session_state.get("data_inicio")
    data_fim = st.session_state.get("data_fim")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### Funil de Status")
        df_st = get_leads_por_status(empresa, data_inicio, data_fim)
        if not df_st.empty:
            ordem = ["Aberto","Em Contato","Em Interacao","Transferencia Vendedor","Objecao Comercial","Aceite","Recuperacao","Stand-by Retrabalho","Fechado Convertido","Fechado Nao Convertido"]
            df_st["ord"] = df_st["Status"].map({s:i for i,s in enumerate(ordem)}).fillna(99)
            df_st = df_st.sort_values("ord")
            fig = px.bar(df_st, x="total", y="Status", orientation="h", text="total", color_discrete_sequence=["#1a1a2e"])
            fig.update_layout(yaxis_title="", xaxis_title="", height=400, showlegend=False, margin=dict(l=0,r=40,t=10,b=10))
            fig.update_traces(textposition="outside")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("#### Origens de Leads")
        df_or = get_leads_por_origem(empresa, data_inicio, data_fim)
        if not df_or.empty:
            df_or = df_or[df_or["LeadSource"].notna()].head(8)
            fig2 = px.bar(df_or, x="total", y="LeadSource", orientation="h", text="total", color_discrete_sequence=["#EC8500"])
            fig2.update_layout(yaxis_title="", xaxis_title="", height=400, showlegend=False, margin=dict(l=0,r=40,t=10,b=10))
            fig2.update_traces(textposition="outside")
            st.plotly_chart(fig2, use_container_width=True)

    col_l2, col_r2 = st.columns(2)

    with col_l2:
        st.markdown("#### Temperatura")
        df_rat = get_leads_por_rating(empresa, data_inicio, data_fim)
        if not df_rat.empty:
            df_rat = df_rat[df_rat["Rating"].notna()]
            cores_t = {"Congelado":"#4FC3F7","Frio":"#29B6F6","Morno":"#FFA726","Quente":"#EF5350","Muito Quente":"#C62828"}
            fig3 = px.pie(df_rat, names="Rating", values="total", color="Rating", color_discrete_map=cores_t)
            fig3.update_traces(textposition="inside", textinfo="percent+label+value")
            fig3.update_layout(height=350, margin=dict(t=10,b=10))
            st.plotly_chart(fig3, use_container_width=True)

    with col_r2:
        st.markdown("#### Motivos de Descarte")
        df_desc = get_leads_motivo_descarte(empresa, data_inicio, data_fim)
        if not df_desc.empty:
            df_d = df_desc.head(8).sort_values("total", ascending=True)
            fig4 = px.bar(df_d, x="total", y="Motivo_do_Descarte__c", orientation="h", text="total", color_discrete_sequence=["#C62828"])
            fig4.update_layout(yaxis_title="", xaxis_title="", height=350, showlegend=False, margin=dict(l=0,r=40,t=10,b=10))
            fig4.update_traces(textposition="outside")
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Leads por Proprietario (Top 20)")
    df_prop = get_leads_por_proprietario(empresa, data_inicio, data_fim)
    if not df_prop.empty:
        pivot = df_prop.pivot_table(index="Owner.Name", columns="Status", values="total", fill_value=0, aggfunc="sum").reset_index()
        pivot["Total"] = pivot.select_dtypes(include="number").sum(axis=1)
        pivot = pivot.sort_values("Total", ascending=False).head(20)
        st.dataframe(pivot, width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
