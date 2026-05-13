"""
Pagina 1 — Visao Geral
Cards Hub-like por empresa: Vendido / Negociacao+Contrato / Pipeline Total.
Combustiveis com soma. Evolucao mes a mes por empresa.
Split Licitacao/Outras nos cards da Flex Tendas (LeadSource='Licitacao').
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
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    MESES_PT, MESES_PT_FULL, get_logo_b64,
)
from components import (
    var_badge, empresa_header, kpi_block, card_open, card_close,
    split_lines, page_header, section, icon,
)
from salesforce_client import (
    get_leads_mensal_por_empresa,
    get_opps_mensal_por_empresa,
    get_opps_ganhas_mensal_por_empresa,
    get_energy_kwh_mensal,
    get_pipeline_aberto_por_empresa,
    get_energy_pipeline_kwh,
    get_opps_por_origem_empresa,
    get_origens_funil_por_empresa,
    get_leads_convertidos_no_mes_por_empresa,
    get_flex_tendas_licitacao_opps_mensal,
    get_flex_tendas_licitacao_ganhas_mensal,
    get_flex_tendas_licitacao_pipeline,
    get_flex_tendas_licitacao_leads_mensal,
)

# ============================================================
# Helpers de formatacao
# ============================================================
def _fmt(v):
    if v is None or pd.isna(v): return "—"
    return f"{int(v):,}".replace(",", ".")
def _fv(v):
    if not v or pd.isna(v) or v == 0: return "—"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    if not v or pd.isna(v) or v == 0: return "—"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"
def _var_pct(atual, du_a, anterior, du_b):
    """Retorna a variacao percentual (None se nao calculavel)."""
    if du_a == 0 or du_b == 0 or anterior == 0:
        return None
    return ((atual/du_a - anterior/du_b) / (anterior/du_b)) * 100
def _bd(df, val="total"):
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
        d[k] = d.get(k,0) + (float(r[val]) if r[val] is not None and not pd.isna(r[val]) else 0)
    return d
def _bd_lic(df, val="total"):
    """Constroi {(ano,mes): valor} a partir de DF da Licitacao (so Flex Tendas)."""
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        k = (int(r["ano"]), int(r["mes"]))
        v = r[val]
        d[k] = float(v) if v is not None and not pd.isna(v) else 0
    return d
def _g(d, e, a, m): return d.get((e,a,m), 0)

# ============================================================
# Periodo
# ============================================================
hoje = date.today()
m, a = hoje.month, hoje.year
m_a, a_a = (m-1, a) if m > 1 else (12, a-1)
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_a, m_a)
n_ant = MESES_PT[m_a]

# Header com gradient + barra de progresso DU
pct = (du_h/du_t*100) if du_t > 0 else 0
st.markdown(page_header(
    title=f"{MESES_PT_FULL.get(m,'')} {a}",
    subtitle=f"<span style='color:#F7C42D;font-weight:600'>{du_h} de {du_t} dias uteis</span> · {n_ant} teve {du_ant} DU",
    status_bar_pct=pct,
), unsafe_allow_html=True)

# ============================================================
# Carregamento de dados
# ============================================================
try:
    df_leads = get_leads_mensal_por_empresa()
    df_opps = get_opps_mensal_por_empresa()
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()
    df_pipe = get_pipeline_aberto_por_empresa()
    df_conv = get_leads_convertidos_no_mes_por_empresa()

    leads_t = _bd(df_leads)
    opps_q = _bd(df_opps)
    opps_v = _bd(df_opps, "valor")
    ganhas_q = _bd(df_ganhas)
    ganhas_v = _bd(df_ganhas, "valor")
    conv_m = _bd(df_conv)
    kwh_m = {}
    if not df_kwh.empty:
        for _, r in df_kwh.iterrows():
            kwh_m[(int(r["ano"]),int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0

    # Pipeline Energy kWh (via OpportunityLineItem)
    energy_pipe_kwh = get_energy_pipeline_kwh()
    energy_pipe_kwh_total = sum(energy_pipe_kwh.values())
    energy_pipe_kwh_neg = sum(v for k, v in energy_pipe_kwh.items() if k in ["Negociação", "Contrato"])

    # Pipeline aberto por empresa — negociacao/contrato vs total
    pipe_neg, pipe_neg_val, pipe_total, pipe_total_val = {}, {}, {}, {}
    if not df_pipe.empty:
        fases_neg = ["Negociação", "Contrato"]
        for _, r in df_pipe.iterrows():
            e = r.get("Empresa_Proprietaria__c","")
            qtd = int(r["total"])
            val = float(r["valor"]) if (r["valor"] is not None and not pd.isna(r["valor"])) else 0
            pipe_total[e] = pipe_total.get(e,0) + qtd
            pipe_total_val[e] = pipe_total_val.get(e,0) + val
            if r["StageName"] in fases_neg:
                pipe_neg[e] = pipe_neg.get(e,0) + qtd
                pipe_neg_val[e] = pipe_neg_val.get(e,0) + val

    # Licitacao — slice especial Flex Tendas
    lic_opps_q = _bd_lic(get_flex_tendas_licitacao_opps_mensal(), "total")
    lic_opps_v = _bd_lic(get_flex_tendas_licitacao_opps_mensal(), "valor")
    lic_gan_q = _bd_lic(get_flex_tendas_licitacao_ganhas_mensal(), "total")
    lic_gan_v = _bd_lic(get_flex_tendas_licitacao_ganhas_mensal(), "valor")
    lic_leads_q = _bd_lic(get_flex_tendas_licitacao_leads_mensal(), "total")

    df_lic_pipe = get_flex_tendas_licitacao_pipeline()
    lic_pipe_q = lic_pipe_v = lic_neg_q = lic_neg_v = 0
    if not df_lic_pipe.empty:
        for _, r in df_lic_pipe.iterrows():
            qtd = int(r["total"]); val = float(r["valor"]) if (r["valor"] is not None and not pd.isna(r["valor"])) else 0
            lic_pipe_q += qtd; lic_pipe_v += val
            if r["StageName"] in ["Negociação", "Contrato"]:
                lic_neg_q += qtd; lic_neg_v += val

    # ============================================================
    # SECAO 1: VENDAS + PIPELINE por empresa
    # ============================================================
    st.markdown(section(
        title=f"VENDAS + PIPELINE — {MESES_PT[m].upper()}/{a}",
        subtitle=f"O que ja vendemos, o que esta em negociacao e o pipeline total — cada empresa vs {n_ant} (por dia util)",
        icon_name="chart",
    ), unsafe_allow_html=True)

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        ie = (emp == "Flex Energy")
        is_tendas = (emp == "Flex Tendas")

        gq = _g(ganhas_q, emp, a, m); gq_a = _g(ganhas_q, emp, a_a, m_a)
        gv = _g(ganhas_v, emp, a, m); gv_a = _g(ganhas_v, emp, a_a, m_a)
        lq = _g(leads_t, emp, a, m); lq_a = _g(leads_t, emp, a_a, m_a)
        oq = _g(opps_q, emp, a, m); oq_a = _g(opps_q, emp, a_a, m_a)

        pn = pipe_neg.get(emp, 0); pnv = pipe_neg_val.get(emp, 0)
        pt = pipe_total.get(emp, 0); ptv = pipe_total_val.get(emp, 0)

        # Volume vendido + pipeline (Energy em kWh; demais R$)
        if ie:
            kh = kwh_m.get((a,m),0); kh_a = kwh_m.get((a_a,m_a),0)
            vol = _fk(kh); vol_lab = "Energia"
            v_vol_pct = _var_pct(kh, du_h, kh_a, du_ant)
            neg_vol = _fk(energy_pipe_kwh_neg); pipe_vol = _fk(energy_pipe_kwh_total)
        else:
            vol = _fv(gv); vol_lab = "Valor"
            v_vol_pct = _var_pct(gv, du_h, gv_a, du_ant)
            neg_vol = _fv(pnv); pipe_vol = _fv(ptv)

        v_gq_pct = _var_pct(gq, du_h, gq_a, du_ant)
        v_lq_pct = _var_pct(lq, du_h, lq_a, du_ant)
        v_oq_pct = _var_pct(oq, du_h, oq_a, du_ant)
        v_orc_pct = _var_pct(oq, du_h, oq_a, du_ant)

        # Sub-linhas Licitacao/Outras (so Flex Tendas)
        lic_v_q = lic_gan_q.get((a,m), 0); lic_v_v = lic_gan_v.get((a,m), 0)
        lic_o_q = lic_opps_q.get((a,m), 0); lic_o_v = lic_opps_v.get((a,m), 0)
        lic_l_q = lic_leads_q.get((a,m), 0)
        out_v_q = max(0, gq - lic_v_q); out_v_v = max(0, gv - lic_v_v)
        out_o_q = max(0, oq - lic_o_q); out_o_v = max(0, oq * 0)  # placeholder
        out_neg_q = max(0, pn - lic_neg_q); out_neg_v = max(0, pnv - lic_neg_v)
        out_pipe_q = max(0, pt - lic_pipe_q); out_pipe_v = max(0, ptv - lic_pipe_v)
        out_l_q = max(0, lq - lic_l_q)
        out_orc_q = max(0, oq - lic_o_q)

        sp_vend_qtd = split_lines("⚖ Licit.", _fmt(lic_v_q), "Outras", _fmt(out_v_q), is_tendas)
        sp_vend_val = split_lines("⚖ Licit.", _fv(lic_v_v), "Outras", _fv(out_v_v), is_tendas)
        sp_neg_qtd = split_lines("⚖ Licit.", _fmt(lic_neg_q), "Outras", _fmt(out_neg_q), is_tendas)
        sp_neg_val = split_lines("⚖ Licit.", _fv(lic_neg_v), "Outras", _fv(out_neg_v), is_tendas)
        sp_pipe_qtd = split_lines("⚖ Licit.", _fmt(lic_pipe_q), "Outras", _fmt(out_pipe_q), is_tendas)
        sp_pipe_val = split_lines("⚖ Licit.", _fv(lic_pipe_v), "Outras", _fv(out_pipe_v), is_tendas)
        sp_lead = split_lines("⚖ Licit.", _fmt(lic_l_q), "Outras", _fmt(out_l_q), is_tendas)
        sp_orc = split_lines("⚖ Licit.", _fmt(lic_o_q), "Outras", _fmt(out_orc_q), is_tendas)

        # Badge no header — só Flex Tendas
        lic_badge = (
            '<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 10px;'
            'background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;color:#B45309;'
            f'font-size:0.65rem;font-weight:700;letter-spacing:0.4px">{icon("scale", 11, "#B45309")} '
            'SEGMENTADO LICITAÇÃO · OUTRAS</span>'
        ) if is_tendas else ""

        # Bloco completo: card_open + header + 3 KPIs + linha extra + card_close
        html = card_open(cor)
        html += empresa_header(emp, badge_extra=lic_badge)
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-bottom:12px">'
        html += kpi_block(
            label="Vendido no Mes", primary_value=_fmt(gq), primary_caption="vendas",
            secondary_value=vol, secondary_caption=vol_lab,
            accent="#059669", tint_bg="#10b98116", icon_name="target",
            primary_extra=f'<div style="margin-top:4px">{var_badge(v_gq_pct)}</div>{sp_vend_qtd}',
            secondary_extra=f'<div style="margin-top:4px">{var_badge(v_vol_pct)}</div>{sp_vend_val}',
        )
        html += kpi_block(
            label="Negociacao + Contrato", primary_value=_fmt(pn), primary_caption="opps quentes",
            secondary_value=neg_vol, secondary_caption=vol_lab,
            accent="#E65100", tint_bg="#f9731614", icon_name="flame",
            primary_extra=sp_neg_qtd, secondary_extra=sp_neg_val,
        )
        html += kpi_block(
            label="Pipeline Total", primary_value=_fmt(pt), primary_caption="opps abertas",
            secondary_value=pipe_vol, secondary_caption=vol_lab,
            accent="#1565C0", tint_bg="#3b82f614", icon_name="list-checks",
            primary_extra=sp_pipe_qtd, secondary_extra=sp_pipe_val,
        )
        html += '</div>'
        # Linha extra: leads + orcamentos (sem tint, mais leve)
        html += (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding-top:10px;border-top:1px solid var(--border)">'
            '<div>'
            f'<div style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;font-weight:700;letter-spacing:0.4px;margin-bottom:4px">Leads</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px"><span style="font-size:1.25rem;font-weight:700;color:var(--text);font-feature-settings:\'tnum\'">{_fmt(lq)}</span>{var_badge(v_lq_pct)}</div>'
            f'{sp_lead}'
            '</div>'
            '<div>'
            f'<div style="font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;font-weight:700;letter-spacing:0.4px;margin-bottom:4px">Orcamentos</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px"><span style="font-size:1.25rem;font-weight:700;color:var(--text);font-feature-settings:\'tnum\'">{_fmt(oq)}</span>{var_badge(v_oq_pct)}</div>'
            f'{sp_orc}'
            '</div>'
            '</div>'
        )
        html += card_close()
        st.markdown(html, unsafe_allow_html=True)

    # ============================================================
    # SECAO 2: COMBUSTIVEIS com soma
    # ============================================================
    st.markdown(section(
        title="COMBUSTIVEIS — Performance por Origem",
        subtitle=f"De onde vem os leads e quantos viram orcamento e venda — {MESES_PT[m]}/{a}",
        icon_name="fuel",
    ), unsafe_allow_html=True)

    ORIGENS = ["Meta ADS","Google Ads","Website","Exact Sales","Instagram","Indicacao","Feira","Prospeccao Ativa Vendedor"]
    d_ini = date(a, m, 1)
    df_lo = get_origens_funil_por_empresa(d_ini, hoje)
    df_oo = get_opps_por_origem_empresa(d_ini, hoje)

    if not df_lo.empty and not df_oo.empty:
        for emp in EMPRESAS:
            cor = CORES[emp]["primaria"]
            ie = (emp == "Flex Energy")
            df_l = df_lo[df_lo["Empresa_Proprietaria__c"]==emp]
            if df_l.empty: continue
            l_or = df_l.groupby("LeadSource")["total"].sum().to_dict()
            df_o = df_oo[df_oo["Empresa_Proprietaria__c"]==emp]
            o_or = df_o.groupby("LeadSource")["total"].sum().to_dict()
            g_or = df_o[df_o["StageName"]=="Fechado Ganho"].groupby("LeadSource")["total"].sum().to_dict()
            v_or = df_o[df_o["StageName"]=="Fechado Ganho"].groupby("LeadSource")["valor"].sum().to_dict()

            origens_cd = [o for o in ORIGENS if l_or.get(o,0)>0 or o_or.get(o,0)>0]
            extras = [o for o in (set(l_or)|set(o_or)) if o and o not in origens_cd]
            origens_cd = origens_cd + extras
            if not origens_cd: continue

            unid = "kWh" if ie else "R$"
            rows = ""
            sum_l = sum_o = sum_g = 0; sum_v = 0.0
            for orig in origens_cd:
                nl = int(l_or.get(orig,0)); no = int(o_or.get(orig,0))
                ng = int(g_or.get(orig,0)); nv = v_or.get(orig,0) or 0
                sum_l += nl; sum_o += no; sum_g += ng; sum_v += nv
                vf = _fk(nv) if ie else _fv(nv)
                tx = f"{(ng/no*100):.0f}%" if no > 0 else "—"
                sc = "#059669" if ng > 0 else "var(--text-muted)"
                rows += (
                    '<tr>'
                    f'<td style="padding:7px 10px;font-size:0.82rem;color:var(--text)">{orig}</td>'
                    f'<td style="padding:7px 10px;text-align:right;font-weight:600;color:var(--text);font-feature-settings:\'tnum\'">{_fmt(nl)}</td>'
                    f'<td style="padding:7px 10px;text-align:right;color:#1565C0;font-weight:600;font-feature-settings:\'tnum\'">{_fmt(no)}</td>'
                    f'<td style="padding:7px 10px;text-align:right;color:{sc};font-weight:700;font-feature-settings:\'tnum\'">{_fmt(ng)}</td>'
                    f'<td style="padding:7px 10px;text-align:right;color:var(--text-secondary);font-size:0.82rem;font-feature-settings:\'tnum\'">{vf}</td>'
                    f'<td style="padding:7px 10px;text-align:right;font-size:0.78rem;color:var(--text-secondary)">{tx}</td>'
                    '</tr>'
                )

            svf = _fk(sum_v) if ie else _fv(sum_v)
            stx = f"{(sum_g/sum_o*100):.0f}%" if sum_o > 0 else "—"
            rows += (
                '<tr style="border-top:2px solid var(--border-strong);font-weight:700">'
                '<td style="padding:8px 10px;font-size:0.82rem;color:var(--text)">TOTAL</td>'
                f'<td style="padding:8px 10px;text-align:right;color:var(--text);font-feature-settings:\'tnum\'">{_fmt(sum_l)}</td>'
                f'<td style="padding:8px 10px;text-align:right;color:#1565C0;font-feature-settings:\'tnum\'">{_fmt(sum_o)}</td>'
                f'<td style="padding:8px 10px;text-align:right;color:#059669;font-feature-settings:\'tnum\'">{_fmt(sum_g)}</td>'
                f'<td style="padding:8px 10px;text-align:right;color:var(--text-secondary);font-feature-settings:\'tnum\'">{svf}</td>'
                f'<td style="padding:8px 10px;text-align:right;color:var(--text)">{stx}</td>'
                '</tr>'
            )

            hdr = (
                '<thead><tr style="border-bottom:2px solid var(--border)">'
                '<th style="padding:6px 10px;text-align:left;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">Origem</th>'
                '<th style="padding:6px 10px;text-align:right;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">Leads</th>'
                '<th style="padding:6px 10px;text-align:right;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">Orcaram</th>'
                '<th style="padding:6px 10px;text-align:right;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">Venderam</th>'
                f'<th style="padding:6px 10px;text-align:right;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">{unid}</th>'
                '<th style="padding:6px 10px;text-align:right;font-size:0.6rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;font-weight:700">Win%</th>'
                '</tr></thead>'
            )
            html = card_open(cor)
            html += empresa_header(emp)
            html += f'<table style="width:100%;border-collapse:collapse">{hdr}<tbody>{rows}</tbody></table>'
            html += card_close()
            st.markdown(html, unsafe_allow_html=True)

    # ============================================================
    # SECAO 3: EVOLUCAO MES A MES
    # ============================================================
    st.markdown(section(
        title="EVOLUCAO MES A MES",
        subtitle="Historico dos ultimos 6 meses — leads, conversoes, orcamentos e vendas por empresa",
        icon_name="calendar",
    ), unsafe_allow_html=True)

    meses_ex = []
    mx, ax = m, a
    for _ in range(6):
        meses_ex.append((ax, mx))
        mx -= 1
        if mx == 0: mx, ax = 12, ax-1
    meses_ex.reverse()

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        ie = (emp == "Flex Energy")
        tab = []
        for (ano, mes) in meses_ex:
            du = dias_uteis_no_mes(ano, mes)
            lq = _g(leads_t, emp, ano, mes)
            cm = _g(conv_m, emp, ano, mes)
            oq = _g(opps_q, emp, ano, mes)
            gq = _g(ganhas_q, emp, ano, mes)
            gv = _g(ganhas_v, emp, ano, mes)
            vol = _fk(kwh_m.get((ano,mes),0)) if ie else _fv(gv)
            tab.append({"Mes": f"{MESES_PT[mes]}/{ano}", "DU": du, "Leads": int(lq), "Conv": int(cm), "Orcs": int(oq), "Vendas": int(gq), "Volume": vol})
        st.markdown(empresa_header(emp), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
