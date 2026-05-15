"""
Pagina 5 - Fechamento Semanal Comercial
Design inspirado no Hub GFlex: Inter, tabular-nums, cards com borda zinc-200/60,
sombras sutis, ícone-em-quadrado nos cabeçalhos, pílulas como tabs, funil com
barras laranja. Mantém integração SF live (kWh para Flex Energy).

Doc: _Brain/Processos/Flex Energy - Fechamento Semanal Comercial.md
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
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    MESES_PT, MESES_PT_FULL,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    get_logo_b64,
)
from components import icon
from salesforce_client import (
    get_leads_periodo, get_leads_origem_periodo, get_leads_status_periodo,
    get_leads_vendedor_periodo, get_energy_consumo_declarado_periodo,
    get_accounts_criadas_periodo, get_opps_criadas_periodo,
    get_opps_ganhas_periodo, get_energy_kwh_periodo,
    get_pipeline_termometro, get_qualidade_contas_energy,
)


# ============================================================
# CSS extra · estilo Hub GFlex
# ============================================================

st.markdown("""
<style>
/* Cards estilo Hub */
.hub-card {
    background: var(--bg-card);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    border: 1px solid rgba(228,228,231,0.6);
    padding: 18px 20px;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.hub-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
[data-theme="dark"] .hub-card { border-color: #27272a; }

.hub-card-tight { padding: 14px 16px; }

/* Section header estilo Hub */
.hub-section {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 34px 0 18px 0;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(228,228,231,0.7);
}
.hub-section-icon {
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.hub-section-title {
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: var(--text);
    margin: 0;
}
.hub-section-sub {
    font-size: 0.78rem;
    color: var(--text-muted);
    margin: 2px 0 0 0;
}
.hub-section-tag {
    margin-left: auto;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 4px 9px;
    border-radius: 6px;
    background: rgba(244,244,245,0.7);
    border: 1px solid rgba(228,228,231,0.6);
}

/* KPI estilo Hub */
.kpi-hub {
    background: var(--bg-card);
    border: 1px solid rgba(228,228,231,0.6);
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s ease;
    min-height: 108px;
    display: flex; flex-direction: column; justify-content: space-between;
}
.kpi-hub:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.kpi-hub-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}
.kpi-hub-value {
    font-size: 1.75rem;
    font-weight: 600;
    letter-spacing: -0.5px;
    color: var(--text);
    font-feature-settings: 'tnum';
    line-height: 1.1;
}
.kpi-hub-foot {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    margin-top: 10px; font-size: 0.7rem;
}
.kpi-hub-delta {
    display: inline-flex; align-items: center; gap: 3px;
    font-weight: 600; font-feature-settings: 'tnum';
}

/* Pílula tab (estilo Hub period selector) */
.hub-tabs {
    display: inline-flex;
    gap: 2px;
    background: var(--bg-subtle);
    border-radius: 10px;
    padding: 3px;
}
.hub-tab {
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s ease;
    border: none;
    background: transparent;
}
.hub-tab.active {
    background: var(--bg-card);
    color: var(--text);
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* Pillas (semânticas) */
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 100px;
        font-size: 0.68rem; font-weight: 600; font-feature-settings: 'tnum'; letter-spacing: 0.02em; }
.pill-up { background: rgba(249,115,22,0.08); color: #ea580c; }
.pill-down { background: rgba(220,38,38,0.08); color: #dc2626; }
.pill-flat { background: var(--bg-overlay); color: var(--text-muted); }
.pill-good { background: rgba(16,185,129,0.1); color: #047857; }
.pill-warn { background: rgba(245,158,11,0.1); color: #b45309; }
.pill-bad { background: rgba(220,38,38,0.1); color: #b91c1c; }

/* Tabela estilo Hub */
.hub-table {
    width: 100%; border-collapse: collapse; font-size: 0.85rem;
    background: var(--bg-card); border-radius: 12px; overflow: hidden;
    border: 1px solid rgba(228,228,231,0.6);
}
.hub-table thead { background: rgba(244,244,245,0.5); }
.hub-table thead th {
    text-align: left; padding: 10px 14px;
    font-size: 0.66rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: var(--text-muted);
    border-bottom: 1px solid rgba(228,228,231,0.6);
}
.hub-table tbody tr { border-top: 1px solid rgba(228,228,231,0.4); }
.hub-table tbody tr:first-child { border-top: none; }
.hub-table tbody tr:hover { background: var(--bg-overlay); }
.hub-table tbody td { padding: 10px 14px; color: var(--text-secondary); }
.hub-table .num { text-align: right; font-feature-settings: 'tnum'; font-variant-numeric: tabular-nums; }
.hub-table tfoot td {
    padding: 10px 14px; background: var(--bg-subtle);
    font-weight: 600; color: var(--text); border-top: 1px solid rgba(228,228,231,0.6);
}

/* Funil barras */
.funnel-row {
    display: grid; grid-template-columns: 160px 1fr 80px 70px;
    gap: 14px; align-items: center; padding: 9px 0;
    border-bottom: 1px solid rgba(228,228,231,0.4);
}
.funnel-row:last-child { border-bottom: none; }
.funnel-label { font-weight: 500; color: var(--text); font-size: 0.9rem; }
.funnel-bar { height: 26px; background: var(--bg-subtle); border-radius: 6px; overflow: hidden; }
.funnel-bar .fill {
    height: 100%; display: flex; align-items: center; padding: 0 10px;
    color: white; font-weight: 600; font-size: 0.78rem; font-feature-settings: 'tnum';
    transition: width 0.5s ease;
}
.funnel-pct { text-align: right; font-weight: 600; font-feature-settings: 'tnum'; font-size: 0.9rem; }
.funnel-conv { text-align: right; font-size: 0.72rem; color: var(--text-muted); font-feature-settings: 'tnum'; }

/* Termômetro */
.temp-card {
    background: var(--bg-card); border: 1px solid rgba(228,228,231,0.6);
    border-radius: 12px; padding: 14px 16px; min-height: 100px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s ease;
}
.temp-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.temp-card .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.temp-card .label {
    font-size: 0.68rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;
    display: flex; align-items: center;
}
.temp-card .count {
    font-size: 1.75rem; font-weight: 700; letter-spacing: -0.5px;
    color: var(--text); font-feature-settings: 'tnum'; line-height: 1;
}
.temp-card .vol {
    font-size: 0.7rem; color: var(--text-muted); margin-top: 8px;
    font-feature-settings: 'tnum';
}

/* Bloco de meta (estilo Hub mas com gradient próprio) */
.hub-meta {
    background: linear-gradient(135deg, #18181b 0%, #27272a 100%);
    color: #fafafa; padding: 22px 26px; border-radius: 14px;
    display: grid; grid-template-columns: 1fr 320px; gap: 28px; align-items: center;
    margin-top: 10px;
}
.hub-meta .kicker {
    font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.12em;
    opacity: 0.65; margin-bottom: 6px;
}
.hub-meta .main {
    font-size: 2.6rem; font-weight: 700; letter-spacing: -1.5px;
    line-height: 1; font-feature-settings: 'tnum';
}
.hub-meta .sub {
    font-size: 0.78rem; opacity: 0.75; margin-top: 8px;
}
.hub-meta .bar { height: 30px; background: rgba(250,250,247,0.08); border-radius: 8px; overflow: hidden; }
.hub-meta .bar .fill { height: 100%; display: flex; align-items: center; padding: 0 12px;
                       font-size: 0.78rem; font-weight: 700; font-feature-settings: 'tnum'; color: white; }

/* Retro card */
.retro-card {
    background: var(--bg-card); border: 1px solid rgba(228,228,231,0.6);
    border-radius: 12px; padding: 16px 18px; min-height: 130px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.retro-card .num {
    display: inline-block; padding: 2px 7px; border-radius: 6px;
    font-size: 0.66rem; font-weight: 700; font-feature-settings: 'tnum';
    letter-spacing: 0.04em; margin-right: 8px;
}

/* Alerta (gradient amarelo/laranja sutil) */
.hub-alerta {
    background: linear-gradient(135deg, rgba(254,243,212,0.6), rgba(252,232,227,0.4));
    border: 1px solid rgba(245,158,11,0.3); border-left: 4px solid #f59e0b;
    border-radius: 10px; padding: 16px 20px; margin-top: 10px;
    display: grid; grid-template-columns: 36px 1fr; gap: 14px;
}
.hub-alerta .icon { width: 36px; height: 36px; border-radius: 8px;
                    background: #f59e0b; color: white; display: flex; align-items: center;
                    justify-content: center; font-size: 1.3rem; font-weight: 700; }

/* Status bucket */
.status-bucket {
    background: var(--bg-card); border: 1px solid rgba(228,228,231,0.6);
    border-radius: 10px; padding: 12px 14px; text-align: center;
}
.status-bucket .label {
    font-size: 0.66rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 5px;
}
.status-bucket .count {
    font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px;
    font-feature-settings: 'tnum'; line-height: 1;
}
.status-bucket .sub { font-size: 0.62rem; color: var(--text-muted); margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Helpers
# ============================================================

def _fmt(v):
    try: return f"{int(v):,}".replace(",", ".")
    except Exception: return "0"


def _fv(v):
    try: v = float(v)
    except Exception: return "R$ 0"
    if v <= 0: return "R$ 0"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"


def _fk(v):
    try: v = float(v)
    except Exception: return "0 kWh"
    if v <= 0: return "0 kWh"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"


def _delta_pct(atual, anterior):
    try:
        atual = float(atual or 0); anterior = float(anterior or 0)
    except Exception: return None
    if anterior == 0:
        return None if atual > 0 else 0.0
    return (atual - anterior) / anterior * 100


def _delta_pill(p):
    if p is None:
        return '<span class="pill pill-flat">→ —</span>'
    if abs(p) < 1:
        return '<span class="pill pill-flat">→ 0%</span>'
    if p > 0:
        return f'<span class="pill pill-up">↑ +{p:.0f}%</span>'
    return f'<span class="pill pill-down">↓ {p:.0f}%</span>'


def _semana_de(d: date):
    seg = d - timedelta(days=d.weekday())
    return seg, seg + timedelta(days=6)


def _persist_key(empresa: str, semana_seg: date) -> str:
    return f"fech_{empresa.replace(' ', '_').lower()}_{semana_seg.isoformat()}"


def _coalesce_vendedor(df, default="(sem proprietario)"):
    """Garante coluna 'vendedor' no df (fallback se SF nao retornou com alias)."""
    if df.empty: return df
    if "vendedor" not in df.columns:
        for cand in ["Owner.Name", "Name", "expr0"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "vendedor"})
                break
        else:
            df["vendedor"] = default
    df["vendedor"] = df["vendedor"].fillna(default)
    return df


# ============================================================
# Cabeçalho da página · estilo Hub
# ============================================================

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:14px">
  <div style="display:flex;align-items:center;gap:14px">
    <div style="width:44px;height:44px;border-radius:11px;background:rgba(236,133,0,0.1);
                color:#EC8500;display:flex;align-items:center;justify-content:center">
      {icon("file-text", 22, "#EC8500")}
    </div>
    <div>
      <h2 style="font-size:1.35rem;font-weight:700;letter-spacing:-0.5px;color:var(--text);margin:0">
        Fechamento Semanal Comercial
      </h2>
      <p style="font-size:0.82rem;color:var(--text-muted);margin:2px 0 0 0">
        Relatorio semanal por empresa · piloto Flex Energy (kWh primario)
      </p>
    </div>
  </div>
  <div style="font-family:ui-monospace,monospace;font-size:0.7rem;color:var(--text-muted);text-align:right">
    v1.0 · Salesforce live<br>
    <span style="color:#EC8500;font-weight:700">Cache 5 min</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Controles · empresa + semana
# ============================================================

ctrl_cols = st.columns([2, 2, 1])
with ctrl_cols[0]:
    emp_options = ["Flex Energy"] + [e for e in EMPRESAS if e != "Flex Energy"]
    empresa = st.selectbox("Empresa", emp_options, index=0, key="fech_empresa",
                           format_func=lambda e: EMPRESA_LABELS.get(e, e))
with ctrl_cols[1]:
    hoje = date.today()
    semana_atual_seg, _ = _semana_de(hoje)
    semanas_opts = [(semana_atual_seg - timedelta(weeks=i)) for i in range(8)]
    def _fmt_sem(seg: date):
        dom = seg + timedelta(days=6)
        return f"Sem {seg.isocalendar().week:02d} · {seg.strftime('%d/%m')}–{dom.strftime('%d/%m')}"
    sem_sel = st.selectbox("Semana", semanas_opts, index=0, key="fech_semana", format_func=_fmt_sem)
with ctrl_cols[2]:
    st.write(""); st.write("")
    if st.button("🔄 Recarregar", use_container_width=True):
        st.cache_data.clear(); st.rerun()

sem_seg, sem_dom = _semana_de(sem_sel)
sem_seg_ant, sem_dom_ant = sem_seg - timedelta(days=7), sem_dom - timedelta(days=7)
mes_a, mes_m = sem_seg.year, sem_seg.month
du_h = dias_uteis_ate_hoje(mes_a, mes_m) if (mes_a, mes_m) == (hoje.year, hoje.month) else dias_uteis_no_mes(mes_a, mes_m)
du_t = dias_uteis_no_mes(mes_a, mes_m)
mtd_inicio = date(mes_a, mes_m, 1)
mtd_fim = sem_dom

# Identidade visual da empresa (cor accent)
cor_emp = CORES.get(empresa, {}).get("primaria", "#EC8500")
cor_emp_2 = CORES.get(empresa, {}).get("secundaria", "#F7C42D")
logo_b64 = get_logo_b64(empresa)

# Banner com empresa + semana + MTD
logo_html = (
    f'<img src="{logo_b64}" style="width:42px;height:42px;border-radius:10px;object-fit:cover" alt=""/>'
    if logo_b64 else
    f'<div style="width:42px;height:42px;border-radius:10px;background:{cor_emp};color:white;'
    f'display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem">{empresa[:1]}</div>'
)
st.markdown(f"""
<div class="hub-card" style="border-left:3px solid {cor_emp};display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:24px">
  <div style="display:flex;align-items:center;gap:14px">
    {logo_html}
    <div>
      <div style="font-size:0.65rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.1em">Empresa em foco</div>
      <div style="font-size:1.2rem;font-weight:700;letter-spacing:-0.3px;color:var(--text);line-height:1.15">
        {EMPRESA_LABELS.get(empresa, empresa)}
      </div>
    </div>
  </div>
  <div style="font-size:0.78rem;color:var(--text-secondary);text-align:right;font-feature-settings:'tnum'">
    <div><b>Semana:</b> {sem_seg.strftime('%d/%m/%Y')} → {sem_dom.strftime('%d/%m/%Y')}</div>
    <div style="margin-top:2px"><b>MTD:</b> {MESES_PT_FULL.get(mes_m,'')} {mes_a} · DU {du_h}/{du_t}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if empresa != "Flex Energy":
    st.info(
        f"O modelo foi desenhado a partir do template **Flex Energy** (kWh primario, "
        f"sub-segmentos Interno/Externo/Repres./Media Tensao). Para "
        f"**{EMPRESA_LABELS.get(empresa, empresa)}**, as queries estao ativas mas a "
        f"sub-segmentacao especifica sera mapeada no proximo ciclo."
    )


# ============================================================
# Carregar dados Salesforce
# ============================================================

with st.spinner("Carregando Salesforce..."):
    df_leads_sem = get_leads_periodo(empresa, sem_seg, sem_dom)
    df_leads_sem_ant = get_leads_periodo(empresa, sem_seg_ant, sem_dom_ant)
    df_leads_origem = get_leads_origem_periodo(empresa, sem_seg, sem_dom)
    df_leads_status = get_leads_status_periodo(empresa, sem_seg, sem_dom)
    df_leads_vend = _coalesce_vendedor(get_leads_vendedor_periodo(empresa, sem_seg, sem_dom))

    contas_sem = get_accounts_criadas_periodo(empresa, sem_seg, sem_dom)
    contas_sem_ant = get_accounts_criadas_periodo(empresa, sem_seg_ant, sem_dom_ant)

    df_opps_sem = _coalesce_vendedor(get_opps_criadas_periodo(empresa, sem_seg, sem_dom))
    df_opps_sem_ant = _coalesce_vendedor(get_opps_criadas_periodo(empresa, sem_seg_ant, sem_dom_ant))
    df_opps_mtd = _coalesce_vendedor(get_opps_criadas_periodo(empresa, mtd_inicio, mtd_fim))

    df_vendas_sem = get_opps_ganhas_periodo(empresa, sem_seg, sem_dom)
    df_vendas_sem_ant = get_opps_ganhas_periodo(empresa, sem_seg_ant, sem_dom_ant)
    df_vendas_mtd = get_opps_ganhas_periodo(empresa, mtd_inicio, mtd_fim)

    df_pipeline = get_pipeline_termometro(empresa)

    if empresa == "Flex Energy":
        kwh_orcado_sem = get_energy_kwh_periodo(sem_seg, sem_dom, ganhas=False)
        kwh_orcado_sem_ant = get_energy_kwh_periodo(sem_seg_ant, sem_dom_ant, ganhas=False)
        kwh_orcado_mtd = get_energy_kwh_periodo(mtd_inicio, mtd_fim, ganhas=False)
        kwh_vendido_sem = get_energy_kwh_periodo(sem_seg, sem_dom, ganhas=True)
        kwh_vendido_sem_ant = get_energy_kwh_periodo(sem_seg_ant, sem_dom_ant, ganhas=True)
        kwh_vendido_mtd = get_energy_kwh_periodo(mtd_inicio, mtd_fim, ganhas=True)
        df_consumo_decl = _coalesce_vendedor(get_energy_consumo_declarado_periodo(sem_seg, sem_dom))
    else:
        kwh_orcado_sem = kwh_orcado_sem_ant = kwh_orcado_mtd = {"kwh": 0, "opps": 0}
        kwh_vendido_sem = kwh_vendido_sem_ant = kwh_vendido_mtd = {"kwh": 0, "opps": 0}
        df_consumo_decl = pd.DataFrame()


# Totais
leads_total_sem = int(df_leads_sem["total"].sum()) if not df_leads_sem.empty else 0
leads_total_ant = int(df_leads_sem_ant["total"].sum()) if not df_leads_sem_ant.empty else 0
leads_convertidos_sem = (
    int(df_leads_sem[df_leads_sem["IsConverted"] == True]["total"].sum())
    if not df_leads_sem.empty and "IsConverted" in df_leads_sem.columns else 0
)

opps_total_sem = int(df_opps_sem["total"].sum()) if not df_opps_sem.empty else 0
opps_total_ant = int(df_opps_sem_ant["total"].sum()) if not df_opps_sem_ant.empty else 0
opps_valor_sem = float(df_opps_sem["valor"].sum()) if not df_opps_sem.empty and "valor" in df_opps_sem.columns else 0.0

vendas_total_sem = len(df_vendas_sem) if not df_vendas_sem.empty else 0
vendas_total_ant = len(df_vendas_sem_ant) if not df_vendas_sem_ant.empty else 0
vendas_valor_sem = float(df_vendas_sem["Amount"].sum()) if not df_vendas_sem.empty and "Amount" in df_vendas_sem.columns else 0.0
vendas_valor_mtd = float(df_vendas_mtd["Amount"].sum()) if not df_vendas_mtd.empty and "Amount" in df_vendas_mtd.columns else 0.0

PKEY = _persist_key(empresa, sem_seg)


# ============================================================
# Section header helper
# ============================================================

def section_head(num, titulo, sub, icon_name, color):
    st.markdown(f"""
    <div class="hub-section">
      <div class="hub-section-icon" style="background:{color}1a;color:{color}">
        {icon(icon_name, 20, color)}
      </div>
      <div>
        <h3 class="hub-section-title">{titulo}</h3>
        <p class="hub-section-sub">{sub}</p>
      </div>
      <span class="hub-section-tag">§ {num}</span>
    </div>
    """, unsafe_allow_html=True)


def kpi_hub_card(label, value, delta_pct=None, caption_extra=""):
    delta_html = _delta_pill(delta_pct)
    extra_html = (
        f'<span style="color:var(--text-muted);font-size:0.7rem">{caption_extra}</span>'
        if caption_extra else ""
    )
    return f"""
    <div class="kpi-hub">
      <div>
        <div class="kpi-hub-label">{label}</div>
        <div class="kpi-hub-value" style="color:{cor_emp}">{value}</div>
      </div>
      <div class="kpi-hub-foot">{delta_html}{extra_html}</div>
    </div>
    """


def kpi_hub_volume(label, value, secondary_label, secondary_value):
    return f"""
    <div class="kpi-hub">
      <div>
        <div class="kpi-hub-label">{label}</div>
        <div class="kpi-hub-value" style="color:{cor_emp}">{value}</div>
      </div>
      <div class="kpi-hub-foot">
        <span style="font-size:0.66rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted)">{secondary_label}</span>
        <span style="font-weight:600;color:var(--text-secondary);font-feature-settings:'tnum'">{secondary_value}</span>
      </div>
    </div>
    """


# ============================================================
# KPI HERO · LINHA 1 (semana vs semana anterior)
# ============================================================

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;
            font-size:0.66rem;text-transform:uppercase;letter-spacing:0.06em;
            color:var(--text);font-weight:600;margin:24px 0 10px 0;padding-bottom:6px;
            border-bottom:1px solid rgba(228,228,231,0.6)">
  <span>Indicadores da semana</span>
  <span style="color:{cor_emp};font-weight:500;text-transform:none;letter-spacing:0;font-style:italic">
    comparativo vs semana anterior · {sem_seg_ant.strftime('%d/%m')} → {sem_dom_ant.strftime('%d/%m')}
  </span>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1: st.markdown(kpi_hub_card("Leads gerados", _fmt(leads_total_sem), _delta_pct(leads_total_sem, leads_total_ant)), unsafe_allow_html=True)
with c2: st.markdown(kpi_hub_card("Contas criadas", _fmt(contas_sem), _delta_pct(contas_sem, contas_sem_ant)), unsafe_allow_html=True)
with c3: st.markdown(kpi_hub_card("Orçamentos gerados", _fmt(opps_total_sem), _delta_pct(opps_total_sem, opps_total_ant), caption_extra=_fv(opps_valor_sem)), unsafe_allow_html=True)
with c4: st.markdown(kpi_hub_card("Vendas fechadas", _fmt(vendas_total_sem), _delta_pct(vendas_total_sem, vendas_total_ant), caption_extra=_fv(vendas_valor_sem)), unsafe_allow_html=True)


# ============================================================
# KPI HERO · LINHA 2 (Volume & Ticket MTD)
# ============================================================

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;
            font-size:0.66rem;text-transform:uppercase;letter-spacing:0.06em;
            color:var(--text);font-weight:600;margin:22px 0 10px 0;padding-bottom:6px;
            border-bottom:1px solid rgba(228,228,231,0.6)">
  <span>Volume &amp; ticket médio · {'kWh primário · Flex Energy' if empresa == 'Flex Energy' else 'R$'}</span>
  <span style="color:{cor_emp};font-weight:500;text-transform:none;letter-spacing:0;font-style:italic">
    ticket médio sempre acumulado no mês (MTD)
  </span>
</div>
""", unsafe_allow_html=True)

if empresa == "Flex Energy":
    vol_orc_sem = kwh_orcado_sem["kwh"]; vol_orc_mtd = kwh_orcado_mtd["kwh"]
    ticket_orc_mtd = (vol_orc_mtd / kwh_orcado_mtd["opps"]) if kwh_orcado_mtd["opps"] > 0 else 0
    vol_ven_sem = kwh_vendido_sem["kwh"]; vol_ven_mtd = kwh_vendido_mtd["kwh"]
    ticket_ven_mtd = (vol_ven_mtd / kwh_vendido_mtd["opps"]) if kwh_vendido_mtd["opps"] > 0 else 0
    fmt_loc = _fk
else:
    vol_orc_sem = opps_valor_sem
    opps_mtd_qtd = int(df_opps_mtd["total"].sum()) if not df_opps_mtd.empty else 0
    vol_orc_mtd = float(df_opps_mtd["valor"].sum()) if not df_opps_mtd.empty and "valor" in df_opps_mtd.columns else 0.0
    ticket_orc_mtd = (vol_orc_mtd / opps_mtd_qtd) if opps_mtd_qtd > 0 else 0
    vol_ven_sem = vendas_valor_sem; vol_ven_mtd = vendas_valor_mtd
    ticket_ven_mtd = (vol_ven_mtd / len(df_vendas_mtd)) if not df_vendas_mtd.empty else 0
    fmt_loc = _fv

c1, c2, c3, c4 = st.columns(4, gap="small")
with c1: st.markdown(kpi_hub_volume("Orçamentos · Volume semana", fmt_loc(vol_orc_sem), "Acumulado mês", fmt_loc(vol_orc_mtd)), unsafe_allow_html=True)
with c2: st.markdown(kpi_hub_volume("Orçamentos · Ticket médio MTD", fmt_loc(ticket_orc_mtd), "Volume MTD", fmt_loc(vol_orc_mtd)), unsafe_allow_html=True)
with c3: st.markdown(kpi_hub_volume("Vendas · Volume semana", fmt_loc(vol_ven_sem), "Acumulado mês", fmt_loc(vol_ven_mtd)), unsafe_allow_html=True)
with c4: st.markdown(kpi_hub_volume("Vendas · Ticket médio MTD", fmt_loc(ticket_ven_mtd), "Volume MTD", fmt_loc(vol_ven_mtd)), unsafe_allow_html=True)


# ============================================================
# § 01 LEADS
# ============================================================

section_head("01", "Leads", "Origem, distribuição entre vendedores e status atual", "users", "#8b5cf6")

# A · Origem
def _origem_bucket(src):
    if not src: return "Outro"
    s = str(src).lower()
    if "exact" in s: return "Exact Sales · Pré-Vendas"
    if "meta" in s or "google" in s: return "Tráfego Pago · SDR2"
    if "indica" in s: return "Indicação / Carteira"
    if "prospec" in s: return "Prospecção Ativa"
    return "Outro"

st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:0 0 10px 0">A · Origem dos leads na semana</p>', unsafe_allow_html=True)
if not df_leads_origem.empty:
    df_o = df_leads_origem.copy()
    df_o["LeadSource"] = df_o["LeadSource"].fillna("Outro")
    df_o["bucket"] = df_o["LeadSource"].apply(_origem_bucket)
    df_b = df_o.groupby("bucket", as_index=False)["total"].sum()
    total_origem = int(df_b["total"].sum())
    ordem = ["Exact Sales · Pré-Vendas", "Tráfego Pago · SDR2", "Indicação / Carteira", "Prospecção Ativa", "Outro"]
    df_b["ord"] = df_b["bucket"].apply(lambda b: ordem.index(b) if b in ordem else 99)
    df_b = df_b.sort_values("ord").drop(columns=["ord"])
    rows_html = ""
    for _, r in df_b.iterrows():
        pct = (r["total"] / total_origem * 100) if total_origem > 0 else 0
        rows_html += f'<tr><td><b>{r["bucket"]}</b></td><td class="num">{int(r["total"])}</td><td class="num">{pct:.0f}%</td></tr>'
    st.markdown(f"""
    <table class="hub-table">
      <thead><tr><th>Origem</th><th class="num">Quantidade</th><th class="num">% do total</th></tr></thead>
      <tbody>{rows_html}</tbody>
      <tfoot><tr><td>Total da semana</td><td class="num">{total_origem}</td><td class="num">100%</td></tr></tfoot>
    </table>
    """, unsafe_allow_html=True)
else:
    st.info("Sem leads no período.")

# B · Distribuição entre vendedores
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 10px 0">B · Distribuição entre vendedores</p>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<p style="font-size:0.7rem;color:{cor_emp};margin:0 0 10px 0;font-weight:500">↳ Flex Energy: sub-segmento Interno / Externo / Representantes / Média Tensão (mapa Owner→segmento — TODO)</p>', unsafe_allow_html=True)

if not df_leads_vend.empty:
    df_v = df_leads_vend.copy()
    df_v["recebidos"] = df_v["total"]
    df_v["tratados"] = df_v.apply(lambda r: r["total"] if r.get("Status") and r.get("Status") != "Aberto" else 0, axis=1)
    df_v["convertidos"] = df_v.apply(lambda r: r["total"] if r.get("IsConverted") else 0, axis=1)
    agg = df_v.groupby("vendedor", as_index=False).agg({"recebidos": "sum", "tratados": "sum", "convertidos": "sum"})
    agg = agg.sort_values("recebidos", ascending=False).head(15)
    rows_html = ""
    for _, r in agg.iterrows():
        pct_t = (r["tratados"]/r["recebidos"]*100) if r["recebidos"] > 0 else 0
        pct_c = (r["convertidos"]/r["recebidos"]*100) if r["recebidos"] > 0 else 0
        pill_c = (
            f'<span class="pill pill-good">{pct_c:.0f}%</span>' if pct_c >= 10 else
            f'<span class="pill pill-warn">{pct_c:.0f}%</span>' if pct_c >= 3 else
            f'<span class="pill pill-flat">{pct_c:.0f}%</span>'
        )
        rows_html += f'<tr><td>{r["vendedor"]}</td><td class="num">{int(r["recebidos"])}</td><td class="num">{int(r["tratados"])}</td><td class="num">{pct_t:.0f}%</td><td class="num">{int(r["convertidos"])}</td><td class="num">{pill_c}</td></tr>'
    st.markdown(f"""
    <table class="hub-table">
      <thead><tr>
        <th>Vendedor</th><th class="num">Recebidos</th><th class="num">Tratados</th>
        <th class="num">% Trat.</th><th class="num">Convertidos</th><th class="num">% Conv.</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)
else:
    st.info("Sem distribuição por vendedor no período.")

# B.1 · Consumo declarado kWh (Flex Energy)
if empresa == "Flex Energy":
    st.markdown(f'<p style="font-size:0.72rem;color:{cor_emp};text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 6px 0">B.1 · Consumo declarado · kWh · exclusivo Flex Energy</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);font-style:italic;margin-bottom:10px">Volume em kWh é a medida primária. Ticket médio considerado como acumulado mensal (MTD).</p>', unsafe_allow_html=True)
    if not df_consumo_decl.empty:
        df_kc = df_consumo_decl.copy()
        df_kc["consumo_medio"] = df_kc.apply(lambda r: r["total_kwh"] / r["total_leads"] if r["total_leads"] > 0 else 0, axis=1)
        df_kc = df_kc.sort_values("total_kwh", ascending=False).head(15)
        rows_html = ""
        for _, r in df_kc.iterrows():
            rows_html += f'<tr><td>{r["vendedor"]}</td><td class="num">{int(r["total_leads"])}</td><td class="num">{int(r["total_kwh"]):,}</td><td class="num">{int(r["consumo_medio"]):,}</td></tr>'.replace(",", ".")
        st.markdown(f"""
        <table class="hub-table">
          <thead><tr><th>Vendedor</th><th class="num">Leads na semana</th><th class="num">Consumo total (kWh)</th><th class="num">Consumo médio/lead (kWh)</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        <p style="font-size:0.78rem;color:var(--text-muted);margin-top:8px"><b>Ticket médio kWh MTD</b> (base Opps criadas): <b style="color:var(--text)">{_fk(ticket_orc_mtd)}</b></p>
        """, unsafe_allow_html=True)
    else:
        st.info("Sem leads com consumo declarado na semana.")

# C · Status dos leads
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 10px 0">C · Status dos leads ao fim da semana</p>', unsafe_allow_html=True)
if not df_leads_status.empty:
    status_map = {}
    for _, r in df_leads_status.iterrows():
        status_map[r.get("Status") or "—"] = int(r["total"])
    em_tratativa = sum(status_map.get(s, 0) for s in ["Em Contato", "Em Interacao", "Aceite", "Recuperacao"])
    convertidos = leads_convertidos_sem
    aguard = status_map.get("Stand-by Retrabalho", 0)
    desqualif = status_map.get("Fechado Nao Convertido", 0)
    sem_acao = status_map.get("Aberto", 0)
    buckets = [
        ("Em tratativa", em_tratativa, "leads", "#3b82f6"),
        ("Convertidos em Conta", convertidos, "leads", "#10b981"),
        ("Aguardando retorno", aguard, "leads", "#f59e0b"),
        ("Desqualificados", desqualif, "leads", "#71717a"),
        ("Sem ação ⚠", sem_acao, "SLA em aberto", "#dc2626"),
    ]
    cols = st.columns(5, gap="small")
    for col, (label, qtd, sub, c) in zip(cols, buckets):
        with col:
            st.markdown(f"""
            <div class="status-bucket">
              <div class="label">{label}</div>
              <div class="count" style="color:{c}">{qtd}</div>
              <div class="sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

with st.expander("📝 Observações · Leads"):
    k_obs_l = f"{PKEY}__obs_leads"
    st.session_state[k_obs_l] = st.text_area("Análise da semana", value=st.session_state.get(k_obs_l, ""),
        placeholder="Qualidade dos leads, gargalos na tratativa, padrões na origem, comportamento Pré-Vendas/SDR2…",
        height=80, key=f"ta_{k_obs_l}", label_visibility="collapsed")


# ============================================================
# § 02 CONTAS
# ============================================================

section_head("02", "Contas", "Criação, equiparação com leads convertidos e qualidade do cadastro", "users", "#10b981")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:0 0 10px 0">A · Volume vs Leads</p>', unsafe_allow_html=True)
    diff = contas_sem - leads_convertidos_sem
    diff_pill = "pill-good" if abs(diff) <= 1 else ("pill-warn" if abs(diff) <= 5 else "pill-bad")
    st.markdown(f"""
    <table class="hub-table">
      <thead><tr><th>Indicador</th><th class="num">Valor</th></tr></thead>
      <tbody>
        <tr><td>Leads convertidos p/ Conta</td><td class="num">{leads_convertidos_sem}</td></tr>
        <tr><td>Contas criadas no Salesforce</td><td class="num">{contas_sem}</td></tr>
        <tr><td><b>Diferença</b></td><td class="num"><span class="pill {diff_pill}">{diff:+d}</span></td></tr>
      </tbody>
    </table>
    """, unsafe_allow_html=True)
    if abs(diff) > 1:
        st.caption(f"⚠ Diferença de {diff:+d} entre leads convertidos e contas criadas - verificar conversão manual ou contas sem origem em lead.")

with col_b:
    st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:0 0 10px 0">B · Qualidade do cadastro</p>', unsafe_allow_html=True)
    qual = get_qualidade_contas_energy(sem_seg, sem_dom) if empresa == "Flex Energy" else None
    if qual and qual["total"] > 0:
        total_q = qual["total"]
        crit = [
            ("Razão social preenchida", qual["razao_social_ok"]),
            ("Setor / Classificação", qual["setor_ok"]),
            ("Endereço completo", qual["endereco_ok"]),
        ]
        rows_html = ""
        for nome, ok in crit:
            if ok is None:
                rows_html += f'<tr><td>{nome}</td><td class="num"><span class="pill pill-flat">n/d</span></td><td class="num"><span class="pill pill-flat">campo não mapeado</span></td></tr>'
                continue
            falta = total_q - ok
            pill = "pill-good" if falta == 0 else ("pill-warn" if falta/total_q < 0.3 else "pill-bad")
            rows_html += f'<tr><td>{nome}</td><td class="num">{ok}</td><td class="num"><span class="pill {pill}">{falta}</span></td></tr>'
        st.markdown(f"""
        <table class="hub-table">
          <thead><tr><th>Critério</th><th class="num">Conformes</th><th class="num">Inconformes</th></tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        <p style="font-size:0.7rem;color:var(--text-muted);margin-top:6px">Base: {total_q} contas {empresa} criadas no período</p>
        """, unsafe_allow_html=True)
    else:
        st.info("Sem contas no período ou critérios indisponíveis.")

with st.expander("📝 Observações · Contas"):
    k_obs_c = f"{PKEY}__obs_contas"
    st.session_state[k_obs_c] = st.text_area("Análise", value=st.session_state.get(k_obs_c, ""),
        placeholder="Aderência leads x contas, padrões de erro no cadastro, reforço de processo…",
        height=70, key=f"ta_{k_obs_c}", label_visibility="collapsed")


# ============================================================
# § 03 OPORTUNIDADES
# ============================================================

section_head("03", "Oportunidades", "Produção semanal + pipeline em aberto · termômetro de negociação", "flame", "#f97316")

# A · Produção
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:0 0 10px 0">A · Produção da semana por vendedor</p>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<p style="font-size:0.7rem;color:{cor_emp};margin:0 0 10px 0;font-weight:500">↳ Flex Energy: discriminar por Interno / Externo / Representantes / Média Tensão · medida primária em kWh</p>', unsafe_allow_html=True)

if not df_opps_sem.empty:
    df_p = df_opps_sem.copy()
    agg_p = df_p.groupby("vendedor", as_index=False).agg({"total": "sum", "valor": "sum"})
    fase_pred = df_p.sort_values("total", ascending=False).groupby("vendedor")["StageName"].first().to_dict()
    agg_p["fase_pred"] = agg_p["vendedor"].map(fase_pred)
    agg_p = agg_p.sort_values("total", ascending=False).head(15)
    rows_html = ""
    for _, r in agg_p.iterrows():
        ticket = (r["valor"] / r["total"]) if r["total"] > 0 and r["valor"] else 0
        rows_html += (
            f'<tr><td>{r["vendedor"]}</td><td class="num">{int(r["total"])}</td>'
            f'<td class="num">{_fv(r["valor"])}</td><td class="num">{_fv(ticket)}</td>'
            f'<td><span class="pill pill-flat">{r["fase_pred"] or "—"}</span></td></tr>'
        )
    st.markdown(f"""
    <table class="hub-table">
      <thead><tr><th>Vendedor</th><th class="num">Orçamentos</th><th class="num">Volume R$</th><th class="num">Ticket médio</th><th>Fase predominante</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

    total_sem_orc = int(df_p["total"].sum())
    total_sem_val = float(df_p["valor"].sum())
    mtd_orc_qtd = int(df_opps_mtd["total"].sum()) if not df_opps_mtd.empty else 0
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
      <div class="hub-card hub-card-tight">
        <div style="font-size:0.66rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600">Total semanal</div>
        <div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-top:4px">{total_sem_orc} orçamentos · {_fv(total_sem_val)}</div>
      </div>
      <div class="hub-card hub-card-tight" style="border-left:3px solid {cor_emp}">
        <div style="font-size:0.66rem;color:{cor_emp};text-transform:uppercase;letter-spacing:0.08em;font-weight:700">Acumulado MTD</div>
        <div style="font-size:1.05rem;font-weight:700;color:{cor_emp};margin-top:4px">
          {mtd_orc_qtd} opps · {_fk(kwh_orcado_mtd["kwh"]) if empresa == "Flex Energy" else _fv(vol_orc_mtd)} · ticket {fmt_loc(ticket_orc_mtd)}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("Sem oportunidades criadas no período.")

# B · Pipeline · termômetro
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 10px 0">B · Pipeline em aberto · termômetro de negociação</p>', unsafe_allow_html=True)
buckets_pipe = {
    "Indo para contrato": {"qtd": 0, "vol": 0.0, "dot": "#10b981"},
    "Quente · negociação": {"qtd": 0, "vol": 0.0, "dot": "#f97316"},
    "Morno · contato ativo": {"qtd": 0, "vol": 0.0, "dot": "#f59e0b"},
    "Frio · contato passivo (ODR)": {"qtd": 0, "vol": 0.0, "dot": "#6366f1"},
}
if not df_pipeline.empty:
    for _, r in df_pipeline.iterrows():
        fase = r.get("fase"); temp = r.get("temp") if "temp" in r.index else None
        qtd = int(r.get("total", 0))
        vol = float(r.get("volume_kwh", r.get("volume_rs", 0)) or 0)
        if fase == "Contrato":
            buckets_pipe["Indo para contrato"]["qtd"] += qtd
            buckets_pipe["Indo para contrato"]["vol"] += vol
        elif fase == "Negociacao" or temp == "Quente":
            buckets_pipe["Quente · negociação"]["qtd"] += qtd
            buckets_pipe["Quente · negociação"]["vol"] += vol
        elif fase == "Contato Ativo" or temp == "Morno":
            buckets_pipe["Morno · contato ativo"]["qtd"] += qtd
            buckets_pipe["Morno · contato ativo"]["vol"] += vol
        elif fase == "Contato Passivo" or temp == "Frio":
            buckets_pipe["Frio · contato passivo (ODR)"]["qtd"] += qtd
            buckets_pipe["Frio · contato passivo (ODR)"]["vol"] += vol

cols_t = st.columns(4, gap="small")
for col, (label, b) in zip(cols_t, buckets_pipe.items()):
    vol_fmt = _fk(b["vol"]) if empresa == "Flex Energy" else _fv(b["vol"])
    with col:
        st.markdown(f"""
        <div class="temp-card">
          <div class="label"><span class="dot" style="background:{b["dot"]}"></span>{label}</div>
          <div class="count">{b["qtd"]}</div>
          <div class="vol">Volume: <b style="color:var(--text-secondary)">{vol_fmt}</b></div>
        </div>
        """, unsafe_allow_html=True)

# C · ODR (manual)
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 10px 0">C · Atuação do ODR · resgate de oportunidades frias</p>', unsafe_allow_html=True)
with st.expander("Preencher / editar dados do ODR"):
    odr_cols = st.columns(2)
    with odr_cols[0]:
        for nome, sufx in [("Trabalhadas pelo ODR · semana", "trab_sem"), ("Reativadas · semana", "reat_sem"),
                            ("Convertidas em venda · semana", "conv_sem"), ("Descartadas · semana", "desc_sem")]:
            k = f"{PKEY}__odr_{sufx}"
            st.session_state[k] = st.number_input(nome, value=float(st.session_state.get(k, 0.0)), step=1.0, key=f"ni_{k}")
    with odr_cols[1]:
        for nome, sufx in [("Trabalhadas pelo ODR · MTD", "trab_mtd"), ("Reativadas · MTD", "reat_mtd"),
                            ("Convertidas em venda · MTD", "conv_mtd"), ("Descartadas · MTD", "desc_mtd")]:
            k = f"{PKEY}__odr_{sufx}"
            st.session_state[k] = st.number_input(nome, value=float(st.session_state.get(k, 0.0)), step=1.0, key=f"ni_{k}")

odr_rows = ""
for nome, sufx_s, sufx_m in [
    ("Trabalhadas pelo ODR", "trab_sem", "trab_mtd"),
    ("Reativadas (esquentaram)", "reat_sem", "reat_mtd"),
    ("Convertidas em venda", "conv_sem", "conv_mtd"),
    ("Descartadas definitivamente", "desc_sem", "desc_mtd"),
]:
    s = int(st.session_state.get(f"{PKEY}__odr_{sufx_s}", 0))
    m = int(st.session_state.get(f"{PKEY}__odr_{sufx_m}", 0))
    odr_rows += f'<tr><td>{nome}</td><td class="num">{s}</td><td class="num">{m}</td></tr>'
st.markdown(f"""
<table class="hub-table">
  <thead><tr><th>Indicador</th><th class="num">Semana</th><th class="num">Acumulado mês</th></tr></thead>
  <tbody>{odr_rows}</tbody>
</table>
""", unsafe_allow_html=True)

with st.expander("📝 Observações · Oportunidades & Pipeline"):
    k_obs_o = f"{PKEY}__obs_opps"
    st.session_state[k_obs_o] = st.text_area("Análise", value=st.session_state.get(k_obs_o, ""),
        placeholder="Movimentação do pipeline, opps de destaque, gargalos por fase, performance ODR, alertas de esfriamento…",
        height=80, key=f"ta_{k_obs_o}", label_visibility="collapsed")


# ============================================================
# § 04 VENDAS · META
# ============================================================

section_head("04", "Vendas · Ritmo de Meta", "O que entrou na semana e o pace acumulado contra a meta", "target", "#3b82f6")

# Meta input
k_meta = f"{PKEY}__meta_mensal"
st.session_state[k_meta] = st.number_input(
    f"Meta mensal · {'kWh' if empresa == 'Flex Energy' else 'R$'} (deixe 0 se não houver meta)",
    value=float(st.session_state.get(k_meta, 0.0)), step=10000.0, key=f"ni_{k_meta}",
)
meta_mtd = st.session_state[k_meta]
realizado_mtd = vol_ven_mtd
pct_meta = (realizado_mtd / meta_mtd * 100) if meta_mtd > 0 else 0
ritmo = (realizado_mtd / du_h) * du_t if du_h > 0 else 0
pct_ritmo = (ritmo / meta_mtd * 100) if meta_mtd > 0 else 0

st.markdown(f"""
<div class="hub-meta">
  <div>
    <div class="kicker">Atingimento da meta · {MESES_PT_FULL.get(mes_m, '')} {mes_a}</div>
    <div style="display:flex;gap:24px;align-items:baseline">
      <div class="main">{pct_meta:.0f}%</div>
      <div style="font-size:0.78rem;opacity:0.85;font-feature-settings:'tnum'">
        Realizado / Meta<br>
        <b style="color:{cor_emp};font-size:1.05rem;display:block;margin-top:2px">{fmt_loc(realizado_mtd)} / {fmt_loc(meta_mtd)}</b>
      </div>
    </div>
    <div class="sub">Ritmo previsto p/ fim do mês: <b>{pct_ritmo:.0f}%</b> ({fmt_loc(ritmo)})</div>
  </div>
  <div>
    <div class="bar">
      <div class="fill" style="background:{cor_emp};width:{min(pct_meta, 100):.0f}%">{pct_meta:.0f}%</div>
    </div>
    <div style="text-align:center;margin-top:8px;font-size:0.72rem;opacity:0.85">
      Dia útil <b>{du_h}</b> de <b>{du_t}</b>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# A · Vendas da semana
st.markdown('<p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600;margin:22px 0 10px 0">A · Vendas da semana (Fechado Ganho)</p>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<p style="font-size:0.7rem;color:{cor_emp};margin:0 0 10px 0;font-weight:500">↳ Flex Energy: medida primária em kWh · sub-segmentação Tipo_de_Conta_ENERGY__c (Baixa Tensão / Média Tensão)</p>', unsafe_allow_html=True)

if not df_vendas_sem.empty:
    df_vs = df_vendas_sem.copy()
    rows_html = ""
    for _, r in df_vs.iterrows():
        vendedor = r.get("Owner.Name", "—")
        cliente = r.get("Account.Name", "—")
        amount = r.get("Amount") or 0
        cd = r.get("CloseDate", "")
        try:
            cd_fmt = pd.to_datetime(cd).strftime("%d/%m/%Y")
        except Exception:
            cd_fmt = str(cd) or "—"
        seg = r.get("Tipo_de_Conta_ENERGY__c", None)
        seg_html = f'<span class="pill pill-flat">{seg}</span>' if seg else "—"
        if empresa == "Flex Energy":
            rows_html += f'<tr><td>{vendedor}</td><td>{seg_html}</td><td>{cliente}</td><td class="num">{_fv(amount)}</td><td class="num">{cd_fmt}</td></tr>'
        else:
            rows_html += f'<tr><td>{vendedor}</td><td>{cliente}</td><td class="num">{_fv(amount)}</td><td class="num">{cd_fmt}</td></tr>'
    if empresa == "Flex Energy":
        thead = '<tr><th>Vendedor</th><th>Segmento</th><th>Cliente</th><th class="num">Ticket R$</th><th class="num">Data fechamento</th></tr>'
    else:
        thead = '<tr><th>Vendedor</th><th>Cliente</th><th class="num">Ticket R$</th><th class="num">Data fechamento</th></tr>'
    st.markdown(f'<table class="hub-table"><thead>{thead}</thead><tbody>{rows_html}</tbody></table>', unsafe_allow_html=True)

    extra_vol_sem = f' · {_fk(kwh_vendido_sem["kwh"])}' if empresa == "Flex Energy" else ''
    extra_vol_mtd = f' · {_fk(kwh_vendido_mtd["kwh"])}' if empresa == "Flex Energy" else ''
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
      <div class="hub-card hub-card-tight">
        <div style="font-size:0.66rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;font-weight:600">Total semanal</div>
        <div style="font-size:1.05rem;font-weight:700;color:var(--text);margin-top:4px">{vendas_total_sem} vendas · {_fv(vendas_valor_sem)}{extra_vol_sem}</div>
      </div>
      <div class="hub-card hub-card-tight" style="border-left:3px solid {cor_emp}">
        <div style="font-size:0.66rem;color:{cor_emp};text-transform:uppercase;letter-spacing:0.08em;font-weight:700">Acumulado MTD</div>
        <div style="font-size:1.05rem;font-weight:700;color:{cor_emp};margin-top:4px">
          {len(df_vendas_mtd)} vendas · {_fv(vendas_valor_mtd)}{extra_vol_mtd} · ticket {fmt_loc(ticket_ven_mtd)}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("Sem vendas (Fechado Ganho) no período selecionado.")

with st.expander("📝 Observações · Vendas"):
    k_obs_v = f"{PKEY}__obs_vendas"
    st.session_state[k_obs_v] = st.text_area("Análise", value=st.session_state.get(k_obs_v, ""),
        placeholder="Destaques, vendas atípicas, mix de produtos/segmentos, riscos para meta…",
        height=80, key=f"ta_{k_obs_v}", label_visibility="collapsed")


# ============================================================
# § 05 FUNIL
# ============================================================

section_head("05", "Funil de Conversão", "Lead → Conta → Oportunidade → Em negociação → Venda", "trending-up", "#8b5cf6")

leads_q = leads_total_sem
contas_q = contas_sem
opps_q = opps_total_sem
neg_q = int(df_opps_sem[df_opps_sem["StageName"].isin(["Negociacao", "Contrato"])]["total"].sum()) if not df_opps_sem.empty else 0
vendas_q = vendas_total_sem

base = max(leads_q, 1)
funnel_data = [
    ("Leads", leads_q, 100.0, None, cor_emp),
    ("Contas", contas_q, (contas_q/base*100) if leads_q else 0, (contas_q/leads_q*100) if leads_q > 0 else 0, "#9a3412"),
    ("Oportunidades", opps_q, (opps_q/base*100) if leads_q else 0, (opps_q/contas_q*100) if contas_q > 0 else 0, "#c2410c"),
    ("Em negociação", neg_q, (neg_q/base*100) if leads_q else 0, (neg_q/opps_q*100) if opps_q > 0 else 0, "#ea580c"),
    ("Vendas", vendas_q, (vendas_q/base*100) if leads_q else 0, (vendas_q/neg_q*100) if neg_q > 0 else 0, "#f97316"),
]
funnel_html = '<div class="hub-card" style="padding:18px">'
for label, qtd, pct, conv, color in funnel_data:
    conv_str = "base" if conv is None else f"↳ {conv:.0f}%"
    bar_w = max(min(pct, 100), 4)
    funnel_html += f"""
    <div class="funnel-row">
      <div class="funnel-label">{label}</div>
      <div class="funnel-bar"><div class="fill" style="background:{color};width:{bar_w}%">{qtd}</div></div>
      <div class="funnel-pct">{pct:.0f}%</div>
      <div class="funnel-conv">{conv_str}</div>
    </div>
    """
funnel_html += "</div>"
st.markdown(funnel_html, unsafe_allow_html=True)

with st.expander("📝 Observações · Funil"):
    k_obs_f = f"{PKEY}__obs_funil"
    st.session_state[k_obs_f] = st.text_area("Análise", value=st.session_state.get(k_obs_f, ""),
        placeholder="Onde está o maior afunilamento? Lead → Conta (cadastro) ou Opp → Venda (proposta/preço)?",
        height=70, key=f"ta_{k_obs_f}", label_visibility="collapsed")


# ============================================================
# § 06 COMPARATIVO 4 SEMANAS
# ============================================================

section_head("06", "Comparativo · Últimas 4 Semanas", "Tendência mensal · evolução das principais métricas", "calendar", "#0ea5e9")

@st.cache_data(ttl=300)
def _build_compare(empresa: str, ate_dom: date, semanas: int = 4):
    out = []
    for i in range(semanas - 1, -1, -1):
        seg = ate_dom - timedelta(days=ate_dom.weekday() + 7 * i)
        dom = seg + timedelta(days=6)
        df_l = get_leads_periodo(empresa, seg, dom)
        df_o = get_opps_criadas_periodo(empresa, seg, dom)
        df_v = get_opps_ganhas_periodo(empresa, seg, dom)
        leads = int(df_l["total"].sum()) if not df_l.empty else 0
        orc = int(df_o["total"].sum()) if not df_o.empty else 0
        vol_orc_v = float(df_o["valor"].sum()) if not df_o.empty and "valor" in df_o.columns else 0
        vendas = len(df_v) if not df_v.empty else 0
        vol_v = float(df_v["Amount"].sum()) if not df_v.empty and "Amount" in df_v.columns else 0
        if empresa == "Flex Energy":
            kwh_o = get_energy_kwh_periodo(seg, dom, ganhas=False)["kwh"]
            kwh_v = get_energy_kwh_periodo(seg, dom, ganhas=True)["kwh"]
            vol_orc_v = kwh_o; vol_v = kwh_v
        out.append({"seg": seg, "leads": leads, "orc": orc, "vol_orc": vol_orc_v,
                    "vendas": vendas, "vol_vendas": vol_v,
                    "conv": (vendas / leads * 100) if leads > 0 else 0})
    return out

compare = _build_compare(empresa, sem_dom)
labels = [f"Sem {c['seg'].isocalendar().week:02d}" for c in compare]
labels[-1] = labels[-1] + " · atual"

def _trend(vals):
    if len(vals) < 2: return ('<span style="color:var(--text-muted)">—</span>', "flat")
    d = vals[-1] - vals[0]
    if d > 0: return ('<span style="color:#10b981;font-weight:700">↑</span>', "up")
    if d < 0: return ('<span style="color:#ef4444;font-weight:700">↓</span>', "down")
    return ('<span style="color:var(--text-muted)">→</span>', "flat")

linhas = [
    ("Leads", [c["leads"] for c in compare], _fmt),
    ("Orçamentos", [c["orc"] for c in compare], _fmt),
    (f"Volume orçado ({'kWh' if empresa == 'Flex Energy' else 'R$'})", [c["vol_orc"] for c in compare], (_fk if empresa == "Flex Energy" else _fv)),
    ("Vendas (qtd)", [c["vendas"] for c in compare], _fmt),
    (f"Volume vendido ({'kWh' if empresa == 'Flex Energy' else 'R$'})", [c["vol_vendas"] for c in compare], (_fk if empresa == "Flex Energy" else _fv)),
    ("Conv. Lead → Venda", [c["conv"] for c in compare], lambda v: f"{v:.1f}%"),
]
thead = '<tr><th>Indicador</th>' + "".join([f'<th class="num">{lb}</th>' for lb in labels]) + '<th class="num">Tend.</th></tr>'
rows = ""
for nome, vals, fmt_fn in linhas:
    cells = ""
    for idx, v in enumerate(vals):
        try: fmt_v = fmt_fn(v)
        except Exception: fmt_v = "—"
        atual = ' style="font-weight:700;color:var(--text);background:rgba(254,243,199,0.4)"' if idx == len(vals) - 1 else ""
        cells += f'<td class="num"{atual}>{fmt_v}</td>'
    trend_html, _ = _trend(vals)
    rows += f'<tr><td><b>{nome}</b></td>{cells}<td class="num">{trend_html}</td></tr>'
st.markdown(f'<table class="hub-table"><thead>{thead}</thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)


# ============================================================
# § 07 RETROSPECTIVA
# ============================================================

section_head("07", "Retrospectiva da Semana", "Preenchido antes da reunião de segunda · base para discussão", "list-checks", "#a855f7")

retro_items = [
    ("01", "Como a semana foi?", "Síntese geral em 2-3 frases: ritmo, clima, eventos relevantes…"),
    ("02", "O que funcionou bem?", "Boas práticas, vendedores em destaque, processos que fluíram…"),
    ("03", "O que não funcionou?", "Gargalos, falhas de processo, oportunidades perdidas, atritos…"),
    ("04", "Ações realizadas", "O que foi executado da semana anterior — vinculado às pendências."),
    ("05", "Ações pendentes", "O que ficou para trás — e por quê. Responsável e motivo."),
    ("06", "Ações para a semana atual", "Compromissos firmados na segunda."),
]
retro_cols = st.columns(2)
for i, (num, titulo, ph) in enumerate(retro_items):
    col = retro_cols[i % 2]
    with col:
        k_r = f"{PKEY}__retro_{num}"
        st.markdown(f"""
        <div class="retro-card" style="margin-bottom:10px">
          <div style="margin-bottom:10px">
            <span class="num" style="background:{cor_emp}1a;color:{cor_emp}">{num}</span>
            <b style="font-size:0.95rem;letter-spacing:-0.2px">{titulo}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.session_state[k_r] = st.text_area(titulo, value=st.session_state.get(k_r, ""),
            placeholder=ph, height=80, key=f"ta_{k_r}", label_visibility="collapsed")


# ============================================================
# § 08 NOTAS DA REUNIÃO
# ============================================================

section_head("08", "Notas da Reunião · Segunda-feira", "Preenchido durante o alinhamento com os gestores", "file-text", "#64748b")

nc = st.columns(2)
with nc[0]:
    k_dec = f"{PKEY}__notas_decisoes"
    st.markdown('<div class="hub-card hub-card-tight" style="margin-bottom:10px;border-left:3px solid #18181b"><b style="font-size:0.85rem">Decisões tomadas</b></div>', unsafe_allow_html=True)
    st.session_state[k_dec] = st.text_area("Decisões", value=st.session_state.get(k_dec, ""),
        placeholder="O que foi decidido — direção, ajustes de meta, mudanças de processo…",
        height=110, key=f"ta_{k_dec}", label_visibility="collapsed")
with nc[1]:
    k_fb = f"{PKEY}__notas_feedback"
    st.markdown('<div class="hub-card hub-card-tight" style="margin-bottom:10px;border-left:3px solid #18181b"><b style="font-size:0.85rem">Pontos de discussão & feedback dos gestores</b></div>', unsafe_allow_html=True)
    st.session_state[k_fb] = st.text_area("Feedback", value=st.session_state.get(k_fb, ""),
        placeholder="O que cada gestor levantou, divergências, sugestões, contexto adicional…",
        height=110, key=f"ta_{k_fb}", label_visibility="collapsed")


# ============================================================
# § 09 ALERTA
# ============================================================

section_head("09", "Alerta", "Algo crítico que precisa de atenção imediata", "flame", "#dc2626")

k_alerta = f"{PKEY}__alerta"
st.session_state[k_alerta] = st.text_area(
    "Destaque crítico da semana",
    value=st.session_state.get(k_alerta, ""),
    placeholder="SOMENTE para alertas que exigem ação imediata: risco de meta, cliente importante perdido, gargalo grave, escalonamento. Deixe em branco se nada se aplicar.",
    height=80, key=f"ta_{k_alerta}",
)
alerta_v = st.session_state[k_alerta]
if alerta_v.strip():
    st.markdown(f"""
    <div class="hub-alerta">
      <div class="icon">!</div>
      <div>
        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#b45309;font-weight:700;margin-bottom:6px">Destaque crítico da semana</div>
        <div style="font-size:0.95rem;line-height:1.5;color:#1a1a2e;font-weight:500">{alerta_v}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Footer
# ============================================================

st.markdown(f"""
<div style="margin-top:36px;padding-top:18px;border-top:1px solid rgba(228,228,231,0.6);
            display:flex;justify-content:space-between;align-items:center;gap:24px;font-size:0.7rem;color:var(--text-muted)">
  <div>GFlex Empresas · Fechamento Semanal Comercial · v1.0 · design Hub-like<br>
       Modelo Flex Energy · estrutura compatível com automação Salesforce</div>
  <div style="font-style:italic;color:var(--text-secondary)">Persistência local via st.session_state · cache SF 5 min</div>
</div>
""", unsafe_allow_html=True)
