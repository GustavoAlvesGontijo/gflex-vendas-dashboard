"""
Pagina 2 — Oportunidades
Card por empresa + pipeline detalhado abaixo de cada card.
Evolucao mes a mes por empresa. Sem detalhamento de periodo nem engajamento.
"""
import streamlit as st
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES, FASES_PIPELINE,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT,
)
from salesforce_client import (
    get_opps_mensal_por_empresa, get_opps_ganhas_mensal_por_empresa,
    get_energy_kwh_mensal, get_pipeline_aberto_por_empresa,
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
<h1 style="color:white;margin:0;font-size:1.5rem">Oportunidades</h1>
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
    df_pipe = get_pipeline_aberto_por_empresa()

    opps_q = _bd(df_opps); opps_v = _bd(df_opps, "valor")
    ganhas_q = _bd(df_ganhas); ganhas_v = _bd(df_ganhas, "valor")
    kwh_m = {}
    if not df_kwh.empty:
        for _, r in df_kwh.iterrows():
            kwh_m[(int(r["ano"]),int(r["mes"]))] = float(r["total_kwh"]) if r["total_kwh"] else 0

    empresas_ex = [empresa] if empresa != "Todas" and empresa in EMPRESAS else EMPRESAS

    # ========================================
    # SECAO 1: CARD + PIPELINE por empresa
    # ========================================
    st.markdown(f"### {MESES_PT[m]}/{a} — Orcamentos, Vendas e Pipeline")
    st.caption(f"Comparacao com {n_ant} normalizada por dias uteis")

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        ie = (emp == "Flex Energy")

        oq = _g(opps_q, emp, a, m); oq_a = _g(opps_q, emp, a_a, m_a)
        gq = _g(ganhas_q, emp, a, m); gq_a = _g(ganhas_q, emp, a_a, m_a)
        gv = _g(ganhas_v, emp, a, m); gv_a = _g(ganhas_v, emp, a_a, m_a)

        if ie:
            kh = kwh_m.get((a,m),0); kh_a = kwh_m.get((a_a,m_a),0)
            vol = _fk(kh); vol_a = _fk(kh_a); vol_lab = "Energia"
            v_vol = _var(kh, du_h, kh_a, du_ant); vol_cor = "#EC8500"
        else:
            vol = _fv(gv); vol_a = _fv(gv_a); vol_lab = "Valor"
            v_vol = _var(gv, du_h, gv_a, du_ant); vol_cor = "#2E7D32"

        v_oq = _var(oq, du_h, oq_a, du_ant)
        v_gq = _var(gq, du_h, gq_a, du_ant)

        # Card
        st.markdown(f"""
<div style="background:white;border-radius:12px 12px 0 0;padding:16px 20px;margin-bottom:0;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
<span style="font-weight:700;color:{cor};font-size:1.05rem">{label}</span>
<span style="font-size:0.7rem;color:#999">vs {n_ant} (por DU)</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:120px;text-align:center;padding:6px 10px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#1565C0">{_fmt(oq)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Orcamentos</div>
<div>{v_oq}</div>
</div>
<div style="flex:1;min-width:120px;text-align:center;padding:6px 10px;border-right:1px solid #f0f0f0">
<div style="font-size:1.3rem;font-weight:700;color:#2E7D32">{_fmt(gq)}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">Vendas</div>
<div>{v_gq}</div>
</div>
<div style="flex:1;min-width:120px;text-align:center;padding:6px 10px">
<div style="font-size:1.3rem;font-weight:700;color:{vol_cor}">{vol}</div>
<div style="font-size:0.55rem;color:#888;text-transform:uppercase;margin:2px 0">{vol_lab} Vendido</div>
<div>{v_vol}</div>
</div>
</div>
<div style="font-size:0.7rem;color:#999;margin-top:6px;padding-top:6px;border-top:1px solid #f5f5f5">
{n_ant}: {_fmt(oq_a)} orcs \u00b7 {_fmt(gq_a)} vendas \u00b7 {vol_a}
</div>
</div>
""", unsafe_allow_html=True)

        # Pipeline abaixo do card
        if not df_pipe.empty:
            df_e = df_pipe[df_pipe["Empresa_Proprietaria__c"]==emp].copy()
            if not df_e.empty:
                ordem = {s:i for i,s in enumerate(FASES_PIPELINE + ["Em Analise"])}
                df_e["ord"] = df_e["StageName"].map(ordem).fillna(99)
                df_e = df_e.sort_values("ord")
                df_e = df_e[~df_e["StageName"].isin(["Fechado Ganho","Fechado Perdido"])]

                if not df_e.empty:
                    unid = "kWh" if ie else "R$"
                    rows = ""
                    total_pipe = int(df_e["total"].sum())
                    for _, r in df_e.iterrows():
                        fase = r["StageName"]; qtd = int(r["total"])
                        val = r["valor"] if r["valor"] else 0
                        vf = _fk(val) if ie else _fv(val)
                        pct = (qtd/total_pipe*100) if total_pipe > 0 else 0
                        bar_w = min(pct, 100)
                        rows += f'<div style="display:flex;align-items:center;padding:4px 8px;border-bottom:1px solid #f5f5f5"><div style="flex:2;font-size:0.8rem">{fase}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt(qtd)}</div><div style="flex:1;text-align:right;color:#666;font-size:0.8rem">{vf}</div><div style="flex:2;padding-left:8px"><div style="background:#e8e8e8;border-radius:4px;height:12px"><div style="background:{cor};border-radius:4px;height:12px;width:{bar_w:.0f}%"></div></div></div></div>'

                    total_val = df_e["valor"].sum()
                    tvf = _fk(total_val) if ie else _fv(total_val)
                    hdr = f'<div style="display:flex;padding:4px 8px;border-bottom:2px solid #ddd"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Fase</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">{unid}</div><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase;padding-left:8px">Distribuicao</div></div>'

                    st.markdown(f"""
<div style="background:#FAFAFA;border-radius:0 0 12px 12px;padding:10px 16px;margin-bottom:16px;border-left:5px solid {cor};border-top:1px dashed #ddd">
<div style="font-size:0.7rem;color:#888;font-weight:600;margin-bottom:6px">PIPELINE ABERTO \u2014 {_fmt(total_pipe)} opps \u00b7 {tvf}</div>
{hdr}{rows}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SECAO 2: EVOLUCAO MES A MES por empresa
    # ========================================
    st.markdown("### Evolucao Mes a Mes")

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
        tab = []
        for (ano, mes) in meses:
            du = dias_uteis_no_mes(ano, mes)
            oq = _g(opps_q, emp, ano, mes)
            gq = _g(ganhas_q, emp, ano, mes)
            gv = _g(ganhas_v, emp, ano, mes)
            wr = (gq/oq*100) if oq > 0 else 0
            vol = _fk(kwh_m.get((ano,mes),0)) if ie else _fv(gv)
            tab.append({"Mes": f"{MESES_PT[mes]}/{ano}", "DU": du, "Orcs": int(oq), "Vendas": int(gq), "Win%": f"{wr:.0f}%", "Volume": vol})
        st.markdown(f'<div style="border-left:4px solid {cor};padding-left:10px;margin:8px 0 4px 0;font-weight:600;color:{cor}">{label}</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
