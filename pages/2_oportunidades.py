"""
Pagina 2 — Oportunidades
Card por empresa + pipeline detalhado abaixo de cada card.
Evolucao mes a mes por empresa. Sem detalhamento de periodo nem engajamento.
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
    EMPRESAS, EMPRESA_LABELS, CORES, FASES_PIPELINE,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT, get_logo_b64,
)
from salesforce_client import (
    get_opps_mensal_por_empresa, get_opps_ganhas_mensal_por_empresa,
    get_energy_kwh_mensal, get_energy_kwh_orcado_mensal,
    get_pipeline_aberto_por_empresa, get_energy_pipeline_kwh,
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
def _var(atual, du_a, anterior, du_b):
    if du_a==0 or du_b==0 or anterior==0: return ""
    pct = ((atual/du_a - anterior/du_b)/(anterior/du_b))*100
    if pct>5: return f'<span style="color:#2E7D32;font-weight:600;font-size:0.75rem">+{pct:.0f}%</span>'
    elif pct<-5: return f'<span style="color:#C62828;font-weight:600;font-size:0.75rem">{pct:.0f}%</span>'
    return f'<span style="color:#888;font-size:0.75rem">{pct:+.0f}%</span>'
def _bd(df, val="total"):
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
        d[k] = d.get(k,0) + (float(r[val]) if r[val] is not None and not pd.isna(r[val]) else 0)
    return d
def _g(d, e, a, m): return d.get((e,a,m), 0)

st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.8rem">💼 OPORTUNIDADES</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Orcamentos, vendas e pipeline por empresa</p>
</div>
""", unsafe_allow_html=True)

empresa = st.session_state.get("empresa_filtro", "Todas")
hoje = date.today()
m, a = hoje.month, hoje.year
m_a, a_a = (m-1, a) if m>1 else (12, a-1)
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_a, m_a)
n_ant = MESES_PT[m_a]

try:
    df_opps = get_opps_mensal_por_empresa()
    df_ganhas = get_opps_ganhas_mensal_por_empresa()
    df_kwh = get_energy_kwh_mensal()
    df_kwh_orc = get_energy_kwh_orcado_mensal()
    df_pipe = get_pipeline_aberto_por_empresa()
    energy_pipe_kwh = get_energy_pipeline_kwh()

    opps_q = _bd(df_opps); opps_v = _bd(df_opps, "valor")
    ganhas_q = _bd(df_ganhas); ganhas_v = _bd(df_ganhas, "valor")
    kwh_m = {}
    if not df_kwh.empty:
        for _, r in df_kwh.iterrows():
            kwh_m[(int(r["ano"]),int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0
    kwh_orc_m = {}
    if not df_kwh_orc.empty:
        for _, r in df_kwh_orc.iterrows():
            kwh_orc_m[(int(r["ano"]),int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0

    empresas_ex = [empresa] if empresa != "Todas" and empresa in EMPRESAS else EMPRESAS

    # ========================================
    # SECAO 1: CARD + PIPELINE por empresa
    # ========================================
    st.markdown(f'<h3 style="font-size:1.3rem;color:#1a1a2e">\U0001f4bc ORCAMENTOS, VENDAS E PIPELINE \u2014 {MESES_PT[m].upper()}/{a}</h3>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#666;font-size:0.9rem;margin-top:-8px">Card de cada empresa + pipeline detalhado por fase \u2014 vs {n_ant} (por dia util)</p>', unsafe_allow_html=True)

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        ie = (emp == "Flex Energy")

        oq = _g(opps_q, emp, a, m); oq_a = _g(opps_q, emp, a_a, m_a)
        ov = _g(opps_v, emp, a, m); ov_a = _g(opps_v, emp, a_a, m_a)
        gq = _g(ganhas_q, emp, a, m); gq_a = _g(ganhas_q, emp, a_a, m_a)
        gv = _g(ganhas_v, emp, a, m); gv_a = _g(ganhas_v, emp, a_a, m_a)

        if ie:
            kh = kwh_m.get((a,m),0); kh_a = kwh_m.get((a_a,m_a),0)
            vol_vend = _fk(kh); vol_lab = "Energia"
            v_vol_vend = _var(kh, du_h, kh_a, du_ant); vol_cor = "#EC8500"
            # Volume orcado em kWh (via OpportunityLineItem)
            kh_orc = kwh_orc_m.get((a,m),0); kh_orc_a = kwh_orc_m.get((a_a,m_a),0)
            vol_orc = _fk(kh_orc); v_vol_orc = _var(kh_orc, du_h, kh_orc_a, du_ant)
        else:
            vol_vend = _fv(gv); vol_lab = "Valor"
            v_vol_vend = _var(gv, du_h, gv_a, du_ant); vol_cor = "#2E7D32"
            vol_orc = _fv(ov); v_vol_orc = _var(ov, du_h, ov_a, du_ant)

        v_oq = _var(oq, du_h, oq_a, du_ant)
        v_gq = _var(gq, du_h, gq_a, du_ant)

        # Valores mes anterior formatados para rodape
        if ie:
            vol_vend_ant = _fk(kh_a)
            vol_orc_ant = _fk(kh_orc_a)
        else:
            vol_vend_ant = _fv(gv_a)
            vol_orc_ant = _fv(ov_a)

        # Card com 4 blocos: Orçamentos | Vol Orçado | Vendas | Vol Vendido
        st.markdown(f"""
<div style="background:white;border-radius:12px 12px 0 0;padding:18px 22px;margin-bottom:0;box-shadow:0 2px 6px rgba(0,0,0,0.06);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
<div style="display:flex;align-items:center;gap:12px"><img src="{get_logo_b64(emp)}" style="height:40px;border-radius:6px" alt="{label}"/><span style="font-weight:700;color:{cor};font-size:1.1rem">{label}</span></div>
<span style="font-size:0.75rem;color:#999">vs {n_ant} (por DU)</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:110px;text-align:center;padding:8px 10px;border-right:1px solid #f0f0f0">
<div style="font-size:1.4rem;font-weight:700;color:#1565C0">{_fmt(oq)}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;margin:3px 0">Orcamentos</div>
<div>{v_oq}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:8px 10px;border-right:1px solid #f0f0f0">
<div style="font-size:1.4rem;font-weight:700;color:#1565C0">{vol_orc}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;margin:3px 0">{vol_lab} Orcado</div>
<div>{v_vol_orc}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:8px 10px;border-right:1px solid #f0f0f0">
<div style="font-size:1.4rem;font-weight:700;color:#2E7D32">{_fmt(gq)}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;margin:3px 0">Vendas</div>
<div>{v_gq}</div>
</div>
<div style="flex:1;min-width:110px;text-align:center;padding:8px 10px">
<div style="font-size:1.4rem;font-weight:700;color:{vol_cor}">{vol_vend}</div>
<div style="font-size:0.65rem;color:#888;text-transform:uppercase;margin:3px 0">{vol_lab} Vendido</div>
<div>{v_vol_vend}</div>
</div>
</div>
<div style="font-size:0.7rem;color:#999;margin-top:6px;padding-top:6px;border-top:1px solid #f5f5f5">
{n_ant}: {_fmt(oq_a)} orcs \u00b7 {vol_orc_ant} orcado \u00b7 {_fmt(gq_a)} vendas \u00b7 {vol_vend_ant} vendido
</div>
</div>
""", unsafe_allow_html=True)

        # Pipeline abaixo do card
        if not df_pipe.empty:
            df_e = df_pipe[df_pipe["Empresa_Proprietaria__c"]==emp].copy()
            if not df_e.empty:
                ordem = {s:i for i,s in enumerate(FASES_PIPELINE)}
                df_e["ord"] = df_e["StageName"].map(ordem).fillna(99)
                df_e = df_e.sort_values("ord")
                df_e = df_e[~df_e["StageName"].isin(["Fechado Ganho","Fechado Perdido"])]

                if not df_e.empty:
                    unid = "kWh" if ie else "R$"
                    rows = ""
                    total_pipe = int(df_e["total"].sum())
                    for _, r in df_e.iterrows():
                        fase = r["StageName"]; qtd = int(r["total"])
                        # Energy: usar kWh real do OpportunityLineItem
                        if ie:
                            val = energy_pipe_kwh.get(fase, 0)
                        else:
                            val = float(r["valor"]) if (r["valor"] is not None and not pd.isna(r["valor"])) else 0
                        vf = _fk(val) if ie else _fv(val)
                        pct = (qtd/total_pipe*100) if total_pipe > 0 else 0
                        bar_w = min(pct, 100)
                        rows += f'<div style="display:flex;align-items:center;padding:4px 8px;border-bottom:1px solid #f5f5f5"><div style="flex:2;font-size:0.8rem">{fase}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt(qtd)}</div><div style="flex:1;text-align:right;color:#666;font-size:0.8rem">{vf}</div><div style="flex:2;padding-left:8px"><div style="background:#e8e8e8;border-radius:4px;height:12px"><div style="background:{cor};border-radius:4px;height:12px;width:{bar_w:.0f}%"></div></div></div></div>'

                    if ie:
                        total_val = sum(energy_pipe_kwh.values())
                    else:
                        total_val = df_e["valor"].sum()
                    tvf = _fk(total_val) if ie else _fv(total_val)
                    hdr = f'<div style="display:flex;padding:4px 8px;border-bottom:2px solid #ddd"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Fase</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">{unid}</div><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase;padding-left:8px">Distribuicao</div></div>'

                    st.markdown(f"""
<div style="background:#FAFAFA;border-radius:0 0 12px 12px;padding:14px 20px;margin-bottom:16px;border-left:5px solid {cor};border-top:1px dashed #ddd">
<div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #eee">
<div style="font-size:0.75rem;color:#666;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">PIPELINE ABERTO</div>
<div style="font-size:1.4rem;font-weight:800;color:{cor}">{_fmt(total_pipe)} <span style="font-size:0.8rem;font-weight:600;color:#888">opps</span></div>
<div style="font-size:1.4rem;font-weight:800;color:#1a1a2e">{tvf}</div>
</div>
{hdr}{rows}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SECAO 2: EVOLUCAO MES A MES por empresa
    # ========================================
    st.markdown('<h3 style="font-size:1.3rem;color:#1a1a2e">\U0001f4c5 EVOLUCAO MES A MES</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color:#666;font-size:0.9rem;margin-top:-8px">Orcamentos, vendas e volume dos ultimos 6 meses por empresa</p>', unsafe_allow_html=True)

    meses = []
    mx, ax = m, a
    for _ in range(6):
        meses.append((ax, mx))
        mx -= 1
        if mx == 0: mx, ax = 12, ax-1
    meses.reverse()

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        ie = (emp == "Flex Energy")
        vol_col = "Energia" if ie else "Valor"

        rows_html = ""
        for (ano, mes) in meses:
            du = dias_uteis_no_mes(ano, mes)
            oq = _g(opps_q, emp, ano, mes)
            gq = _g(ganhas_q, emp, ano, mes)
            gv = _g(ganhas_v, emp, ano, mes)
            wr = f"{(gq/oq*100):.0f}%" if oq > 0 else "\u2014"
            vol = _fk(kwh_m.get((ano,mes),0)) if ie else _fv(gv)
            orc_du = f"{oq/du:.1f}" if du > 0 else "\u2014"
            vend_du = f"{gq/du:.1f}" if du > 0 else "\u2014"
            bg = "#fff" if len(rows_html) % 2 == 0 else "#F8F9FA"
            rows_html += f'<tr style="background:{bg}"><td style="font-weight:600;color:#1a1a2e">{MESES_PT[mes]}/{ano}</td><td style="text-align:center;color:#888">{du}</td><td style="text-align:center;font-weight:600;color:#1565C0;font-size:1.05rem">{_fmt(oq)}</td><td style="text-align:center;color:#888">{orc_du}</td><td style="text-align:center;font-weight:700;color:#2E7D32;font-size:1.05rem">{_fmt(gq)}</td><td style="text-align:center;color:#888">{vend_du}</td><td style="text-align:center;color:#555">{wr}</td><td style="text-align:right;font-weight:600;color:{cor}">{vol}</td></tr>'

        hdr = f'<tr style="background:#1a1a2e"><th style="color:white;padding:10px 12px;font-size:0.75rem;text-transform:uppercase">Mes</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.75rem">DU</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.75rem">Orcs</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.7rem">Orcs/DU</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.75rem">Vendas</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.7rem">Vend/DU</th><th style="color:white;text-align:center;padding:10px 8px;font-size:0.75rem">Win%</th><th style="color:white;text-align:right;padding:10px 12px;font-size:0.75rem">{vol_col}</th></tr>'

        st.markdown(f"""
<div style="margin:12px 0 16px 0">
<div style="display:flex;align-items:center;gap:10px;border-left:4px solid {cor};padding:8px 14px;margin-bottom:0;font-weight:700;color:{cor};font-size:1rem;background:white;border-radius:8px 8px 0 0"><img src="{get_logo_b64(emp)}" style="height:28px;border-radius:4px" alt="{label}"/><span>{label}</span></div>
<table style="width:100%;border-collapse:collapse;border-radius:0 0 8px 8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06)">
{hdr}{rows_html}
</table>
</div>
""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
