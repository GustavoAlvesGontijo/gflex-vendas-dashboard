"""
Pagina 1 — Visao Geral
Cards por empresa: VENDIDO | EM NEGOCIACAO/CONTRATO lado a lado.
Combustiveis com soma. Evolucao por empresa (nao somada).
Top origens movido para Leads. Trimestre Q atual vs Q anterior.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Auth check
if not st.session_state.get("authenticated", False):
    st.warning("Acesse pela pagina principal para fazer login.")
    st.stop()
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    MESES_PT, MESES_PT_FULL,
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
)

def _fmt(v):
    if v is None or pd.isna(v): return "\u2014"
    return f"{int(v):,}".replace(",", ".")
def _fv(v):
    if not v or pd.isna(v) or v == 0: return "\u2014"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    if not v or pd.isna(v) or v == 0: return "\u2014"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"
def _var(atual, du_a, anterior, du_b):
    if du_a == 0 or du_b == 0 or anterior == 0: return ""
    pct = ((atual/du_a - anterior/du_b) / (anterior/du_b)) * 100
    if pct > 5: return f'<span style="color:#2E7D32;font-weight:600;font-size:0.75rem">+{pct:.0f}%</span>'
    elif pct < -5: return f'<span style="color:#C62828;font-weight:600;font-size:0.75rem">{pct:.0f}%</span>'
    return f'<span style="color:#888;font-size:0.75rem">{pct:+.0f}%</span>'
def _bd(df, val="total", fc=None, fv=None):
    d = {}
    if df.empty: return d
    for _, r in df.iterrows():
        if fc and r.get(fc) != fv: continue
        k = (r.get("Empresa_Proprietaria__c",""), int(r["ano"]), int(r["mes"]))
        d[k] = d.get(k,0) + (float(r[val]) if r[val] is not None and not pd.isna(r[val]) else 0)
    return d
def _g(d, e, a, m): return d.get((e,a,m), 0)

# Header
hoje = date.today()
m, a = hoje.month, hoje.year
m_a, a_a = (m-1, a) if m > 1 else (12, a-1)
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_a, m_a)
n_ant = MESES_PT[m_a]
tri = (m-1)//3+1
meses_tri = [(a, mx) for mx in range((tri-1)*3+1, min(tri*3+1, m+1))]
if tri > 1: tri_a, a_ta = tri-1, a
else: tri_a, a_ta = 4, a-1
meses_tri_a = [(a_ta, mx) for mx in range((tri_a-1)*3+1, tri_a*3+1)]

st.markdown(f"""
<div style="background:#1a1a2e;padding:20px 28px;border-radius:14px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.6rem;font-weight:700">{MESES_PT_FULL.get(m,"")} {a}</h1>
<div style="display:flex;gap:24px;margin-top:8px">
<span style="color:#EC8500;font-size:0.85rem;font-weight:600">{du_h} de {du_t} dias uteis</span>
<span style="color:rgba(255,255,255,0.5);font-size:0.85rem">{n_ant} teve {du_ant} DU</span>
</div>
</div>
""", unsafe_allow_html=True)
pct = (du_h/du_t*100) if du_t > 0 else 0
st.markdown(f'<div style="background:#e8e8e8;border-radius:6px;height:6px;margin:-12px 0 20px 0"><div style="background:linear-gradient(90deg,#EC8500,#F7C42D);border-radius:6px;height:6px;width:{pct:.0f}%"></div></div>', unsafe_allow_html=True)

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

    # Pipeline Energy kWh (real, via OpportunityLineItem)
    energy_pipe_kwh = get_energy_pipeline_kwh()
    energy_pipe_kwh_total = sum(energy_pipe_kwh.values())
    energy_pipe_kwh_neg = sum(v for k, v in energy_pipe_kwh.items() if k in ["Negocia\u00e7\u00e3o", "Contrato"])

    # Pipeline aberto por empresa — separar negociacao/contrato vs total
    pipe_neg = {}
    pipe_neg_val = {}
    pipe_total = {}
    pipe_total_val = {}
    if not df_pipe.empty:
        fases_negociacao = ["Negocia\u00e7\u00e3o", "Contrato"]
        for _, r in df_pipe.iterrows():
            e = r.get("Empresa_Proprietaria__c","")
            qtd = int(r["total"])
            val = float(r["valor"]) if r["valor"] else 0
            pipe_total[e] = pipe_total.get(e,0) + qtd
            pipe_total_val[e] = pipe_total_val.get(e,0) + val
            if r["StageName"] in fases_negociacao:
                pipe_neg[e] = pipe_neg.get(e,0) + qtd
                pipe_neg_val[e] = pipe_neg_val.get(e,0) + val

    # ========================================
    # SECAO 1: VENDAS + PIPELINE por empresa
    # ========================================
    st.markdown("### Vendas no Mes + Pipeline")
    st.caption(f"Vendido vs em negociacao/contrato — {MESES_PT[m]}/{a} vs {n_ant} (por DU)")

    icones = {"Flex Energy":"\u26a1","GF2 Solu\u00e7\u00f5es Integradas":"\U0001f529","Flex Tendas":"\u26fa","Flex Medi\u00e7\u00f5es":"\U0001f52c","MEC Estruturas Met\u00e1licas":"\U0001f3d7\ufe0f","Flex Solar":"\u2600\ufe0f"}

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
        ic = icones.get(emp,"\U0001f4ca")
        ie = (emp == "Flex Energy")

        gq = _g(ganhas_q, emp, a, m); gq_a = _g(ganhas_q, emp, a_a, m_a)
        gv = _g(ganhas_v, emp, a, m); gv_a = _g(ganhas_v, emp, a_a, m_a)
        lq = _g(leads_t, emp, a, m); lq_a = _g(leads_t, emp, a_a, m_a)
        oq = _g(opps_q, emp, a, m); oq_a = _g(opps_q, emp, a_a, m_a)

        # Pipeline: negociacao+contrato vs total
        pn = pipe_neg.get(emp, 0)
        pnv = pipe_neg_val.get(emp, 0)
        pt = pipe_total.get(emp, 0)
        ptv = pipe_total_val.get(emp, 0)

        # Volume vendido + pipeline
        if ie:
            kh = kwh_m.get((a,m),0); kh_a = kwh_m.get((a_a,m_a),0)
            vol = _fk(kh); vol_a = _fk(kh_a); vol_lab = "Energia"; v_vol = _var(kh, du_h, kh_a, du_ant)
            # Pipeline Energy usa kWh real (OpportunityLineItem)
            neg_vol = _fk(energy_pipe_kwh_neg); pipe_vol = _fk(energy_pipe_kwh_total)
        else:
            vol = _fv(gv); vol_a = _fv(gv_a); vol_lab = "Valor"; v_vol = _var(gv, du_h, gv_a, du_ant)
            neg_vol = _fv(pnv); pipe_vol = _fv(ptv)

        v_gq = _var(gq, du_h, gq_a, du_ant)
        v_lq = _var(lq, du_h, lq_a, du_ant)
        v_oq = _var(oq, du_h, oq_a, du_ant)

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px 20px;margin-bottom:10px;box-shadow:0 2px 6px rgba(0,0,0,0.06);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
<span style="font-weight:700;color:{cor};font-size:1.1rem">{ic} {label}</span>
<span style="font-size:0.7rem;color:#999">vs {n_ant} (por DU)</span>
</div>
<div style="display:flex;gap:10px;flex-wrap:wrap">
<div style="flex:1;min-width:180px;background:#E8F5E9;border-radius:10px;padding:12px 16px">
<div style="font-size:0.6rem;color:#2E7D32;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:6px">\u2705 Vendido no Mes</div>
<div style="display:flex;gap:16px">
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#2E7D32">{_fmt(gq)}</div><div style="font-size:0.55rem;color:#666">vendas {v_gq}</div></div>
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#2E7D32">{vol}</div><div style="font-size:0.55rem;color:#666">{vol_lab} {v_vol}</div></div>
</div>
</div>
<div style="flex:1;min-width:180px;background:#FFF3E0;border-radius:10px;padding:12px 16px">
<div style="font-size:0.6rem;color:#E65100;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:6px">\U0001f525 Negociacao + Contrato</div>
<div style="display:flex;gap:16px">
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#E65100">{_fmt(pn)}</div><div style="font-size:0.55rem;color:#666">opps</div></div>
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#E65100">{neg_vol}</div><div style="font-size:0.55rem;color:#666">{vol_lab}</div></div>
</div>
</div>
<div style="flex:1;min-width:180px;background:#E3F2FD;border-radius:10px;padding:12px 16px">
<div style="font-size:0.6rem;color:#1565C0;text-transform:uppercase;font-weight:700;letter-spacing:0.5px;margin-bottom:6px">\U0001f4cb Pipeline Total</div>
<div style="display:flex;gap:16px">
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#1565C0">{_fmt(pt)}</div><div style="font-size:0.55rem;color:#666">opps abertas</div></div>
<div style="text-align:center"><div style="font-size:1.5rem;font-weight:700;color:#1565C0">{pipe_vol}</div><div style="font-size:0.55rem;color:#666">{vol_lab}</div></div>
</div>
</div>
<div style="flex:1;min-width:180px;padding:12px 16px">
<div style="display:flex;gap:16px">
<div style="text-align:center"><div style="font-size:1.2rem;font-weight:700;color:#555">{_fmt(lq)}</div><div style="font-size:0.55rem;color:#888">leads {v_lq}</div></div>
<div style="text-align:center"><div style="font-size:1.2rem;font-weight:700;color:#555">{_fmt(oq)}</div><div style="font-size:0.55rem;color:#888">orcamentos {v_oq}</div></div>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SECAO 2: TRIMESTRE Q atual vs Q anterior
    # ========================================
    st.markdown(f"### Trimestre Q{tri} vs Q{tri_a}")
    st.caption("Cada empresa vs ela mesma — normalizado por dias uteis")

    du_tri = sum(dias_uteis_no_mes(ax,mx) for ax,mx in meses_tri)
    du_tri_a = sum(dias_uteis_no_mes(ax,mx) for ax,mx in meses_tri_a)

    tri_d = []
    for emp in EMPRESAS:
        label = EMPRESA_LABELS[emp]
        ie = (emp == "Flex Energy")
        gt = sum(_g(ganhas_q,emp,ax,mx) for ax,mx in meses_tri)
        ga = sum(_g(ganhas_q,emp,ax,mx) for ax,mx in meses_tri_a)
        gvt = sum(_g(ganhas_v,emp,ax,mx) for ax,mx in meses_tri)
        gva = sum(_g(ganhas_v,emp,ax,mx) for ax,mx in meses_tri_a)
        ot = sum(_g(opps_q,emp,ax,mx) for ax,mx in meses_tri)
        oa = sum(_g(opps_q,emp,ax,mx) for ax,mx in meses_tri_a)
        def _vdu(at,da,an,db):
            if da==0 or db==0 or an==0: return "\u2014"
            p = ((at/da-an/db)/(an/db))*100
            return f"{p:+.0f}%"
        row = {"Empresa": label}
        row[f"Vendas Q{tri}"] = int(gt)
        row[f"Vendas Q{tri_a}"] = int(ga)
        row["Var"] = _vdu(gt,du_tri,ga,du_tri_a)
        if ie:
            row[f"Vol Q{tri}"] = _fk(gvt)
            row[f"Vol Q{tri_a}"] = _fk(gva)
        else:
            row[f"Vol Q{tri}"] = _fv(gvt)
            row[f"Vol Q{tri_a}"] = _fv(gva)
        row[f"Orcs Q{tri}"] = int(ot)
        row[f"Orcs Q{tri_a}"] = int(oa)
        tri_d.append(row)
    st.dataframe(pd.DataFrame(tri_d), width="stretch", hide_index=True)

    st.markdown("---")

    # ========================================
    # SECAO 3: COMBUSTIVEIS com soma
    # ========================================
    st.markdown("### Combustiveis — Performance por Origem")
    st.caption(f"Leads criados, orcamentos e vendas no mes de {MESES_PT[m]}/{a} — por empresa e canal")

    ORIGENS = ["Meta ADS","Google Ads","Website","Exact Sales","Instagram","Indicacao","Feira","Prospeccao Ativa Vendedor"]
    d_ini = date(a, m, 1)
    df_lo = get_origens_funil_por_empresa(d_ini, hoje)
    df_oo = get_opps_por_origem_empresa(d_ini, hoje)

    if not df_lo.empty and not df_oo.empty:
        for emp in EMPRESAS:
            cor = CORES[emp]["primaria"]
            label = EMPRESA_LABELS[emp]
            ie = (emp == "Flex Energy")
            df_l = df_lo[df_lo["Empresa_Proprietaria__c"]==emp]
            if df_l.empty: continue

            l_or = df_l.groupby("LeadSource")["total"].sum().to_dict()
            df_o = df_oo[df_oo["Empresa_Proprietaria__c"]==emp]
            o_or = df_o.groupby("LeadSource")["total"].sum().to_dict()
            g_or = df_o[df_o["StageName"]=="Fechado Ganho"].groupby("LeadSource")["total"].sum().to_dict()
            v_or = df_o[df_o["StageName"]=="Fechado Ganho"].groupby("LeadSource")["valor"].sum().to_dict()

            origens_cd = [o for o in ORIGENS if l_or.get(o,0)>0 or o_or.get(o,0)>0]
            if not origens_cd: continue

            unid = "kWh" if ie else "R$"
            rows = ""
            sum_l = sum_o = sum_g = sum_v = 0
            for orig in origens_cd:
                nl = int(l_or.get(orig,0)); no = int(o_or.get(orig,0)); ng = int(g_or.get(orig,0)); nv = v_or.get(orig,0)
                sum_l += nl; sum_o += no; sum_g += ng; sum_v += nv
                vf = _fk(nv) if ie else _fv(nv)
                tx = f"{(ng/no*100):.0f}%" if no > 0 else "\u2014"
                sc = "#2E7D32" if ng > 0 else "#999"
                rows += f'<div style="display:flex;align-items:center;padding:3px 0;border-bottom:1px solid #f5f5f5"><div style="flex:2;font-size:0.8rem">{orig}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt(nl)}</div><div style="flex:1;text-align:right;color:#1565C0">{_fmt(no)}</div><div style="flex:1;text-align:right;color:{sc};font-weight:600">{_fmt(ng)}</div><div style="flex:1;text-align:right;color:#666;font-size:0.8rem">{vf}</div><div style="flex:1;text-align:right;font-size:0.75rem">{tx}</div></div>'

            # Linha de total
            svf = _fk(sum_v) if ie else _fv(sum_v)
            stx = f"{(sum_g/sum_o*100):.0f}%" if sum_o > 0 else "\u2014"
            rows += f'<div style="display:flex;align-items:center;padding:5px 0;border-top:2px solid #ddd;font-weight:700"><div style="flex:2;font-size:0.8rem">TOTAL</div><div style="flex:1;text-align:right">{_fmt(sum_l)}</div><div style="flex:1;text-align:right;color:#1565C0">{_fmt(sum_o)}</div><div style="flex:1;text-align:right;color:#2E7D32">{_fmt(sum_g)}</div><div style="flex:1;text-align:right;color:#666">{svf}</div><div style="flex:1;text-align:right">{stx}</div></div>'

            hdr = f'<div style="display:flex;padding:2px 0;border-bottom:2px solid #eee;margin-bottom:2px"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Origem</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Leads</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Orcaram</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Venderam</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">{unid}</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Win%</div></div>'
            st.markdown(f'<div style="background:white;border-radius:12px;padding:14px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:3px solid {cor}"><div style="font-weight:700;color:{cor};margin-bottom:8px;font-size:0.95rem">{label}</div>{hdr}{rows}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SECAO 4: EVOLUCAO MES A MES — POR EMPRESA
    # ========================================
    st.markdown("### Evolucao Mes a Mes — Por Empresa")

    meses_ex = []
    mx, ax = m, a
    for _ in range(6):
        meses_ex.append((ax, mx))
        mx -= 1
        if mx == 0: mx, ax = 12, ax-1
    meses_ex.reverse()

    for emp in EMPRESAS:
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
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
        st.markdown(f'<div style="border-left:4px solid {cor};padding-left:10px;margin:8px 0 4px 0;font-weight:600;color:{cor}">{label}</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
