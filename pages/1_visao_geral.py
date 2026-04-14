"""
Pagina 1 — Visao Geral
Responde em segundos:
  1. Quanto ja vendemos esse mes em cada empresa?
  2. Estamos orcando mais ou menos que o trimestre passado?
  3. Qual origem de leads esta performando mais nesse mes em cada empresa?

Comparacao entre meses usa DIAS UTEIS (seg-sex sem feriados) para ser justa.
Cada empresa e comparada consigo mesma — nunca entre empresas diferentes.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    MESES_PT, MESES_PT_FULL,
)
from salesforce_client import (
    get_leads_mensal_por_empresa,
    get_contas_mensal_por_empresa,
    get_opps_mensal_por_empresa,
    get_opps_ganhas_mensal_por_empresa,
    get_leads_origem_mensal_por_empresa,
    get_os_mensal_por_empresa,
    get_energy_kwh_mensal,
    get_pipeline_aberto_por_empresa,
    get_opps_por_origem_empresa,
    get_origens_funil_por_empresa,
    get_leads_convertidos_no_mes_por_empresa,
)

# --- Helpers ---
def _fmt_num(v):
    if v is None or pd.isna(v):
        return "—"
    return f"{int(v):,}".replace(",", ".")

def _fmt_valor(v):
    if v is None or pd.isna(v) or v == 0:
        return "—"
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"

def _fmt_kwh(v):
    if v is None or pd.isna(v) or v == 0:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000:
        return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"

def _variacao_html(atual_por_du, anterior_por_du):
    """Retorna HTML da variacao baseada em valor/dia util."""
    if anterior_por_du == 0:
        if atual_por_du > 0:
            return '<span style="color:#2E7D32;font-size:0.8rem;font-weight:600">NOVO</span>'
        return ""
    pct = ((atual_por_du - anterior_por_du) / anterior_por_du) * 100
    if pct > 5:
        return f'<span style="color:#2E7D32;font-size:0.8rem;font-weight:600">+{pct:.0f}%</span>'
    elif pct < -5:
        return f'<span style="color:#C62828;font-size:0.8rem;font-weight:600">{pct:.0f}%</span>'
    return f'<span style="color:#888;font-size:0.8rem">{pct:+.0f}%</span>'

def _build_dict(df, value_col="total", filter_col=None, filter_val=None):
    """Constroi dict {(empresa, ano, mes): valor} a partir de DataFrame."""
    d = {}
    if df.empty:
        return d
    for _, row in df.iterrows():
        if filter_col and row.get(filter_col) != filter_val:
            continue
        emp = row.get("Empresa_Proprietaria__c", "")
        key = (emp, int(row["ano"]), int(row["mes"]))
        d[key] = d.get(key, 0) + (float(row[value_col]) if row[value_col] is not None and not pd.isna(row[value_col]) else 0)
    return d


# ==============================================
# HEADER
# ==============================================
hoje = date.today()
mes_atual = hoje.month
ano_atual = hoje.year
nome_mes = MESES_PT_FULL.get(mes_atual, "")

# Mes anterior
if mes_atual > 1:
    mes_ant, ano_ant = mes_atual - 1, ano_atual
else:
    mes_ant, ano_ant = 12, ano_atual - 1
nome_mes_ant = MESES_PT.get(mes_ant, "")

# Dias uteis
du_mes_total = dias_uteis_no_mes(ano_atual, mes_atual)
du_ate_hoje = dias_uteis_ate_hoje(ano_atual, mes_atual)
du_mes_ant = dias_uteis_no_mes(ano_ant, mes_ant)

# Trimestre atual e anterior
tri_atual = (mes_atual - 1) // 3 + 1
meses_tri_atual = [(ano_atual, m) for m in range((tri_atual - 1) * 3 + 1, min(tri_atual * 3 + 1, mes_atual + 1))]
if tri_atual > 1:
    tri_ant = tri_atual - 1
    ano_tri_ant = ano_atual
else:
    tri_ant = 4
    ano_tri_ant = ano_atual - 1
meses_tri_ant = [(ano_tri_ant, m) for m in range((tri_ant - 1) * 3 + 1, tri_ant * 3 + 1)]

st.markdown(f"""
<div style="background:#1a1a2e;padding:20px 28px;border-radius:14px;margin-bottom:24px">
    <h1 style="color:white;margin:0;font-size:1.6rem;font-weight:700">{nome_mes} {ano_atual}</h1>
    <div style="display:flex;gap:24px;margin-top:8px">
        <span style="color:#EC8500;font-size:0.85rem;font-weight:600">Dia {hoje.day} de {dias_uteis_no_mes(ano_atual, mes_atual)}</span>
        <span style="color:rgba(255,255,255,0.6);font-size:0.85rem">{du_ate_hoje} de {du_mes_total} dias uteis trabalhados</span>
        <span style="color:rgba(255,255,255,0.4);font-size:0.85rem">{nome_mes_ant} teve {du_mes_ant} dias uteis</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Barra de progresso
pct = (du_ate_hoje / du_mes_total * 100) if du_mes_total > 0 else 0
st.markdown(f"""
<div style="background:#e8e8e8;border-radius:6px;height:6px;margin:-12px 0 20px 0">
    <div style="background:linear-gradient(90deg,#EC8500,#F7C42D);border-radius:6px;height:6px;width:{pct:.0f}%"></div>
</div>
""", unsafe_allow_html=True)

try:
    # ==============================================
    # CARREGAR DADOS (6 queries, todas por empresa)
    # ==============================================
    df_leads = get_leads_mensal_por_empresa()
    df_contas = get_contas_mensal_por_empresa()
    df_opps = get_opps_mensal_por_empresa()
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_origens = get_leads_origem_mensal_por_empresa()
    df_os = get_os_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()
    df_conv_mes = get_leads_convertidos_no_mes_por_empresa()

    # Dicts: (empresa, ano, mes) -> valor
    leads_total = _build_dict(df_leads)
    leads_conv = _build_dict(df_leads, filter_col="IsConverted", filter_val=True)
    contas = _build_dict(df_contas)
    opps_qtd = _build_dict(df_opps)
    opps_val = _build_dict(df_opps, value_col="valor")
    ganhas_qtd = _build_dict(df_ganhas)
    ganhas_val = _build_dict(df_ganhas, value_col="valor")
    os_qtd = _build_dict(df_os)

    # Conversoes do mes (ConvertedDate)
    conv_no_mes = _build_dict(df_conv_mes)

    # kWh Energy: dict simples (ano, mes) -> kwh (sem empresa, so Energy)
    kwh_por_mes = {}
    if not df_kwh.empty:
        for _, row in df_kwh.iterrows():
            key = (int(row["ano"]), int(row["mes"]))
            kwh_por_mes[key] = kwh_por_mes.get(key, 0) + (float(row["total_kwh"]) if row["total_kwh"] else 0)

    def _get(d, emp, ano, mes):
        return d.get((emp, ano, mes), 0)

    def _get_tri(d, emp, meses_list):
        return sum(d.get((emp, a, m), 0) for a, m in meses_list)

    def _var_du(atual, du_atual, anterior, du_anterior):
        """Variacao percentual normalizada por dias uteis."""
        if du_atual == 0 or du_anterior == 0:
            return 0
        rate_atual = atual / du_atual
        rate_anterior = anterior / du_anterior
        if rate_anterior == 0:
            return 100 if rate_atual > 0 else 0
        return ((rate_atual - rate_anterior) / rate_anterior) * 100

    # ==============================================
    # PERGUNTA 1: Quanto ja vendemos esse mes em cada empresa?
    # ==============================================
    st.markdown("### Vendas no Mes — Por Empresa")
    st.caption("Cada empresa comparada consigo mesma no mes anterior (normalizado por dias uteis)")

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
        icone_map = {"Flex Energy": "\u26a1", "GF2 Solu\u00e7\u00f5es Integradas": "\U0001f529", "Flex Tendas": "\u26fa", "Flex Medi\u00e7\u00f5es": "\U0001f52c", "MEC Estruturas Met\u00e1licas": "\U0001f3d7\ufe0f", "Flex Solar": "\u2600\ufe0f"}
        icone = icone_map.get(emp, "\U0001f4ca")
        is_energy = (emp == "Flex Energy")

        # Dados mes atual
        g_qtd = _get(ganhas_qtd, emp, ano_atual, mes_atual)
        g_val = _get(ganhas_val, emp, ano_atual, mes_atual)
        l_qtd = _get(leads_total, emp, ano_atual, mes_atual)
        o_qtd = _get(opps_qtd, emp, ano_atual, mes_atual)

        # kWh para Energy
        if is_energy:
            kwh_atual = kwh_por_mes.get((ano_atual, mes_atual), 0)
            kwh_ant = kwh_por_mes.get((ano_ant, mes_ant), 0)

        # Dados mes anterior
        g_qtd_ant = _get(ganhas_qtd, emp, ano_ant, mes_ant)
        g_val_ant = _get(ganhas_val, emp, ano_ant, mes_ant)
        l_qtd_ant = _get(leads_total, emp, ano_ant, mes_ant)
        o_qtd_ant = _get(opps_qtd, emp, ano_ant, mes_ant)

        # Projecao (baseada em dias uteis)
        if du_ate_hoje > 0:
            proj_g_qtd = int(g_qtd / du_ate_hoje * du_mes_total)
            if is_energy:
                proj_vol = kwh_atual / du_ate_hoje * du_mes_total
            else:
                proj_vol = g_val / du_ate_hoje * du_mes_total
        else:
            proj_g_qtd = 0
            proj_vol = 0

        # Variacoes (normalizadas por DU)
        var_vendas_html = _variacao_html(g_qtd / max(du_ate_hoje, 1), g_qtd_ant / max(du_mes_ant, 1))
        var_leads_html = _variacao_html(l_qtd / max(du_ate_hoje, 1), l_qtd_ant / max(du_mes_ant, 1))
        var_opps_html = _variacao_html(o_qtd / max(du_ate_hoje, 1), o_qtd_ant / max(du_mes_ant, 1))

        # Volume: kWh para Energy, R$ para as demais
        if is_energy:
            vol_fmt = _fmt_kwh(kwh_atual)
            vol_label = "Energia Vendida"
            vol_ant_fmt = _fmt_kwh(kwh_ant)
            proj_vol_fmt = _fmt_kwh(proj_vol)
            var_vol_html = _variacao_html(kwh_atual / max(du_ate_hoje, 1), kwh_ant / max(du_mes_ant, 1))
            vol_color = "#EC8500"
        else:
            vol_fmt = _fmt_valor(g_val)
            vol_label = "Valor Fechado"
            vol_ant_fmt = _fmt_valor(g_val_ant)
            proj_vol_fmt = _fmt_valor(proj_vol)
            var_vol_html = _variacao_html(g_val / max(du_ate_hoje, 1), g_val_ant / max(du_mes_ant, 1))
            vol_color = "#2E7D32"

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:18px 24px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
<span style="font-size:1.1rem;font-weight:700;color:{cor}">{icone} {label}</span>
<span style="font-size:0.7rem;color:#999">vs {nome_mes_ant} (por dia util)</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:130px;text-align:center;padding:8px 12px;border-right:1px solid #f0f0f0">
<div style="font-size:1.5rem;font-weight:700;color:#1a1a2e">{_fmt_num(g_qtd)}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin:2px 0">Vendas</div>
<div>{var_vendas_html}</div>
</div>
<div style="flex:1;min-width:130px;text-align:center;padding:8px 12px;border-right:1px solid #f0f0f0">
<div style="font-size:1.5rem;font-weight:700;color:{vol_color}">{vol_fmt}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin:2px 0">{vol_label}</div>
<div>{var_vol_html}</div>
</div>
<div style="flex:1;min-width:130px;text-align:center;padding:8px 12px;border-right:1px solid #f0f0f0">
<div style="font-size:1.5rem;font-weight:700;color:#555">{_fmt_num(l_qtd)}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin:2px 0">Leads</div>
<div>{var_leads_html}</div>
</div>
<div style="flex:1;min-width:130px;text-align:center;padding:8px 12px">
<div style="font-size:1.5rem;font-weight:700;color:#555">{_fmt_num(o_qtd)}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin:2px 0">Oportunidades</div>
<div>{var_opps_html}</div>
</div>
</div>
<div style="margin-top:8px;padding-top:8px;border-top:1px solid #f5f5f5;font-size:0.7rem;color:#999">
Projecao: {_fmt_num(proj_g_qtd)} vendas · {proj_vol_fmt} &nbsp;|&nbsp; {nome_mes_ant}: {_fmt_num(g_qtd_ant)} vendas · {vol_ant_fmt}
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================
    # PERGUNTA 2: Orcando mais ou menos que trimestre passado?
    # ==============================================
    st.markdown(f"### Trimestre Atual (Q{tri_atual}) vs Anterior (Q{tri_ant})")
    st.caption("Total acumulado — cada empresa vs ela mesma")

    # Calcular DU dos trimestres
    du_tri_atual = sum(dias_uteis_no_mes(a, m) for a, m in meses_tri_atual)
    du_tri_ant = sum(dias_uteis_no_mes(a, m) for a, m in meses_tri_ant)

    tri_dados = []
    for emp in EMPRESAS:
        label = EMPRESA_LABELS[emp]
        g_tri_atual = _get_tri(ganhas_qtd, emp, meses_tri_atual)
        g_tri_ant = _get_tri(ganhas_qtd, emp, meses_tri_ant)
        gv_tri_atual = _get_tri(ganhas_val, emp, meses_tri_atual)
        gv_tri_ant = _get_tri(ganhas_val, emp, meses_tri_ant)
        o_tri_atual = _get_tri(opps_qtd, emp, meses_tri_atual)
        o_tri_ant = _get_tri(opps_qtd, emp, meses_tri_ant)
        l_tri_atual = _get_tri(leads_total, emp, meses_tri_atual)
        l_tri_ant = _get_tri(leads_total, emp, meses_tri_ant)

        var_g = _var_du(g_tri_atual, du_tri_atual, g_tri_ant, du_tri_ant)
        var_o = _var_du(o_tri_atual, du_tri_atual, o_tri_ant, du_tri_ant)

        tri_dados.append({
            "Empresa": label,
            f"Vendas Q{tri_atual}": int(g_tri_atual),
            f"Vendas Q{tri_ant}": int(g_tri_ant),
            "Var Vendas": f"{var_g:+.0f}%",
            f"Valor Q{tri_atual}": _fmt_valor(gv_tri_atual),
            f"Valor Q{tri_ant}": _fmt_valor(gv_tri_ant),
            f"Opps Q{tri_atual}": int(o_tri_atual),
            f"Opps Q{tri_ant}": int(o_tri_ant),
            "Var Opps": f"{var_o:+.0f}%",
            f"Leads Q{tri_atual}": int(l_tri_atual),
            f"Leads Q{tri_ant}": int(l_tri_ant),
        })

    df_tri = pd.DataFrame(tri_dados)
    st.dataframe(df_tri, width="stretch", hide_index=True)

    st.markdown("---")

    # ==============================================
    # PERGUNTA 3: Qual origem de leads performa mais nesse mes em cada empresa?
    # ==============================================
    st.markdown("### Top Origens de Leads — Mes Atual por Empresa")
    st.caption(f"{nome_mes}/{ano_atual} — ranking das origens que mais geram leads em cada empresa")

    if not df_origens.empty:
        df_or = df_origens.copy()
        df_or = df_or[(df_or["ano"] == ano_atual) & (df_or["mes"] == mes_atual)]
        df_or = df_or[df_or["LeadSource"].notna()]
        df_or = df_or[df_or["Empresa_Proprietaria__c"].isin(EMPRESAS)]

        for emp in EMPRESAS:
            cor = CORES[emp]["primaria"]
            label = EMPRESA_LABELS[emp]
            df_emp = df_or[df_or["Empresa_Proprietaria__c"] == emp].sort_values("total", ascending=False).head(5)

            if df_emp.empty:
                continue

            # Dados do mes anterior para comparar
            df_ant = df_origens.copy()
            df_ant = df_ant[(df_ant["ano"] == ano_ant) & (df_ant["mes"] == mes_ant)]
            df_ant = df_ant[df_ant["Empresa_Proprietaria__c"] == emp]
            df_ant = df_ant[df_ant["LeadSource"].notna()]
            ant_dict = dict(zip(df_ant["LeadSource"], df_ant["total"]))

            items_html = ""
            for _, row in df_emp.iterrows():
                origem = row["LeadSource"]
                qtd = int(row["total"])
                qtd_ant = ant_dict.get(origem, 0)
                var_html = _variacao_html(qtd / max(du_ate_hoje, 1), qtd_ant / max(du_mes_ant, 1))
                pct_total = (qtd / df_emp["total"].sum() * 100) if df_emp["total"].sum() > 0 else 0
                items_html += f'<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #f8f8f8"><div style="flex:2;font-size:0.85rem">{origem}</div><div style="flex:1;text-align:right;font-weight:600;font-size:0.9rem">{_fmt_num(qtd)}</div><div style="flex:1;text-align:right;font-size:0.75rem;color:#999">{pct_total:.0f}%</div><div style="flex:1;text-align:right">{var_html}</div></div>'

            header_html = f'<div style="display:flex;padding:2px 0;border-bottom:2px solid #eee;margin-bottom:4px"><div style="flex:2;font-size:0.65rem;color:#999;text-transform:uppercase">Origem</div><div style="flex:1;text-align:right;font-size:0.65rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.65rem;color:#999;text-transform:uppercase">%</div><div style="flex:1;text-align:right;font-size:0.65rem;color:#999;text-transform:uppercase">vs {nome_mes_ant}</div></div>'
            card_html = f'<div style="background:white;border-radius:10px;padding:14px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:3px solid {cor}"><div style="font-weight:700;color:{cor};margin-bottom:8px;font-size:0.95rem">{label}</div>{header_html}{items_html}</div>'
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================
    # PIPELINE ABERTO — Quanto cada empresa tem em negociacao
    # ==============================================
    st.markdown("### Pipeline Aberto — Em Negociacao e Contrato")
    st.caption("Oportunidades que ainda nao fecharam (ganho ou perdido) — valor acumulado no pipeline")

    df_pipe = get_pipeline_aberto_por_empresa()
    if not df_pipe.empty:
        df_pipe = df_pipe[df_pipe["Empresa_Proprietaria__c"].isin(EMPRESAS)]
        fases_ativas = ["Negociacao", "Contrato", "Em Cotacao"]
        fases_prospeccao = ["Novo", "Em Analise", "Contato Ativo", "Contato Passivo"]

        for emp in EMPRESAS:
            cor = CORES[emp]["primaria"]
            label = EMPRESA_LABELS[emp]
            df_e = df_pipe[df_pipe["Empresa_Proprietaria__c"] == emp]
            if df_e.empty:
                continue

            is_energy = (emp == "Flex Energy")
            total_pipe = int(df_e["total"].sum())
            total_valor = df_e["valor"].sum()

            # Separar fases quentes vs frias
            df_quente = df_e[df_e["StageName"].isin(fases_ativas)]
            df_fria = df_e[df_e["StageName"].isin(fases_prospeccao)]
            qtd_quente = int(df_quente["total"].sum())
            val_quente = df_quente["valor"].sum()
            qtd_fria = int(df_fria["total"].sum())
            val_fria = df_fria["valor"].sum()

            # Montar itens por fase
            fases_html = ""
            for _, row in df_e.sort_values("total", ascending=False).iterrows():
                fase = row["StageName"]
                qtd = int(row["total"])
                val = row["valor"] if row["valor"] else 0
                val_fmt = _fmt_kwh(val) if is_energy else _fmt_valor(val)
                fases_html += f'<div style="display:flex;padding:3px 0;border-bottom:1px solid #f8f8f8"><div style="flex:2;font-size:0.8rem">{fase}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt_num(qtd)}</div><div style="flex:1;text-align:right;color:#666">{val_fmt}</div></div>'

            val_total_fmt = _fmt_kwh(total_valor) if is_energy else _fmt_valor(total_valor)
            val_quente_fmt = _fmt_kwh(val_quente) if is_energy else _fmt_valor(val_quente)
            unidade = "kWh" if is_energy else "R$"

            st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<span style="font-weight:700;color:{cor};font-size:1rem">{label}</span>
<span style="font-size:0.85rem;font-weight:600;color:#1a1a2e">{_fmt_num(total_pipe)} opps · {val_total_fmt}</span>
</div>
<div style="display:flex;gap:16px;margin-bottom:8px">
<div style="background:#FFF3E0;border-radius:8px;padding:8px 14px;flex:1;text-align:center">
<div style="font-size:1.1rem;font-weight:700;color:#E65100">{_fmt_num(qtd_quente)}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase">Quentes ({val_quente_fmt})</div>
</div>
<div style="background:#E3F2FD;border-radius:8px;padding:8px 14px;flex:1;text-align:center">
<div style="font-size:1.1rem;font-weight:700;color:#1565C0">{_fmt_num(qtd_fria)}</div>
<div style="font-size:0.6rem;color:#888;text-transform:uppercase">Prospeccao</div>
</div>
</div>
<div style="display:flex;padding:2px 0;border-bottom:2px solid #eee;margin-bottom:2px"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Fase</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">{unidade}</div></div>
{fases_html}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================
    # COMBUSTIVEIS — Performance de Origens/Ads
    # ==============================================
    st.markdown("### Combustiveis — Performance por Origem")
    st.caption("De onde vem os leads, quantos orcam e quantos vendem — por empresa e por canal")

    ORIGENS_ADS = ["Meta ADS", "Google Ads", "Website", "Exact Sales", "Instagram", "Indicacao", "Feira", "Prospeccao Ativa Vendedor"]

    data_inicio_mes = date(ano_atual, mes_atual, 1)
    df_leads_origem = get_origens_funil_por_empresa(data_inicio_mes, hoje)
    df_opps_origem = get_opps_por_origem_empresa(data_inicio_mes, hoje)

    if not df_leads_origem.empty and not df_opps_origem.empty:
        for emp in EMPRESAS:
            cor = CORES[emp]["primaria"]
            label = EMPRESA_LABELS[emp]

            # Leads por origem
            df_l = df_leads_origem[df_leads_origem["Empresa_Proprietaria__c"] == emp]
            if df_l.empty:
                continue

            leads_por_or = df_l.groupby("LeadSource")["total"].sum().to_dict()
            conv_por_or = df_l[df_l["IsConverted"] == True].groupby("LeadSource")["total"].sum().to_dict()

            # Opps por origem
            df_o = df_opps_origem[df_opps_origem["Empresa_Proprietaria__c"] == emp]
            opps_por_or = df_o.groupby("LeadSource")["total"].sum().to_dict()
            ganhas_or = df_o[df_o["StageName"] == "Fechado Ganho"].groupby("LeadSource")["total"].sum().to_dict()
            valor_or = df_o[df_o["StageName"] == "Fechado Ganho"].groupby("LeadSource")["valor"].sum().to_dict()

            # Filtrar apenas origens com dados
            origens_com_dados = [o for o in ORIGENS_ADS if leads_por_or.get(o, 0) > 0 or opps_por_or.get(o, 0) > 0]
            if not origens_com_dados:
                continue

            is_energy = (emp == "Flex Energy")

            rows_html = ""
            for origem in origens_com_dados:
                n_leads = int(leads_por_or.get(origem, 0))
                n_conv = int(conv_por_or.get(origem, 0))
                n_opps = int(opps_por_or.get(origem, 0))
                n_ganhas = int(ganhas_or.get(origem, 0))
                val = valor_or.get(origem, 0)
                val_fmt = _fmt_kwh(val) if is_energy else _fmt_valor(val)
                taxa = f"{(n_ganhas/n_opps*100):.0f}%" if n_opps > 0 else "—"

                # Cor do status
                if n_ganhas > 0:
                    status_cor = "#2E7D32"
                elif n_opps > 0:
                    status_cor = "#1565C0"
                else:
                    status_cor = "#999"

                rows_html += f'<div style="display:flex;align-items:center;padding:4px 0;border-bottom:1px solid #f5f5f5"><div style="flex:2;font-size:0.8rem">{origem}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt_num(n_leads)}</div><div style="flex:1;text-align:right;color:#1565C0">{_fmt_num(n_opps)}</div><div style="flex:1;text-align:right;color:{status_cor};font-weight:600">{_fmt_num(n_ganhas)}</div><div style="flex:1;text-align:right;color:#666;font-size:0.8rem">{val_fmt}</div><div style="flex:1;text-align:right;font-size:0.75rem">{taxa}</div></div>'

            unidade = "kWh" if is_energy else "R$"
            header_html = f'<div style="display:flex;padding:2px 0;border-bottom:2px solid #eee;margin-bottom:2px"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Origem</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Leads</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Orcaram</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Venderam</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">{unidade}</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Win%</div></div>'

            st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:3px solid {cor}">
<div style="font-weight:700;color:{cor};margin-bottom:8px;font-size:0.95rem">{label} — {nome_mes}/{ano_atual}</div>
{header_html}{rows_html}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================
    # EVOLUCAO MES A MES (tabela limpa)
    # ==============================================
    st.markdown("### Evolucao Mes a Mes (todas as empresas somadas)")

    meses_exibir = []
    m, a = mes_atual, ano_atual
    for _ in range(6):
        meses_exibir.append((a, m))
        m -= 1
        if m == 0:
            m = 12
            a -= 1
    meses_exibir.reverse()

    tabela = []
    for (ano, mes) in meses_exibir:
        du = dias_uteis_no_mes(ano, mes)
        l = sum(_get(leads_total, e, ano, mes) for e in EMPRESAS)
        cv = sum(_get(leads_conv, e, ano, mes) for e in EMPRESAS)
        ct = sum(_get(contas, e, ano, mes) for e in EMPRESAS)
        oq = sum(_get(opps_qtd, e, ano, mes) for e in EMPRESAS)
        ov = sum(_get(opps_val, e, ano, mes) for e in EMPRESAS)
        gq = sum(_get(ganhas_qtd, e, ano, mes) for e in EMPRESAS)
        gv = sum(_get(ganhas_val, e, ano, mes) for e in EMPRESAS)

        tabela.append({
            "Mes": f"{MESES_PT[mes]}/{ano}",
            "DU": du,
            "Leads": int(l),
            "Convertidos": int(cv),
            "Contas": int(ct),
            "Opps": int(oq),
            "Opps (R$)": _fmt_valor(ov),
            "Ganhas": int(gq),
            "Ganhas (R$)": _fmt_valor(gv),
        })

    st.dataframe(pd.DataFrame(tabela), width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    import traceback
    st.code(traceback.format_exc())
