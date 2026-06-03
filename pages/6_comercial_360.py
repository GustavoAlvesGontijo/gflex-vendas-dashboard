"""
Pagina 6 — Comercial 360
Mapa de gargalos + acompanhamento Diario/Semanal/Mensal/Custom.
Scoreboard auto-expandido (Energy em 4 sub-linhas: Interno/Externo/Repres/MT).
Filtros Yago aplicados silenciosamente (excl. Pos Venda + concessionaria != Elektro).
Drill-down quando empresa selecionada: funil + breakdown + perdas + pipeline.
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
from config import EMPRESAS, EMPRESA_LABELS, CORES, MESES_PT_FULL
from components import page_header, icon
from salesforce_client import (
    get_leads_criados_unificado,
    get_leads_convertidos_unificado,
    get_opps_criadas_unificado,
    get_opps_em_fase_unificado,
    get_opps_ganhas_unificado,
    get_energy_kwh_unificado,
    # Novas — refinadas para Comercial 360
    get_energy_opps_por_casa_unificado,
    get_energy_kwh_por_casa_unificado,
    get_energy_leads_por_casa_unificado,
    get_energy_leads_conv_por_casa_unificado,
    get_perdas_unificado,
    get_pipeline_aberto_snapshot,
    get_pipeline_aberto_energy_kwh_snapshot,
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
def _pct_diff(atual, anterior):
    if not anterior or anterior == 0: return None
    return ((atual - anterior) / anterior) * 100

# ============================================================
# Casa de vendas Energy — classifica via Owner.Title + Tipo_de_Conta
# ============================================================
ENERGY = "Flex Energy"
CASAS = ["Interno", "Externo", "Representantes", "Média Tensão"]

def classificar_casa(title: str, tipo_conta: str) -> str:
    """Aplica regras dos dashboards SF para classificar a casa."""
    t = (tipo_conta or "").strip()
    titlel = (title or "").lower()
    if t == "Média Tensão":
        return "Média Tensão"
    if "interno" in titlel:
        return "Interno"
    if "externo" in titlel:
        return "Externo"
    if "representante" in titlel:
        return "Representantes"
    return "Outros"

# ============================================================
# Periodo + filtros UI
# ============================================================
st.markdown(page_header(
    title="Comercial 360 — Mapa de Gargalos",
    subtitle="Acompanhamento Diário · Semanal · Mensal · Custom · com split Energy por Casa de Vendas",
), unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1.3, 1.6, 1.6, 1.5])
hoje = date.today()
with c1:
    modo = st.selectbox(
        "Período",
        ["Hoje", "Esta semana", "Este mês", "Mês passado", "Últimos 7 dias", "Últimos 30 dias", "Custom"],
        index=2, key="c360_modo",
    )

if modo == "Hoje":
    di = df = hoje; di_ant = df_ant = hoje - timedelta(days=1)
elif modo == "Esta semana":
    di = hoje - timedelta(days=hoje.weekday()); df = di + timedelta(days=6)
    di_ant = di - timedelta(days=7); df_ant = di_ant + timedelta(days=6)
elif modo == "Este mês":
    di = date(hoje.year, hoje.month, 1); df = hoje
    if hoje.month == 1:
        di_ant = date(hoje.year-1, 12, 1); df_ant = date(hoje.year-1, 12, hoje.day)
    else:
        di_ant = date(hoje.year, hoje.month-1, 1)
        prev_last = (date(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        df_ant = date(hoje.year, hoje.month-1, min(hoje.day, prev_last))
elif modo == "Mês passado":
    if hoje.month == 1:
        di = date(hoje.year-1, 12, 1); df = date(hoje.year-1, 12, 31)
    else:
        di = date(hoje.year, hoje.month-1, 1)
        last_day = (date(hoje.year, hoje.month, 1) - timedelta(days=1)).day
        df = date(hoje.year, hoje.month-1, last_day)
    # anterior = 2 meses atras
    m2 = di.month - 1 if di.month > 1 else 12
    a2 = di.year if di.month > 1 else di.year - 1
    di_ant = date(a2, m2, 1)
    last_ant = (date(di.year, di.month, 1) - timedelta(days=1)).day
    df_ant = date(a2, m2, last_ant)
elif modo == "Últimos 7 dias":
    di = hoje - timedelta(days=6); df = hoje
    di_ant = di - timedelta(days=7); df_ant = di_ant + timedelta(days=6)
elif modo == "Últimos 30 dias":
    di = hoje - timedelta(days=29); df = hoje
    di_ant = di - timedelta(days=30); df_ant = di_ant + timedelta(days=29)
else:
    di = df = hoje; di_ant = df_ant = hoje - timedelta(days=1)

with c2:
    if modo == "Custom":
        di = st.date_input("Início", value=hoje - timedelta(days=7), key="c360_di")
        delta = (df - di).days if isinstance(df, date) else 0
    else:
        st.markdown(f'<div style="padding-top:30px;font-size:0.85rem"><span style="color:var(--text-muted)">De:</span> <b>{di.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

with c3:
    if modo == "Custom":
        df = st.date_input("Fim", value=hoje, key="c360_df")
        di_ant = di - timedelta(days=(df-di).days+1); df_ant = di - timedelta(days=1)
    else:
        st.markdown(f'<div style="padding-top:30px;font-size:0.85rem"><span style="color:var(--text-muted)">Até:</span> <b>{df.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

with c4:
    empresas_opcoes = ["TODAS"] + EMPRESAS
    empresa_sel = st.selectbox(
        "Empresa (drill-down)",
        empresas_opcoes,
        format_func=lambda e: "TODAS" if e == "TODAS" else EMPRESA_LABELS.get(e, e),
        index=0, key="c360_empresa",
    )

dias_periodo = (df - di).days + 1

# Banner: filtros Yago aplicados
st.markdown(
    '<div style="display:flex;align-items:center;gap:10px;padding:9px 14px;background:#10b98112;'
    'border:1px solid #10b98130;border-radius:8px;margin-bottom:18px;font-size:0.78rem">'
    f'{icon("scale",14,"#059669")}'
    '<div><b style="color:#059669">Filtros Yago aplicados:</b> '
    '<span style="color:var(--text-secondary)">exclui Pós-Venda · exclui concessionária Elektro (Energy) · '
    f'comparativo vs período equivalente anterior ({di_ant.strftime("%d/%m")} a {df_ant.strftime("%d/%m")})</span></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ============================================================
# CARGA DE DADOS
# ============================================================
try:
    with st.spinner(f"Carregando dados de {di.strftime('%d/%m')} a {df.strftime('%d/%m')} e comparativo..."):
        # Periodo atual
        df_lc = get_leads_criados_unificado(di, df)
        df_lconv = get_leads_convertidos_unificado(di, df)
        df_oc = get_opps_criadas_unificado(di, df)
        df_oneg = get_opps_em_fase_unificado(di, df, "Negociação")
        df_oct = get_opps_em_fase_unificado(di, df, "Contrato")
        df_og = get_opps_ganhas_unificado(di, df)
        df_perdas = get_perdas_unificado(di, df)
        df_pipe = get_pipeline_aberto_snapshot()
        # Periodo anterior (so vendas - para vs anterior do scoreboard)
        df_og_ant = get_opps_ganhas_unificado(di_ant, df_ant)
        # Energy kWh
        kwh_ganhas = get_energy_kwh_unificado(di, df, "ganhas")
        kwh_ganhas_ant = get_energy_kwh_unificado(di_ant, df_ant, "ganhas")
        kwh_pipe = get_pipeline_aberto_energy_kwh_snapshot()
        # Energy por casa
        e_op_criadas = get_energy_opps_por_casa_unificado(di, df, "criadas")
        e_op_neg = get_energy_opps_por_casa_unificado(di, df, "negociacao")
        e_op_ct = get_energy_opps_por_casa_unificado(di, df, "contrato")
        e_op_ganhas = get_energy_opps_por_casa_unificado(di, df, "ganhas")
        e_op_ganhas_ant = get_energy_opps_por_casa_unificado(di_ant, df_ant, "ganhas")
        e_kwh_ganhas = get_energy_kwh_por_casa_unificado(di, df, "ganhas")
        e_kwh_ganhas_ant = get_energy_kwh_por_casa_unificado(di_ant, df_ant, "ganhas")
        e_leads = get_energy_leads_por_casa_unificado(di, df)
        e_leads_conv = get_energy_leads_conv_por_casa_unificado(di, df)

    # ============================================================
    # Agregacoes basicas por empresa
    # ============================================================
    def _agg(df_in, col="total"):
        if df_in is None or df_in.empty: return {}
        return df_in.groupby("Empresa_Proprietaria__c")[col].sum().to_dict()
    def _agg_v(df_in):
        if df_in is None or df_in.empty: return {}, {}
        g = df_in.groupby("Empresa_Proprietaria__c").agg({"total":"sum","valor":"sum"})
        return g["total"].to_dict(), g["valor"].to_dict()

    leads = _agg(df_lc); conv = _agg(df_lconv)
    opps_q, opps_v = _agg_v(df_oc)
    neg_q, neg_v = _agg_v(df_oneg)
    ct_q, ct_v = _agg_v(df_oct)
    gan_q, gan_v = _agg_v(df_og)
    gan_q_ant, gan_v_ant = _agg_v(df_og_ant)

    # Pipeline snapshot
    pipe_q, pipe_v = {}, {}
    if not df_pipe.empty:
        g = df_pipe.groupby("Empresa_Proprietaria__c").agg({"total":"sum","valor":"sum"})
        pipe_q = g["total"].to_dict(); pipe_v = g["valor"].to_dict()

    # Energy totais consolidados (todas casas)
    energy_kwh_ganhas = float(kwh_ganhas["kwh"].sum()) if not kwh_ganhas.empty else 0
    energy_kwh_ganhas_ant = float(kwh_ganhas_ant["kwh"].sum()) if not kwh_ganhas_ant.empty else 0
    energy_kwh_pipe = float(kwh_pipe["kwh"].sum()) if not kwh_pipe.empty else 0

    # ============================================================
    # Energy: agrupar por CASA (Interno/Externo/Repres/MT)
    # ============================================================
    def agrega_por_casa(df_in, valor_col="valor"):
        """Retorna {casa: {'qtd': int, 'valor': float}} a partir de df com title+tipo_conta."""
        out = {c: {"qtd": 0, "valor": 0.0} for c in CASAS}
        if df_in is None or df_in.empty: return out
        for _, r in df_in.iterrows():
            casa = classificar_casa(r.get("title", ""), r.get("tipo_conta", ""))
            if casa == "Outros": continue
            out[casa]["qtd"] += int(r.get("total", 0))
            v = r.get(valor_col, 0)
            out[casa]["valor"] += float(v) if v and not pd.isna(v) else 0
        return out

    def agrega_kwh_por_casa(df_in):
        out = {c: {"qtd": 0, "kwh": 0.0} for c in CASAS}
        if df_in is None or df_in.empty: return out
        for _, r in df_in.iterrows():
            casa = classificar_casa(r.get("title", ""), r.get("tipo_conta", ""))
            if casa == "Outros": continue
            out[casa]["qtd"] += int(r.get("opps", 0))
            k = r.get("kwh", 0)
            out[casa]["kwh"] += float(k) if k and not pd.isna(k) else 0
        return out

    def agrega_leads_por_casa(df_in):
        out = {c: 0 for c in CASAS}
        if df_in is None or df_in.empty: return out
        for _, r in df_in.iterrows():
            casa = classificar_casa(r.get("title", ""), r.get("tipo_conta", ""))
            if casa == "Outros": continue
            out[casa] += int(r.get("total", 0))
        return out

    e_casa_criadas = agrega_por_casa(e_op_criadas)
    e_casa_neg = agrega_por_casa(e_op_neg)
    e_casa_ct = agrega_por_casa(e_op_ct)
    e_casa_ganhas = agrega_por_casa(e_op_ganhas)
    e_casa_ganhas_ant = agrega_por_casa(e_op_ganhas_ant)
    e_casa_kwh_ganhas = agrega_kwh_por_casa(e_kwh_ganhas)
    e_casa_kwh_ganhas_ant = agrega_kwh_por_casa(e_kwh_ganhas_ant)
    e_casa_leads = agrega_leads_por_casa(e_leads)
    e_casa_leads_conv = agrega_leads_por_casa(e_leads_conv)

    # ============================================================
    # SCOREBOARD MACRO
    # Linhas: Energy (consolidada) + 4 sub-linhas casas + 5 outras empresas
    # ============================================================
    st.markdown(
        '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
        f'{icon("list-checks",18,"var(--accent)")} SCOREBOARD MACRO</h3>'
        f'<p class="gx-subtle">Período: <b>{di.strftime("%d/%m/%Y")} a {df.strftime("%d/%m/%Y")}</b> ({dias_periodo} dia{"s" if dias_periodo>1 else ""}) · '
        f'Energy expandida por Casa de Vendas · variação vs <b>{di_ant.strftime("%d/%m")}–{df_ant.strftime("%d/%m")}</b></p>',
        unsafe_allow_html=True,
    )

    def _vbadge(p):
        if p is None: return '<span style="color:var(--text-muted);font-size:0.65rem">—</span>'
        if abs(p) < 1: return f'<span style="color:var(--text-muted);font-size:0.65rem">{p:+.0f}%</span>'
        pos = p > 0
        col = "#059669" if pos else "#dc2626"
        bg = "#10b98118" if pos else "#dc262618"
        arr = "↑" if pos else "↓"
        return f'<span style="display:inline-flex;align-items:center;gap:2px;padding:1px 6px;border-radius:5px;background:{bg};color:{col};font-size:0.65rem;font-weight:700">{arr} {p:+.0f}%</span>'

    def _gargalo_label(leads_v, conv_v, opps_v, neg_v, ct_v, gan_v):
        """Detecta a transicao com maior queda (gargalo principal)."""
        TRANS = [
            ("Qualificação", leads_v, conv_v),
            ("Conversão→Opp", conv_v, opps_v),
            ("Avanço Negoc.", opps_v, neg_v),
            ("Avanço Contr.", neg_v, ct_v),
            ("Fechamento", ct_v, gan_v),
        ]
        worst = None; worst_q = 0
        for lab, src, dst in TRANS:
            if src >= 3:  # so considera onde ha volume minimo
                queda = 100 - (dst/src*100) if src > 0 else 0
                if queda > worst_q:
                    worst_q = queda; worst = lab
        if worst and worst_q >= 50:
            return f'<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 7px;background:#dc262615;color:#dc2626;border-radius:5px;font-size:0.68rem;font-weight:700">⚠️ {worst} ({-worst_q:.0f}%)</span>'
        return '<span style="color:var(--text-muted);font-size:0.7rem">—</span>'

    sb_html = '<div style="background:var(--bg-card);border-radius:12px;box-shadow:var(--shadow-md);overflow:hidden;margin-bottom:24px">'
    # Header
    sb_html += (
        '<div style="display:grid;grid-template-columns:1.5fr 0.55fr 0.55fr 0.55fr 0.55fr 0.55fr 0.65fr 0.9fr 0.6fr 1.1fr;'
        'gap:0;padding:11px 14px;background:#1a1a2e;color:white;font-size:0.62rem;font-weight:700;'
        'text-transform:uppercase;letter-spacing:0.5px">'
        '<div>Empresa · Casa</div>'
        '<div style="text-align:right">Leads</div>'
        '<div style="text-align:right">Conv</div>'
        '<div style="text-align:right">Opps</div>'
        '<div style="text-align:right">Neg</div>'
        '<div style="text-align:right">Contr</div>'
        '<div style="text-align:right">Vend</div>'
        '<div style="text-align:right">Volume</div>'
        '<div style="text-align:right">vs Ant</div>'
        '<div style="padding-left:8px">Gargalo</div>'
        '</div>'
    )

    def _cell(v, align="right"):
        return (f'<div style="text-align:{align};padding:8px 8px;color:var(--text);'
                f'font-weight:700;font-feature-settings:\'tnum\';font-size:0.86rem">{_fmt(v)}</div>')

    def _row(label, lv, cv, ov, nv, ctv, gv, vol_fmt, var_pct, gargalo_html, cor, sub=False, leftpad=""):
        nome_html = (
            f'<div style="padding:8px 14px;display:flex;align-items:center;gap:6px;'
            f'{"border-left:3px solid "+cor if not sub else ""};'
            f'{"padding-left:32px" if sub else ""};{leftpad}">'
            f'<span style="{"color:var(--text-muted);font-size:0.78rem" if sub else "color:var(--text);font-weight:700;font-size:0.86rem"}">'
            f'{"└ " if sub else ""}{label}</span></div>'
        )
        return (
            '<div style="display:grid;grid-template-columns:1.5fr 0.55fr 0.55fr 0.55fr 0.55fr 0.55fr 0.65fr 0.9fr 0.6fr 1.1fr;'
            f'gap:0;border-top:1px solid var(--border);align-items:center;{"background:var(--bg-overlay)" if sub else ""}">'
            f'{nome_html}'
            f'{_cell(lv)}{_cell(cv)}{_cell(ov)}{_cell(nv)}{_cell(ctv)}{_cell(gv)}'
            f'<div style="text-align:right;padding:8px 8px;color:{cor};font-weight:700;'
            f'font-feature-settings:\'tnum\';font-size:0.82rem">{vol_fmt}</div>'
            f'<div style="text-align:right;padding:8px 6px">{_vbadge(var_pct)}</div>'
            f'<div style="padding:8px 10px">{gargalo_html}</div>'
            '</div>'
        )

    # Linha Energy consolidada
    cor_e = CORES[ENERGY]["primaria"]
    e_l_tot = sum(e_casa_leads.values())
    e_c_tot = sum(e_casa_leads_conv.values())
    e_o_tot = sum(x["qtd"] for x in e_casa_criadas.values())
    e_n_tot = sum(x["qtd"] for x in e_casa_neg.values())
    e_ct_tot = sum(x["qtd"] for x in e_casa_ct.values())
    e_g_tot = sum(x["qtd"] for x in e_casa_ganhas.values())
    e_kwh_tot = sum(x["kwh"] for x in e_casa_kwh_ganhas.values())
    e_kwh_ant_tot = sum(x["kwh"] for x in e_casa_kwh_ganhas_ant.values())
    sb_html += _row(
        EMPRESA_LABELS[ENERGY], e_l_tot, e_c_tot, e_o_tot, e_n_tot, e_ct_tot, e_g_tot,
        _fk(e_kwh_tot), _pct_diff(e_kwh_tot, e_kwh_ant_tot),
        _gargalo_label(e_l_tot, e_c_tot, e_o_tot, e_n_tot, e_ct_tot, e_g_tot),
        cor_e,
    )
    # 4 sub-linhas casas
    for casa in CASAS:
        lv = e_casa_leads.get(casa, 0)
        cv = e_casa_leads_conv.get(casa, 0)
        ov = e_casa_criadas[casa]["qtd"]
        nv = e_casa_neg[casa]["qtd"]
        ctv = e_casa_ct[casa]["qtd"]
        gv = e_casa_ganhas[casa]["qtd"]
        kwh_v = e_casa_kwh_ganhas[casa]["kwh"]
        kwh_v_ant = e_casa_kwh_ganhas_ant[casa]["kwh"]
        sb_html += _row(
            casa, lv, cv, ov, nv, ctv, gv,
            _fk(kwh_v), _pct_diff(kwh_v, kwh_v_ant),
            _gargalo_label(lv, cv, ov, nv, ctv, gv),
            cor_e, sub=True,
        )

    # Demais empresas
    for emp in EMPRESAS:
        if emp == ENERGY: continue
        cor = CORES[emp]["primaria"]
        lv = int(leads.get(emp, 0)); cv = int(conv.get(emp, 0))
        ov = int(opps_q.get(emp, 0)); nv = int(neg_q.get(emp, 0))
        ctv = int(ct_q.get(emp, 0)); gv = int(gan_q.get(emp, 0))
        gv_val = float(gan_v.get(emp, 0)); gv_val_ant = float(gan_v_ant.get(emp, 0))
        sb_html += _row(
            EMPRESA_LABELS[emp], lv, cv, ov, nv, ctv, gv,
            _fv(gv_val), _pct_diff(gv_val, gv_val_ant),
            _gargalo_label(lv, cv, ov, nv, ctv, gv),
            cor,
        )
    sb_html += '</div>'
    st.markdown(sb_html, unsafe_allow_html=True)

    # ============================================================
    # DRILL DOWN (quando empresa selecionada)
    # ============================================================
    if empresa_sel != "TODAS":
        emp = empresa_sel
        cor = CORES[emp]["primaria"]
        is_e = (emp == ENERGY)

        st.markdown(
            f'<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px;margin-top:28px">'
            f'{icon("chart",18,cor)} DRILL DOWN — {EMPRESA_LABELS[emp]}</h3>'
            '<p class="gx-subtle">Funil visual + breakdown por dimensão chave + perdas + pipeline</p>',
            unsafe_allow_html=True,
        )

        # Funil vertical (mesma logica do anterior)
        if is_e:
            vals = {
                "leads": e_l_tot, "conv": e_c_tot, "opps": e_o_tot,
                "neg": e_n_tot, "ct": e_ct_tot, "ganhas": e_g_tot,
            }
            vol_atual = e_kwh_tot
            vol_fmt_f = _fk
        else:
            vals = {
                "leads": int(leads.get(emp, 0)), "conv": int(conv.get(emp, 0)),
                "opps": int(opps_q.get(emp, 0)), "neg": int(neg_q.get(emp, 0)),
                "ct": int(ct_q.get(emp, 0)), "ganhas": int(gan_q.get(emp, 0)),
            }
            vol_atual = float(gan_v.get(emp, 0))
            vol_fmt_f = _fv

        ETAPAS = [("leads","Leads Criados","#3b82f6"),("conv","Convertidos","#10b981"),
                  ("opps","Opps Criadas","#8b5cf6"),("neg","Em Negociação","#f97316"),
                  ("ct","Contratos","#eab308"),("ganhas","Vendas","#059669")]
        mx = max(vals.values()) if max(vals.values()) > 0 else 1
        funil_rows = ""
        for i, (k, lab, ec) in enumerate(ETAPAS):
            v = vals[k]
            pct_bar = (v/mx*100) if mx > 0 else 0
            taxa = ""
            if i < len(ETAPAS)-1:
                nx = vals[ETAPAS[i+1][0]]
                if v >= 3:
                    ret = (nx/v*100) if v > 0 else 0
                    queda = 100 - ret
                    alert = queda >= 80
                    tcor = "#dc2626" if alert else ("#059669" if ret >= 50 else "#888")
                    arrow = "↓" if alert else "→"
                    taxa = (f'<div style="margin-left:160px;padding:2px 0 4px 8px;font-size:0.65rem;'
                            f'color:{tcor};font-weight:700">{arrow} {ret:.0f}% retém · perde {queda:.0f}%'
                            f'{" — GARGALO" if alert else ""}</div>')
            funil_rows += (
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">'
                f'<div style="width:145px;font-size:0.78rem;color:var(--text-secondary);font-weight:600;text-align:right">{lab}</div>'
                '<div style="flex:1;height:28px;background:var(--bg-overlay);border-radius:6px;position:relative;overflow:hidden">'
                f'<div style="height:100%;width:{pct_bar}%;background:linear-gradient(90deg,{ec},{ec}cc);border-radius:6px;min-width:3px"></div>'
                f'<div style="position:absolute;top:0;left:12px;right:12px;line-height:28px;font-size:0.88rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\'">{_fmt(v)}</div>'
                '</div></div>'
                f'{taxa}'
            )
        st.markdown(
            f'<div class="gx-card" style="border-left:4px solid {cor};margin-bottom:14px">'
            f'<div style="font-weight:700;color:{cor};font-size:1rem;margin-bottom:14px;display:flex;align-items:center;gap:8px">'
            f'{icon("chart",16,cor)} Funil do período · Volume: <b>{vol_fmt_f(vol_atual)}</b></div>'
            f'{funil_rows}</div>',
            unsafe_allow_html=True,
        )

        # Breakdown: Energy por casa, Locações por origem, demais por origem do periodo
        if is_e:
            st.markdown(
                f'<h4 style="margin-top:18px;font-size:0.95rem;color:var(--text);display:flex;align-items:center;gap:8px">'
                f'{icon("users",15,cor)} Breakdown por Casa de Vendas</h4>',
                unsafe_allow_html=True,
            )
            tbl = '<div style="background:var(--bg-card);border-radius:10px;overflow:hidden;box-shadow:var(--shadow-sm);margin-bottom:16px">'
            tbl += ('<div style="display:grid;grid-template-columns:1.4fr 0.6fr 0.6fr 0.6fr 0.6fr 0.6fr 0.6fr 0.9fr;gap:0;'
                    'padding:9px 14px;background:#1a1a2e;color:white;font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">'
                    '<div>Casa</div><div style="text-align:right">Leads</div><div style="text-align:right">Conv</div>'
                    '<div style="text-align:right">Opps</div><div style="text-align:right">Neg</div>'
                    '<div style="text-align:right">Contr</div><div style="text-align:right">Vend</div>'
                    '<div style="text-align:right">kWh</div></div>')
            for casa in CASAS:
                tbl += ('<div style="display:grid;grid-template-columns:1.4fr 0.6fr 0.6fr 0.6fr 0.6fr 0.6fr 0.6fr 0.9fr;gap:0;'
                        'border-top:1px solid var(--border);padding:8px 14px;font-size:0.82rem">'
                        f'<div style="font-weight:600;color:var(--text)">{casa}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_leads.get(casa,0))}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_leads_conv.get(casa,0))}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_criadas[casa]["qtd"])}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_neg[casa]["qtd"])}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_ct[casa]["qtd"])}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(e_casa_ganhas[casa]["qtd"])}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\';color:{cor};font-weight:700">{_fk(e_casa_kwh_ganhas[casa]["kwh"])}</div>'
                        '</div>')
            tbl += '</div>'
            st.markdown(tbl, unsafe_allow_html=True)
        else:
            # Para outras empresas: breakdown por origem do periodo
            st.markdown(
                f'<h4 style="margin-top:18px;font-size:0.95rem;color:var(--text);display:flex;align-items:center;gap:8px">'
                f'{icon("file-text",15,cor)} Breakdown por Origem (Opps criadas)</h4>',
                unsafe_allow_html=True,
            )
            if not df_oc.empty:
                emp_oc = df_oc[df_oc["Empresa_Proprietaria__c"] == emp]
                if not emp_oc.empty:
                    by_o = emp_oc.groupby("LeadSource").agg({"total":"sum","valor":"sum"}).sort_values("valor", ascending=False)
                    tbl = '<div style="background:var(--bg-card);border-radius:10px;overflow:hidden;box-shadow:var(--shadow-sm);margin-bottom:16px">'
                    tbl += ('<div style="display:grid;grid-template-columns:2fr 0.7fr 1fr;gap:0;'
                            'padding:9px 14px;background:#1a1a2e;color:white;font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">'
                            '<div>Origem</div><div style="text-align:right">Qtd</div><div style="text-align:right">Valor</div></div>')
                    for origem, r in by_o.iterrows():
                        tbl += ('<div style="display:grid;grid-template-columns:2fr 0.7fr 1fr;gap:0;'
                                'border-top:1px solid var(--border);padding:8px 14px;font-size:0.85rem">'
                                f'<div style="color:var(--text)">{origem or "(sem origem)"}</div>'
                                f'<div style="text-align:right;font-feature-settings:\'tnum\';font-weight:600">{_fmt(int(r["total"]))}</div>'
                                f'<div style="text-align:right;font-feature-settings:\'tnum\';color:{cor};font-weight:700">{_fv(float(r["valor"] or 0))}</div>'
                                '</div>')
                    tbl += '</div>'
                    st.markdown(tbl, unsafe_allow_html=True)

        # Perdas com top motivos
        if not df_perdas.empty:
            perdas_emp = df_perdas[df_perdas["Empresa_Proprietaria__c"] == emp]
            if not perdas_emp.empty:
                by_m = perdas_emp.groupby("motivo").agg({"total":"sum","valor":"sum"}).sort_values("total", ascending=False).head(8)
                tot_p = int(perdas_emp["total"].sum())
                val_p = float(perdas_emp["valor"].sum())
                st.markdown(
                    f'<h4 style="margin-top:18px;font-size:0.95rem;color:var(--text);display:flex;align-items:center;gap:8px">'
                    f'{icon("trending-down",15,"#dc2626")} Perdas no período · <b>{tot_p}</b> opps · <b>{_fv(val_p)}</b></h4>',
                    unsafe_allow_html=True,
                )
                tbl = '<div style="background:var(--bg-card);border-radius:10px;overflow:hidden;box-shadow:var(--shadow-sm);margin-bottom:16px">'
                tbl += ('<div style="display:grid;grid-template-columns:2.4fr 0.6fr 0.9fr;gap:0;padding:8px 14px;background:#1a1a2e;color:white;font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">'
                        '<div>Motivo</div><div style="text-align:right">Qtd</div><div style="text-align:right">Valor</div></div>')
                for motivo, r in by_m.iterrows():
                    pct = int(r["total"])/tot_p*100 if tot_p else 0
                    tbl += ('<div style="display:grid;grid-template-columns:2.4fr 0.6fr 0.9fr;gap:0;border-top:1px solid var(--border);padding:7px 14px;font-size:0.82rem">'
                            f'<div style="color:var(--text)">{motivo or "(sem motivo)"} <span style="color:var(--text-muted);font-size:0.7rem">({pct:.0f}%)</span></div>'
                            f'<div style="text-align:right;font-weight:600;font-feature-settings:\'tnum\'">{_fmt(int(r["total"]))}</div>'
                            f'<div style="text-align:right;font-feature-settings:\'tnum\';color:#dc2626">{_fv(float(r["valor"] or 0))}</div>'
                            '</div>')
                tbl += '</div>'
                st.markdown(tbl, unsafe_allow_html=True)

        # Pipeline atual snapshot
        st.markdown(
            f'<h4 style="margin-top:18px;font-size:0.95rem;color:var(--text);display:flex;align-items:center;gap:8px">'
            f'{icon("list-checks",15,cor)} Pipeline aberto agora (snapshot)</h4>',
            unsafe_allow_html=True,
        )
        if not df_pipe.empty:
            pipe_emp = df_pipe[df_pipe["Empresa_Proprietaria__c"] == emp]
            if not pipe_emp.empty:
                # ordenar pelas fases canonicas
                fase_ordem = ["Novo","Em Análise","Contato Ativo","Contato Passivo","Em Cotação","Negociação","Contrato"]
                pipe_emp = pipe_emp.copy()
                pipe_emp["ordem"] = pipe_emp["StageName"].apply(lambda s: fase_ordem.index(s) if s in fase_ordem else 99)
                pipe_emp = pipe_emp.sort_values("ordem")
                tot_p_qtd = int(pipe_emp["total"].sum())
                tot_p_val = float(pipe_emp["valor"].sum())
                tbl = '<div style="background:var(--bg-card);border-radius:10px;overflow:hidden;box-shadow:var(--shadow-sm);margin-bottom:16px">'
                tbl += ('<div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr;gap:0;padding:8px 14px;background:#1a1a2e;color:white;font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">'
                        '<div>Fase</div><div style="text-align:right">Opps</div><div style="text-align:right">Valor</div></div>')
                for _, r in pipe_emp.iterrows():
                    tbl += ('<div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr;gap:0;border-top:1px solid var(--border);padding:7px 14px;font-size:0.85rem">'
                            f'<div style="color:var(--text)">{r["StageName"]}</div>'
                            f'<div style="text-align:right;font-weight:600;font-feature-settings:\'tnum\'">{_fmt(int(r["total"]))}</div>'
                            f'<div style="text-align:right;font-feature-settings:\'tnum\';color:{cor};font-weight:700">{_fv(float(r["valor"] or 0))}</div>'
                            '</div>')
                tbl += ('<div style="display:grid;grid-template-columns:1.6fr 0.6fr 1fr;gap:0;border-top:2px solid var(--border-strong);padding:9px 14px;font-size:0.88rem;font-weight:800;background:var(--bg-overlay)">'
                        '<div>TOTAL</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\'">{_fmt(tot_p_qtd)}</div>'
                        f'<div style="text-align:right;font-feature-settings:\'tnum\';color:{cor}">{_fv(tot_p_val)}</div>'
                        '</div></div>')
                st.markdown(tbl, unsafe_allow_html=True)

    # Nota tecnica
    st.markdown(
        '<div style="margin-top:20px;padding:11px 14px;background:var(--bg-subtle);border-radius:8px;font-size:0.72rem;color:var(--text-muted);line-height:1.55">'
        '<b style="color:var(--text)">Notas técnicas:</b> '
        '"Em Negociação" e "Contratos" = opps atualmente nessas fases com mudança no período (via LastStageChangeDate). '
        'Energy: Casa = Owner.Title (Interno/Externo/Representante) + Tipo_de_Conta_ENERGY = "Média Tensão" override. '
        'Filtros silenciosos: exclui Pos-Venda · exclui concessionária Elektro (Energy) · alinhado com dashboards SF do Yago. '
        'Comparativo "vs Ant" usa período equivalente anterior (mesma quantidade de dias).'
        '</div>',
        unsafe_allow_html=True,
    )

except Exception as e:
    st.error(f"Erro carregando dados: {e}")
    import traceback
    st.code(traceback.format_exc())
