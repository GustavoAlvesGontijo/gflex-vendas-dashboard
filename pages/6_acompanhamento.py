"""
Pagina 5 - Acompanhamento (Diario / Semanal / Mensal / Custom)
Por empresa: leads criados, convertidos, opps criadas, movidas pra
negociacao, contratos, vendas. Filtro de origem opcional. Split
Licit/Outras para Flex Tendas. Flex Energy em kWh.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if not st.session_state.get("authenticated", False):
    st.warning("Acesse pela pagina principal para fazer login.")
    st.stop()
from styles import inject_css
inject_css()
import pandas as pd
from datetime import date, timedelta, datetime
from config import EMPRESAS, EMPRESA_LABELS, CORES, MESES_PT_FULL
from components import (
    page_header, section, icon, empresa_header, card_open, card_close,
)
from salesforce_client import (
    get_leads_criados_unificado,
    get_leads_convertidos_unificado,
    get_opps_criadas_unificado,
    get_opps_em_fase_unificado,
    get_opps_ganhas_unificado,
    get_energy_kwh_unificado,
)

# ============================================================
# Formatadores
# ============================================================
def _fmt(v):
    if v is None or pd.isna(v): return "—"
    return f"{int(v):,}".replace(",", ".")
def _fv(v):
    if not v or pd.isna(v) or v == 0: return "R$ 0"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    if not v or pd.isna(v) or v == 0: return "0 kWh"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"

# ============================================================
# Periodo
# ============================================================
ENERGY = "Flex Energy"
TENDAS = "Flex Tendas"
LICIT_SOURCE = "Licitacao"

st.markdown(page_header(
    title="Acompanhamento",
    subtitle="Vendas, opps e leads por empresa - diario, semanal, mensal ou periodo custom",
), unsafe_allow_html=True)

# Linha de filtros
c1, c2, c3, c4 = st.columns([1.2, 1.5, 1.5, 1.5])
hoje = date.today()

with c1:
    modo = st.selectbox("Periodo", ["Hoje", "Esta semana", "Este mes", "Mes passado", "Ultimos 7 dias", "Ultimos 30 dias", "Custom"], index=0, key="acomp_modo")

# Resolver datas baseado no modo
if modo == "Hoje":
    di = df = hoje
elif modo == "Esta semana":
    di = hoje - timedelta(days=hoje.weekday())  # segunda
    df = di + timedelta(days=6)
elif modo == "Este mes":
    di = date(hoje.year, hoje.month, 1)
    df = hoje
elif modo == "Mes passado":
    if hoje.month == 1:
        di = date(hoje.year - 1, 12, 1)
        df = date(hoje.year - 1, 12, 31)
    else:
        di = date(hoje.year, hoje.month - 1, 1)
        last_day = (date(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        df = date(hoje.year, hoje.month - 1, last_day)
elif modo == "Ultimos 7 dias":
    di = hoje - timedelta(days=6)
    df = hoje
elif modo == "Ultimos 30 dias":
    di = hoje - timedelta(days=29)
    df = hoje
else:  # Custom
    di = df = hoje  # placeholder, overwritten below

with c2:
    if modo == "Custom":
        di = st.date_input("Data inicio", value=hoje - timedelta(days=7), key="acomp_di")
    else:
        st.markdown(
            f'<div style="padding-top:30px"><span style="color:var(--text-muted);font-size:0.75rem">De:</span> '
            f'<b style="color:var(--text)">{di.strftime("%d/%m/%Y")}</b></div>',
            unsafe_allow_html=True,
        )

with c3:
    if modo == "Custom":
        df = st.date_input("Data fim", value=hoje, key="acomp_df")
    else:
        st.markdown(
            f'<div style="padding-top:30px"><span style="color:var(--text-muted);font-size:0.75rem">Ate:</span> '
            f'<b style="color:var(--text)">{df.strftime("%d/%m/%Y")}</b></div>',
            unsafe_allow_html=True,
        )

with c4:
    origem_filter = st.selectbox(
        "Filtrar leads por origem",
        ["Todas", "Meta ADS", "Google Ads", "Website", "Exact Sales", "Instagram", "Indicacao", "Feira", "Prospeccao Ativa Vendedor", "Licitacao"],
        index=0, key="acomp_orig",
    )

dias_periodo = (df - di).days + 1

# ============================================================
# Carregamento de dados (1 chamada por metrica, todas empresas)
# ============================================================
try:
    with st.spinner(f"Carregando dados de {di.strftime('%d/%m')} ate {df.strftime('%d/%m')}..."):
        df_lc = get_leads_criados_unificado(di, df)
        df_lconv = get_leads_convertidos_unificado(di, df)
        df_oc = get_opps_criadas_unificado(di, df)
        df_oneg = get_opps_em_fase_unificado(di, df, "Negociação")
        df_oct = get_opps_em_fase_unificado(di, df, "Contrato")
        df_og = get_opps_ganhas_unificado(di, df)
        # Energy kWh por modo
        kwh_criadas = get_energy_kwh_unificado(di, df, "criadas")
        kwh_negoc = get_energy_kwh_unificado(di, df, "negociacao")
        kwh_contr = get_energy_kwh_unificado(di, df, "contrato")
        kwh_ganhas = get_energy_kwh_unificado(di, df, "ganhas")

    # Aplicar filtro de origem (so afeta leads criados/convertidos conforme pedido)
    if origem_filter != "Todas":
        if not df_lc.empty:
            df_lc = df_lc[df_lc["LeadSource"] == origem_filter]
        if not df_lconv.empty:
            df_lconv = df_lconv[df_lconv["LeadSource"] == origem_filter]

    # Helpers de agregacao por empresa
    def _agg_qtd(df_in, col_total="total"):
        if df_in is None or df_in.empty: return {}
        return df_in.groupby("Empresa_Proprietaria__c")[col_total].sum().to_dict()

    def _agg_qtd_valor(df_in):
        if df_in is None or df_in.empty: return {}, {}
        g = df_in.groupby("Empresa_Proprietaria__c").agg({"total":"sum","valor":"sum"})
        return g["total"].to_dict(), g["valor"].to_dict()

    leads_criados_por_emp = _agg_qtd(df_lc)
    leads_conv_por_emp = _agg_qtd(df_lconv)
    opps_criadas_qtd, opps_criadas_val = _agg_qtd_valor(df_oc)
    neg_qtd, neg_val = _agg_qtd_valor(df_oneg)
    ct_qtd, ct_val = _agg_qtd_valor(df_oct)
    gan_qtd, gan_val = _agg_qtd_valor(df_og)

    # Top origens por empresa (so leads_criados, para tooltip)
    def _top_origens(df_in, emp, n=3):
        if df_in is None or df_in.empty: return []
        d = df_in[df_in["Empresa_Proprietaria__c"] == emp]
        if d.empty: return []
        d = d.groupby("LeadSource")["total"].sum().sort_values(ascending=False).head(n)
        return [(o, int(t)) for o, t in d.items() if o]

    # Energy kWh totais (filtra por origem se aplicavel)
    def _sum_kwh(df_kwh):
        if df_kwh is None or df_kwh.empty: return 0.0
        d = df_kwh
        if origem_filter != "Todas":
            d = d[d["origem"] == origem_filter]
        if d.empty: return 0.0
        return float(d["kwh"].sum())

    energy_kwh_criadas = _sum_kwh(kwh_criadas)
    energy_kwh_negoc = _sum_kwh(kwh_negoc)
    energy_kwh_contr = _sum_kwh(kwh_contr)
    energy_kwh_ganhas = _sum_kwh(kwh_ganhas)

    # ============================================================
    # Cabecalho com info do periodo
    # ============================================================
    periodo_label = (
        f"{di.strftime('%d/%m/%Y')}" if di == df
        else f"{di.strftime('%d/%m/%Y')} a {df.strftime('%d/%m/%Y')}"
    )
    filter_chip = (
        f' · <span style="display:inline-block;padding:2px 8px;background:#EC850018;color:#B45309;border-radius:5px;font-size:0.75rem;font-weight:700">Filtro: {origem_filter}</span>'
        if origem_filter != "Todas" else ""
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--bg-subtle);'
        f'border-radius:10px;margin-bottom:18px;font-size:0.88rem;color:var(--text-secondary)">'
        f'{icon("calendar", 16, "var(--accent)")} <b style="color:var(--text)">{periodo_label}</b> '
        f'<span style="color:var(--text-muted)">·</span> {dias_periodo} dia(s){filter_chip}</div>',
        unsafe_allow_html=True,
    )

    # ============================================================
    # Card por empresa com 6 mini-KPIs
    # ============================================================
    # cores das categorias (consistente com Hub)
    CORES_KPI = {
        "leads":       ("#3b82f6", "#3b82f614", "users",       "Leads criados"),
        "conv":        ("#10b981", "#10b98114", "target",      "Leads convertidos"),
        "opps":        ("#8b5cf6", "#8b5cf614", "file-text",   "Opps criadas"),
        "negociacao":  ("#f97316", "#f9731614", "flame",       "Em Negociacao"),
        "contrato":    ("#eab308", "#eab30814", "list-checks", "Contratos"),
        "vendas":      ("#059669", "#05966914", "trending-up", "Vendas"),
    }

    def _mini_kpi(key, value_str, sub_str="", small_extra=""):
        color, bg, ico_name, label = CORES_KPI[key]
        return (
            f'<div style="background:{bg};border-radius:10px;padding:11px 13px">'
            f'<div style="display:flex;align-items:center;gap:5px;font-size:0.58rem;color:{color};'
            f'text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:6px">'
            f'{icon(ico_name, 11, color)} {label}</div>'
            f'<div style="font-size:1.35rem;font-weight:800;color:{color};line-height:1;'
            f'font-feature-settings:\'tnum\';letter-spacing:-0.3px">{value_str}</div>'
            f'<div style="font-size:0.62rem;color:var(--text-secondary);margin-top:4px;line-height:1.3">{sub_str}</div>'
            f'{small_extra}'
            '</div>'
        )

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        ie = (emp == ENERGY)
        is_tendas = (emp == TENDAS)

        l_qtd = int(leads_criados_por_emp.get(emp, 0))
        c_qtd = int(leads_conv_por_emp.get(emp, 0))
        o_qtd = int(opps_criadas_qtd.get(emp, 0))
        o_val = float(opps_criadas_val.get(emp, 0))
        n_qtd = int(neg_qtd.get(emp, 0))
        n_val = float(neg_val.get(emp, 0))
        ct_q = int(ct_qtd.get(emp, 0))
        ct_v = float(ct_val.get(emp, 0))
        g_qtd = int(gan_qtd.get(emp, 0))
        g_val = float(gan_val.get(emp, 0))

        # Volume formatado: Energy em kWh, demais em R$
        if ie:
            v_opps = _fk(energy_kwh_criadas)
            v_neg = _fk(energy_kwh_negoc)
            v_ct = _fk(energy_kwh_contr)
            v_gan = _fk(energy_kwh_ganhas)
        else:
            v_opps = _fv(o_val)
            v_neg = _fv(n_val)
            v_ct = _fv(ct_v)
            v_gan = _fv(g_val)

        # Top origens (leads criados) — mostra so se filtro nao aplicado
        top_html = ""
        if origem_filter == "Todas":
            top = _top_origens(df_lc, emp, n=3)
            if top:
                top_html = '<div style="margin-top:6px;font-size:0.58rem;color:var(--text-muted);line-height:1.5">'
                for o, t in top:
                    top_html += f'<div>· {o}: <b>{t}</b></div>'
                top_html += '</div>'

        # Split Licit/Outras pra Flex Tendas
        lic_badge = ""
        sp_opps = sp_neg = sp_ct = sp_gan = sp_leads = sp_conv = ""
        if is_tendas and not df_lc.empty:
            # Filtrar por origem licitacao no df_lc/df_lconv/df_oc/df_oneg/df_oct/df_og
            def _emp_origem_qtd(df_in, e, origem):
                if df_in is None or df_in.empty: return 0
                d = df_in[(df_in["Empresa_Proprietaria__c"] == e) & (df_in["LeadSource"] == origem)]
                return int(d["total"].sum()) if not d.empty else 0
            def _emp_origem_valor(df_in, e, origem):
                if df_in is None or df_in.empty: return 0.0
                d = df_in[(df_in["Empresa_Proprietaria__c"] == e) & (df_in["LeadSource"] == origem)]
                return float(d["valor"].sum()) if not d.empty else 0.0

            lic_l = _emp_origem_qtd(df_lc, emp, LICIT_SOURCE)
            lic_conv = _emp_origem_qtd(df_lconv, emp, LICIT_SOURCE)
            lic_o_q = _emp_origem_qtd(df_oc, emp, LICIT_SOURCE)
            lic_o_v = _emp_origem_valor(df_oc, emp, LICIT_SOURCE)
            lic_n_q = _emp_origem_qtd(df_oneg, emp, LICIT_SOURCE)
            lic_n_v = _emp_origem_valor(df_oneg, emp, LICIT_SOURCE)
            lic_ct_q = _emp_origem_qtd(df_oct, emp, LICIT_SOURCE)
            lic_ct_v = _emp_origem_valor(df_oct, emp, LICIT_SOURCE)
            lic_g_q = _emp_origem_qtd(df_og, emp, LICIT_SOURCE)
            lic_g_v = _emp_origem_valor(df_og, emp, LICIT_SOURCE)

            def _split_html(total_q, lic_q, total_v=None, lic_v=None):
                out_q = max(0, total_q - lic_q)
                lines = (
                    f'<div style="color:#B45309">⚖ Licit.: {_fmt(lic_q)}</div>'
                    f'<div style="color:var(--text-muted)">Outras: {_fmt(out_q)}</div>'
                )
                if total_v is not None and lic_v is not None:
                    out_v = max(0, total_v - lic_v)
                    lines = (
                        f'<div style="color:#B45309">⚖ Licit.: {_fmt(lic_q)} · {_fv(lic_v)}</div>'
                        f'<div style="color:var(--text-muted)">Outras: {_fmt(out_q)} · {_fv(out_v)}</div>'
                    )
                return (
                    '<div style="margin-top:5px;font-size:0.55rem;font-weight:600;line-height:1.4">'
                    f'{lines}</div>'
                )

            sp_leads = _split_html(l_qtd, lic_l)
            sp_conv = _split_html(c_qtd, lic_conv)
            sp_opps = _split_html(o_qtd, lic_o_q, o_val, lic_o_v)
            sp_neg = _split_html(n_qtd, lic_n_q, n_val, lic_n_v)
            sp_ct = _split_html(ct_q, lic_ct_q, ct_v, lic_ct_v)
            sp_gan = _split_html(g_qtd, lic_g_q, g_val, lic_g_v)
            lic_badge = (
                '<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 10px;'
                'background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;color:#B45309;'
                f'font-size:0.62rem;font-weight:700;letter-spacing:0.4px">{icon("scale", 11, "#B45309")} '
                'SEGMENTADO LICITAÇÃO · OUTRAS</span>'
            )

        # Render do card
        html = card_open(cor)
        html += empresa_header(emp, badge_extra=lic_badge)
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:9px">'
        # 6 mini-KPIs
        html += _mini_kpi("leads", _fmt(l_qtd), f"{dias_periodo} dia(s)", top_html if not is_tendas else sp_leads)
        html += _mini_kpi("conv",  _fmt(c_qtd), f"convertidos no periodo", sp_conv)
        html += _mini_kpi("opps",  _fmt(o_qtd), f"orcadas · {v_opps}", sp_opps)
        html += _mini_kpi("negociacao", _fmt(n_qtd), f"em fase · {v_neg}", sp_neg)
        html += _mini_kpi("contrato", _fmt(ct_q), f"em fase · {v_ct}", sp_ct)
        html += _mini_kpi("vendas", _fmt(g_qtd), f"ganhas · {v_gan}", sp_gan)
        html += '</div>'
        # Nota explicativa pequena (so 1x, na primeira empresa)
        html += card_close()
        st.markdown(html, unsafe_allow_html=True)

    # Nota de aproximacao
    st.markdown(
        '<div style="margin-top:18px;padding:10px 14px;background:var(--bg-subtle);'
        'border-radius:8px;font-size:0.7rem;color:var(--text-muted);line-height:1.5">'
        '<b>Como interpretar:</b> Em Negociação / Contratos refletem opps <i>atualmente</i> '
        'naquela fase com mudança de fase no período (aproximação via LastStageChangeDate). '
        'Opps que já saíram da fase não aparecem. Para o universo exato seria necessário '
        'consultar OpportunityFieldHistory.'
        '</div>',
        unsafe_allow_html=True,
    )

except Exception as e:
    st.error(f"Erro carregando dados: {e}")
    import traceback
    st.code(traceback.format_exc())
