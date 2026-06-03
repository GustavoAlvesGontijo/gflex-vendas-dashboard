"""
Pagina 6 - Acompanhamento (mapeador de gargalos)
Funil visual por empresa: leads -> conv -> opps -> negociacao -> contrato -> vendas.
Cor de alerta na etapa com maior queda. Scoreboard macro no topo.
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
from datetime import date, timedelta
from config import EMPRESAS, EMPRESA_LABELS, CORES
from components import page_header, icon
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
    if not v or pd.isna(v) or v == 0: return "—"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    if not v or pd.isna(v) or v == 0: return "—"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"

# ============================================================
# Periodo + filtros
# ============================================================
ENERGY = "Flex Energy"

st.markdown(page_header(
    title="Acompanhamento - Mapa de Gargalos",
    subtitle="Funil por empresa em qualquer periodo - identifica visualmente onde o fluxo trava",
), unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.4, 1.6, 1.6])
hoje = date.today()
with c1:
    modo = st.selectbox(
        "Periodo",
        ["Hoje", "Esta semana", "Este mes", "Mes passado", "Ultimos 7 dias", "Ultimos 30 dias", "Custom"],
        index=2, key="acomp_modo",
    )

if modo == "Hoje":
    di = df = hoje
elif modo == "Esta semana":
    di = hoje - timedelta(days=hoje.weekday())
    df = di + timedelta(days=6)
elif modo == "Este mes":
    di = date(hoje.year, hoje.month, 1)
    df = hoje
elif modo == "Mes passado":
    if hoje.month == 1:
        di = date(hoje.year - 1, 12, 1); df = date(hoje.year - 1, 12, 31)
    else:
        di = date(hoje.year, hoje.month - 1, 1)
        last_day = (date(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        df = date(hoje.year, hoje.month - 1, last_day)
elif modo == "Ultimos 7 dias":
    di = hoje - timedelta(days=6); df = hoje
elif modo == "Ultimos 30 dias":
    di = hoje - timedelta(days=29); df = hoje
else:
    di = df = hoje

with c2:
    if modo == "Custom":
        di = st.date_input("Data inicio", value=hoje - timedelta(days=7), key="acomp_di")
    else:
        st.markdown(f'<div style="padding-top:30px;font-size:0.85rem"><span style="color:var(--text-muted)">De:</span> <b>{di.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

with c3:
    if modo == "Custom":
        df = st.date_input("Data fim", value=hoje, key="acomp_df")
    else:
        st.markdown(f'<div style="padding-top:30px;font-size:0.85rem"><span style="color:var(--text-muted)">Ate:</span> <b>{df.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

dias_periodo = (df - di).days + 1

# ============================================================
# Dados
# ============================================================
try:
    with st.spinner(f"Carregando dados de {di.strftime('%d/%m')} ate {df.strftime('%d/%m')}..."):
        df_lc = get_leads_criados_unificado(di, df)
        df_lconv = get_leads_convertidos_unificado(di, df)
        df_oc = get_opps_criadas_unificado(di, df)
        df_oneg = get_opps_em_fase_unificado(di, df, "Negociação")
        df_oct = get_opps_em_fase_unificado(di, df, "Contrato")
        df_og = get_opps_ganhas_unificado(di, df)
        kwh_criadas = get_energy_kwh_unificado(di, df, "criadas")
        kwh_negoc = get_energy_kwh_unificado(di, df, "negociacao")
        kwh_contr = get_energy_kwh_unificado(di, df, "contrato")
        kwh_ganhas = get_energy_kwh_unificado(di, df, "ganhas")

    def _agg(df_in, col="total"):
        if df_in is None or df_in.empty: return {}
        return df_in.groupby("Empresa_Proprietaria__c")[col].sum().to_dict()
    def _agg_v(df_in):
        if df_in is None or df_in.empty: return {}, {}
        g = df_in.groupby("Empresa_Proprietaria__c").agg({"total":"sum","valor":"sum"})
        return g["total"].to_dict(), g["valor"].to_dict()

    leads = _agg(df_lc)
    conv = _agg(df_lconv)
    opps_q, opps_v = _agg_v(df_oc)
    neg_q, neg_v = _agg_v(df_oneg)
    ct_q, ct_v = _agg_v(df_oct)
    gan_q, gan_v = _agg_v(df_og)
    energy_kwh = {
        "criadas": float(kwh_criadas["kwh"].sum()) if not kwh_criadas.empty else 0,
        "neg": float(kwh_negoc["kwh"].sum()) if not kwh_negoc.empty else 0,
        "ct": float(kwh_contr["kwh"].sum()) if not kwh_contr.empty else 0,
        "ganhas": float(kwh_ganhas["kwh"].sum()) if not kwh_ganhas.empty else 0,
    }

    # ============================================================
    # Etapas + transicoes do funil
    # ============================================================
    ETAPAS_KEYS = ["leads", "conv", "opps", "neg", "ct", "ganhas"]
    ETAPAS_LABELS = {
        "leads": "Leads Criados",
        "conv":  "Convertidos",
        "opps":  "Opps Criadas",
        "neg":   "Em Negociação",
        "ct":    "Contratos",
        "ganhas":"Vendas",
    }
    TRANSICOES = [
        ("leads",  "conv",   "Qualificação"),
        ("conv",   "opps",   "Conversão→Opp"),
        ("opps",   "neg",    "Avanço p/ Negociação"),
        ("neg",    "ct",     "Avanço p/ Contrato"),
        ("ct",     "ganhas", "Fechamento"),
    ]

    def funil_da_empresa(emp):
        is_e = (emp == ENERGY)
        vals = {
            "leads": int(leads.get(emp, 0)),
            "conv":  int(conv.get(emp, 0)),
            "opps":  int(opps_q.get(emp, 0)),
            "neg":   int(neg_q.get(emp, 0)),
            "ct":    int(ct_q.get(emp, 0)),
            "ganhas":int(gan_q.get(emp, 0)),
        }
        vol = {
            "opps":   energy_kwh["criadas"] if is_e else float(opps_v.get(emp, 0)),
            "neg":    energy_kwh["neg"] if is_e else float(neg_v.get(emp, 0)),
            "ct":     energy_kwh["ct"] if is_e else float(ct_v.get(emp, 0)),
            "ganhas": energy_kwh["ganhas"] if is_e else float(gan_v.get(emp, 0)),
        }
        max_v = max(vals.values()) if max(vals.values()) > 0 else 1
        taxas = []
        for src, dst, label in TRANSICOES:
            sv = vals[src]; dv = vals[dst]
            if sv > 0:
                ret = (dv / sv) * 100
                queda = 100 - ret
                taxas.append({"src": src, "dst": dst, "label": label, "ret": ret, "queda": queda})
            else:
                taxas.append({"src": src, "dst": dst, "label": label, "ret": None, "queda": None})
        validas = [t for t in taxas if t["queda"] is not None and vals[t["src"]] >= 3]
        gargalo = max(validas, key=lambda t: t["queda"]) if validas else None
        return vals, vol, max_v, taxas, gargalo, is_e

    # ============================================================
    # SECAO 1: SCOREBOARD MACRO
    # ============================================================
    st.markdown(
        '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
        f'{icon("list-checks",18,"var(--accent)")} SCOREBOARD MACRO</h3>'
        f'<p class="gx-subtle">Funil resumido por empresa - {dias_periodo} dia(s) · '
        '<span style="color:#dc2626;font-weight:700">vermelho</span> = gargalo principal detectado</p>',
        unsafe_allow_html=True,
    )

    sb_html = '<div style="background:var(--bg-card);border-radius:12px;box-shadow:var(--shadow-md);overflow:hidden;margin-bottom:24px">'
    sb_html += (
        '<div style="display:grid;grid-template-columns:1.4fr 0.7fr 0.7fr 0.7fr 0.7fr 0.7fr 0.7fr 1.4fr;'
        'gap:0;padding:11px 14px;background:#1a1a2e;color:white;font-size:0.65rem;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.6px">'
        '<div>Empresa</div>'
        '<div style="text-align:right">Leads</div>'
        '<div style="text-align:right">Conv</div>'
        '<div style="text-align:right">Opps</div>'
        '<div style="text-align:right">Negoc.</div>'
        '<div style="text-align:right">Contr.</div>'
        '<div style="text-align:right">Vendas</div>'
        '<div style="padding-left:12px">Gargalo principal</div>'
        '</div>'
    )
    for emp in EMPRESAS:
        vals, vol, mx, taxas, gargalo, is_e = funil_da_empresa(emp)
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
        alert_dst = gargalo["dst"] if (gargalo and gargalo["queda"] >= 50) else None
        gargalo_html = (
            '<span style="color:var(--text-muted);font-size:0.72rem">— sem gargalo critico</span>'
            if not gargalo or gargalo["queda"] < 50 else
            f'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 9px;'
            f'background:#dc262615;color:#dc2626;border-radius:5px;font-size:0.72rem;font-weight:700">'
            f'⚠️ {gargalo["label"]} · -{gargalo["queda"]:.0f}%</span>'
        )

        def _cell(val_key, alert=False):
            v = vals[val_key]
            bg = "#dc262610" if alert else "transparent"
            color = "#dc2626" if alert else "var(--text)"
            return (
                f'<div style="text-align:right;padding:9px 8px;background:{bg};color:{color};'
                f'font-weight:700;font-feature-settings:\'tnum\';font-size:0.92rem">{_fmt(v)}</div>'
            )
        sb_html += (
            '<div style="display:grid;grid-template-columns:1.4fr 0.7fr 0.7fr 0.7fr 0.7fr 0.7fr 0.7fr 1.4fr;'
            'gap:0;border-top:1px solid var(--border);align-items:center">'
            f'<div style="padding:9px 14px;display:flex;align-items:center;gap:8px;border-left:3px solid {cor}">'
            f'<span style="font-weight:700;color:var(--text);font-size:0.88rem">{label}</span></div>'
            f'{_cell("leads", alert_dst=="leads")}'
            f'{_cell("conv", alert_dst=="conv")}'
            f'{_cell("opps", alert_dst=="opps")}'
            f'{_cell("neg", alert_dst=="neg")}'
            f'{_cell("ct", alert_dst=="ct")}'
            f'{_cell("ganhas", alert_dst=="ganhas")}'
            f'<div style="padding:9px 12px">{gargalo_html}</div>'
            '</div>'
        )
    sb_html += '</div>'
    st.markdown(sb_html, unsafe_allow_html=True)

    # ============================================================
    # SECAO 2: FUNIL VISUAL DETALHADO POR EMPRESA
    # ============================================================
    st.markdown(
        '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
        f'{icon("chart",18,"var(--accent)")} FUNIL POR EMPRESA</h3>'
        '<p class="gx-subtle">Largura da barra = volume relativo à maior etapa. '
        '<span style="color:#dc2626;font-weight:700">vermelho</span> = queda &gt; 80% · '
        '<span style="color:#059669;font-weight:700">verde</span> = retenção &gt; 50%</p>',
        unsafe_allow_html=True,
    )

    ETAPA_CORES = {
        "leads": "#3b82f6", "conv": "#10b981", "opps": "#8b5cf6",
        "neg": "#f97316", "ct": "#eab308", "ganhas": "#059669",
    }

    for emp in EMPRESAS:
        vals, vol, mx, taxas, gargalo, is_e = funil_da_empresa(emp)
        cor = CORES[emp]["primaria"]
        label = EMPRESA_LABELS[emp]
        gargalo_chip = ""
        if gargalo and gargalo["queda"] >= 50:
            gargalo_chip = (
                f'<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;'
                f'background:#dc262615;color:#dc2626;border-radius:6px;font-size:0.72rem;font-weight:700">'
                f'⚠️ Gargalo: {gargalo["label"]} · -{gargalo["queda"]:.0f}%</span>'
            )
        rows = ""
        for i, k in enumerate(ETAPAS_KEYS):
            v = vals[k]
            ec = ETAPA_CORES[k]
            pct_bar = (v / mx * 100) if mx > 0 else 0
            extra = ""
            if k in vol and v > 0:
                vfmt = _fk(vol[k]) if is_e else _fv(vol[k])
                extra = f' · <span style="color:var(--text-muted);font-weight:500;font-size:0.75rem">{vfmt}</span>'
            taxa_html = ""
            if i < len(ETAPAS_KEYS) - 1:
                t = taxas[i]
                if t["ret"] is not None:
                    alert = (t["queda"] >= 80)
                    tcor = "#dc2626" if alert else ("#059669" if t["ret"] >= 50 else "#888")
                    icone = "↓" if alert else "→"
                    taxa_html = (
                        '<div style="margin-left:155px;padding:2px 0 4px 8px;font-size:0.65rem;'
                        f'color:{tcor};font-weight:700;font-feature-settings:\'tnum\'">'
                        f'{icone} {t["ret"]:.0f}% retem · perde {t["queda"]:.0f}%'
                        f'{" — GARGALO" if alert else ""}</div>'
                    )
            rows += (
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">'
                f'<div style="width:140px;font-size:0.78rem;color:var(--text-secondary);'
                f'font-weight:600;text-align:right">{ETAPAS_LABELS[k]}</div>'
                '<div style="flex:1;height:28px;background:var(--bg-overlay);border-radius:6px;position:relative;overflow:hidden">'
                f'<div style="height:100%;width:{pct_bar}%;background:linear-gradient(90deg,{ec},{ec}cc);'
                f'border-radius:6px;transition:width 0.4s;min-width:3px"></div>'
                f'<div style="position:absolute;top:0;left:12px;right:12px;line-height:28px;'
                f'font-size:0.88rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\'">'
                f'{_fmt(v)}{extra}</div>'
                '</div>'
                '</div>'
                f'{taxa_html}'
            )
        st.markdown(
            f'<div class="gx-card" style="border-left:4px solid {cor};margin-bottom:14px">'
            '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:14px">'
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<div style="width:8px;height:24px;background:{cor};border-radius:3px"></div>'
            f'<span style="font-weight:700;color:{cor};font-size:1.05rem">{label}</span>'
            '</div>'
            f'{gargalo_chip}'
            '</div>'
            f'{rows}'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="margin-top:18px;padding:11px 14px;background:var(--bg-subtle);'
        'border-radius:8px;font-size:0.72rem;color:var(--text-muted);line-height:1.55">'
        '<b style="color:var(--text)">Como ler:</b> '
        'Cada barra representa uma etapa do funil. Largura = volume relativo à maior etapa. '
        '<b>% retem</b> = quantos passaram para a próxima etapa. '
        '<b>Gargalo</b> = etapa com maior perda (vermelho ≥ 80%, alerta ≥ 50%). '
        'Em Negociação e Contratos refletem opps atualmente nessas fases com mudança no período '
        '(aproximação via LastStageChangeDate).'
        '</div>',
        unsafe_allow_html=True,
    )

except Exception as e:
    st.error(f"Erro carregando dados: {e}")
    import traceback
    st.code(traceback.format_exc())
