"""
Pagina 4 — Leads
%F1, origens por empresa, funil de status como tabela por empresa.
Sem temperatura, sem motivos de descarte.
"""
import streamlit as st
import pandas as pd
from datetime import date
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT,
)
from salesforce_client import (
    get_leads_por_status, get_leads_por_origem,
    get_leads_mensal_por_empresa, get_contas_mensal_por_empresa,
    get_leads_convertidos_no_mes_por_empresa,
    get_leads_origem_mensal_por_empresa,
)

def _fmt(v): return f"{int(v):,}".replace(",",".") if v else "0"
def _var(atual, du_a, anterior, du_b):
    if du_a==0 or du_b==0 or anterior==0: return ""
    pct = ((atual/du_a - anterior/du_b)/(anterior/du_b))*100
    if pct>5: return f'<span style="color:#2E7D32;font-weight:600;font-size:0.75rem">+{pct:.0f}%</span>'
    elif pct<-5: return f'<span style="color:#C62828;font-weight:600;font-size:0.75rem">{pct:.0f}%</span>'
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

st.markdown("""
<div style="background:#1a1a2e;padding:16px 24px;border-radius:12px;margin-bottom:20px">
<h1 style="color:white;margin:0;font-size:1.5rem">Leads</h1>
<p style="color:#EC8500;margin:2px 0 0 0;font-size:0.85rem">Geracao, conversao, %F1, origens e funil — por empresa</p>
</div>
""", unsafe_allow_html=True)

hoje = date.today()
m, a = hoje.month, hoje.year
m_a, a_a = (m-1, a) if m>1 else (12, a-1)
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
du_ant = dias_uteis_no_mes(a_a, m_a)
n_ant = MESES_PT[m_a]
empresa = st.session_state.get("empresa_filtro", "Todas")

try:
    df_leads = get_leads_mensal_por_empresa()
    df_contas = get_contas_mensal_por_empresa()
    df_conv = get_leads_convertidos_no_mes_por_empresa()
    df_origens = get_leads_origem_mensal_por_empresa()

    leads_t = _bd(df_leads)
    leads_cc = _bd(df_leads, fc="IsConverted", fv=True)
    conv_m = _bd(df_conv)
    contas_d = _bd(df_contas)

    empresas_ex = [empresa] if empresa != "Todas" and empresa in EMPRESAS else EMPRESAS

    # ========================================
    # SUBSECAO 1: CARDS DO MES com %F1
    # ========================================
    st.markdown(f"### Mes Vigente — {MESES_PT[m]}/{a}", anchor="mes")
    st.caption(f"{du_h} de {du_t} DU | %F1 = criados E convertidos no mesmo mes")

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        l = _g(leads_t, emp, a, m); l_a = _g(leads_t, emp, a_a, m_a)
        cm = _g(conv_m, emp, a, m); cm_a = _g(conv_m, emp, a_a, m_a)
        cc = _g(leads_cc, emp, a, m); cc_a = _g(leads_cc, emp, a_a, m_a)
        ct = _g(contas_d, emp, a, m); ct_a = _g(contas_d, emp, a_a, m_a)
        f1 = (cc/l*100) if l > 0 else 0
        f1_a = (cc_a/l_a*100) if l_a > 0 else 0
        v_l = _var(l, du_h, l_a, du_ant)
        v_cm = _var(cm, du_h, cm_a, du_ant)
        v_ct = _var(ct, du_h, ct_a, du_ant)
        f1_d = f1-f1_a
        f1v = f'<span style="color:{"#2E7D32" if f1_d>0 else "#C62828"};font-weight:600;font-size:0.75rem">{f1_d:+.1f}pp</span>' if abs(f1_d)>1 else ""

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<span style="font-weight:700;color:{cor};font-size:1rem">{label}</span>
<span style="font-size:0.7rem;color:#999">vs {n_ant}</span>
</div>
<div style="display:flex;gap:0;flex-wrap:wrap">
<div style="flex:1;min-width:90px;text-align:center;padding:5px 6px;border-right:1px solid #f0f0f0">
<div style="font-size:1.2rem;font-weight:700;color:#1a1a2e">{_fmt(l)}</div>
<div style="font-size:0.5rem;color:#888;text-transform:uppercase;margin:2px 0">Leads</div>
<div>{v_l}</div>
</div>
<div style="flex:1;min-width:90px;text-align:center;padding:5px 6px;border-right:1px solid #f0f0f0">
<div style="font-size:1.2rem;font-weight:700;color:#2E7D32">{_fmt(cm)}</div>
<div style="font-size:0.5rem;color:#888;text-transform:uppercase;margin:2px 0">Conv. Mes</div>
<div>{v_cm}</div>
</div>
<div style="flex:1;min-width:90px;text-align:center;padding:5px 6px;border-right:1px solid #f0f0f0;background:#E8F5E9;border-radius:6px">
<div style="font-size:1.2rem;font-weight:700;color:#1B5E20">{f1:.1f}%</div>
<div style="font-size:0.5rem;color:#888;text-transform:uppercase;margin:2px 0">%F1</div>
<div>{f1v}</div>
</div>
<div style="flex:1;min-width:90px;text-align:center;padding:5px 6px;border-right:1px solid #f0f0f0">
<div style="font-size:1.2rem;font-weight:700;color:#1565C0">{_fmt(cc)}</div>
<div style="font-size:0.5rem;color:#888;text-transform:uppercase;margin:2px 0">Criados+Conv</div>
</div>
<div style="flex:1;min-width:90px;text-align:center;padding:5px 6px">
<div style="font-size:1.2rem;font-weight:700;color:#555">{_fmt(ct)}</div>
<div style="font-size:0.5rem;color:#888;text-transform:uppercase;margin:2px 0">Contas</div>
<div>{v_ct}</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SUBSECAO 2: ORIGENS DO MES por empresa
    # ========================================
    st.markdown(f"### Origens de Leads — {MESES_PT[m]}/{a}", anchor="origens")

    if not df_origens.empty:
        df_or = df_origens[(df_origens["ano"]==a) & (df_origens["mes"]==m)]
        df_or = df_or[df_or["LeadSource"].notna()]
        df_or_a = df_origens[(df_origens["ano"]==a_a) & (df_origens["mes"]==m_a)]

        for emp in empresas_ex:
            cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
            label = EMPRESA_LABELS.get(emp,emp)
            df_e = df_or[df_or["Empresa_Proprietaria__c"]==emp].sort_values("total", ascending=False).head(6)
            if df_e.empty: continue
            ant_d = dict(zip(df_or_a[df_or_a["Empresa_Proprietaria__c"]==emp]["LeadSource"], df_or_a[df_or_a["Empresa_Proprietaria__c"]==emp]["total"]))

            items = ""
            for _, r in df_e.iterrows():
                orig = r["LeadSource"]; qtd = int(r["total"]); qtd_a = ant_d.get(orig,0)
                pct = (qtd/df_e["total"].sum()*100) if df_e["total"].sum()>0 else 0
                vh = _var(qtd, du_h, qtd_a, du_ant)
                items += f'<div style="display:flex;align-items:center;padding:3px 0;border-bottom:1px solid #f8f8f8"><div style="flex:2;font-size:0.8rem">{orig}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt(qtd)}</div><div style="flex:1;text-align:right;color:#888;font-size:0.8rem">{pct:.0f}%</div><div style="flex:1;text-align:right">{vh}</div></div>'

            hdr = f'<div style="display:flex;padding:2px 0;border-bottom:2px solid #eee;margin-bottom:2px"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Origem</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">%</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">vs {n_ant}</div></div>'
            st.markdown(f'<div style="background:white;border-radius:10px;padding:14px 20px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:3px solid {cor}"><div style="font-weight:700;color:{cor};margin-bottom:8px;font-size:0.95rem">{label}</div>{hdr}{items}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SUBSECAO 3: FUNIL DE STATUS — tabela por empresa
    # ========================================
    st.markdown(f"### Funil de Status — {MESES_PT[m]}/{a}", anchor="funil")
    st.caption("Distribuicao de leads criados no mes por status atual")

    d_ini = date(a, m, 1)
    STATUS_ORDEM = ["Aberto","Em Contato","Em Interacao","Transferencia Vendedor","Objecao Comercial","Aceite","Recuperacao","Stand-by Retrabalho","Fechado Convertido","Fechado Nao Convertido"]

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        df_st = get_leads_por_status(emp, d_ini, hoje)
        if df_st.empty: continue

        total = int(df_st["total"].sum())
        df_st["ord"] = df_st["Status"].map({s:i for i,s in enumerate(STATUS_ORDEM)}).fillna(99)
        df_st = df_st.sort_values("ord")

        rows = ""
        for _, r in df_st.iterrows():
            status = r["Status"]; qtd = int(r["total"])
            pct = (qtd/total*100) if total > 0 else 0
            bar_w = min(pct, 100)
            # Cor por status
            if "Convertido" in status and "Nao" not in status: sc = "#2E7D32"
            elif "Nao Convertido" in status: sc = "#C62828"
            else: sc = cor
            rows += f'<div style="display:flex;align-items:center;padding:4px 8px;border-bottom:1px solid #f5f5f5"><div style="flex:2;font-size:0.8rem">{status}</div><div style="flex:1;text-align:right;font-weight:600">{_fmt(qtd)}</div><div style="flex:1;text-align:right;color:#888;font-size:0.8rem">{pct:.0f}%</div><div style="flex:2;padding-left:8px"><div style="background:#e8e8e8;border-radius:4px;height:10px"><div style="background:{sc};border-radius:4px;height:10px;width:{bar_w:.0f}%"></div></div></div></div>'

        hdr = f'<div style="display:flex;padding:4px 8px;border-bottom:2px solid #ddd"><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase">Status</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">Qtd</div><div style="flex:1;text-align:right;font-size:0.6rem;color:#999;text-transform:uppercase">%</div><div style="flex:2;font-size:0.6rem;color:#999;text-transform:uppercase;padding-left:8px">Distribuicao</div></div>'

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:14px 18px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-left:5px solid {cor}">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
<span style="font-weight:700;color:{cor};font-size:0.95rem">{label}</span>
<span style="font-size:0.8rem;font-weight:600;color:#1a1a2e">{_fmt(total)} leads</span>
</div>
{hdr}{rows}
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # ========================================
    # SUBSECAO 4: EVOLUCAO MES A MES por empresa
    # ========================================
    st.markdown("### Evolucao Mes a Mes", anchor="evolucao")

    meses_ex = []
    mx, ax = m, a
    for _ in range(6):
        meses_ex.append((ax, mx))
        mx -= 1
        if mx == 0: mx, ax = 12, ax-1
    meses_ex.reverse()

    for emp in empresas_ex:
        cor = CORES.get(emp,{}).get("primaria","#1a1a2e")
        label = EMPRESA_LABELS.get(emp,emp)
        tab = []
        for (ano, mes) in meses_ex:
            du = dias_uteis_no_mes(ano, mes)
            lq = _g(leads_t, emp, ano, mes)
            cm = _g(conv_m, emp, ano, mes)
            cc = _g(leads_cc, emp, ano, mes)
            f1 = (cc/lq*100) if lq > 0 else 0
            ct = _g(contas_d, emp, ano, mes)
            tab.append({"Mes": f"{MESES_PT[mes]}/{ano}", "DU": du, "Leads": int(lq), "Conv": int(cm), "%F1": f"{f1:.1f}%", "Contas": int(ct)})
        st.markdown(f'<div style="border-left:4px solid {cor};padding-left:10px;margin:8px 0 4px 0;font-weight:600;color:{cor}">{label}</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(tab), width="stretch", hide_index=True)

except Exception as e:
    st.error(f"Erro: {e}")
    import traceback
    st.code(traceback.format_exc())
