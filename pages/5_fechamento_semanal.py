"""
Pagina 5 - Fechamento Semanal Comercial
Modelo baseado no HTML 'fechamento_semanal_flex_2.html' adaptado para Streamlit
e integrado ao Salesforce. Piloto: Flex Energy (kWh primario, sub-segmentado
Interno/Externo/Representantes/Media Tensao). Demais empresas: estrutura disponivel,
mapeamentos especificos sao TODO conforme o template for sendo replicado.

Doc de referencia (regras de negocio): _Brain/Processos/Flex Energy - Fechamento Semanal Comercial.md
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
from datetime import date, timedelta
from config import (
    EMPRESAS, EMPRESA_LABELS, CORES,
    MESES_PT, MESES_PT_FULL,
    dias_uteis_no_mes, dias_uteis_ate_hoje,
    get_logo_b64,
)
from components import icon, var_badge
from salesforce_client import (
    get_leads_periodo, get_leads_origem_periodo, get_leads_status_periodo,
    get_leads_vendedor_periodo, get_energy_consumo_declarado_periodo,
    get_accounts_criadas_periodo, get_opps_criadas_periodo,
    get_opps_ganhas_periodo, get_energy_kwh_periodo,
    get_pipeline_termometro, get_qualidade_contas_energy,
)


# ============================================================
# Helpers
# ============================================================

def _fmt(v):
    try:
        return f"{int(v):,}".replace(",", ".")
    except Exception:
        return "0"


def _fv(v):
    try:
        v = float(v)
    except Exception:
        return "R$ 0"
    if v <= 0:
        return "R$ 0"
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"


def _fk(v):
    try:
        v = float(v)
    except Exception:
        return "0 kWh"
    if v <= 0:
        return "0 kWh"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000:
        return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"


def _delta_pct(atual, anterior):
    try:
        atual = float(atual or 0)
        anterior = float(anterior or 0)
    except Exception:
        return None
    if anterior == 0:
        if atual > 0:
            return None  # "novo"
        return 0.0
    return (atual - anterior) / anterior * 100


def _delta_str(p):
    if p is None:
        return "—"
    if p > 0:
        return f"↑ {p:+.0f}%"
    if p < 0:
        return f"↓ {p:+.0f}%"
    return "→ 0%"


def _delta_color(p):
    if p is None:
        return "var(--text-muted)"
    if p > 1:
        return "#059669"
    if p < -1:
        return "#dc2626"
    return "var(--text-muted)"


def _semana_de(d: date):
    """Retorna (segunda, domingo) da semana que contem d."""
    seg = d - timedelta(days=d.weekday())
    dom = seg + timedelta(days=6)
    return seg, dom


def _persist_key(empresa: str, semana_seg: date) -> str:
    return f"fech_{empresa.replace(' ', '_').lower()}_{semana_seg.isoformat()}"


def _txt(state_key: str, label: str, placeholder: str = "", height: int = 80, key_suffix: str = "") -> str:
    """Textarea persistente em st.session_state."""
    full_key = f"{state_key}__{key_suffix}" if key_suffix else state_key
    val = st.session_state.get(full_key, "")
    new = st.text_area(label, value=val, placeholder=placeholder, height=height, key=f"ta_{full_key}", label_visibility="visible")
    st.session_state[full_key] = new
    return new


def _num(state_key: str, label: str, key_suffix: str = "", step: float = 1.0) -> float:
    full_key = f"{state_key}__{key_suffix}" if key_suffix else state_key
    val = st.session_state.get(full_key, 0.0)
    new = st.number_input(label, value=float(val), step=step, key=f"ni_{full_key}", label_visibility="visible")
    st.session_state[full_key] = new
    return new


# ============================================================
# Header da pagina
# ============================================================

st.markdown("""
<div style="background:#1a1a2e;padding:18px 26px;border-radius:14px;margin-bottom:18px">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
    <div>
      <h1 style="color:white;margin:0;font-size:1.8rem;letter-spacing:-0.5px">📋 Fechamento Semanal Comercial</h1>
      <p style="color:#EC8500;margin:4px 0 0 0;font-size:0.85rem">
        Relatorio semanal por empresa · piloto <b>Flex Energy</b> (kWh primario) ·
        integrado ao Salesforce em tempo real
      </p>
    </div>
    <div style="text-align:right;color:#a1a1aa;font-size:0.7rem;font-family:ui-monospace,monospace">
      v1.0 · cache 5min<br>
      <span style="color:#EC8500;font-weight:700">SF · live</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Controles · empresa + semana
# ============================================================

col_emp, col_sem, col_acoes = st.columns([2, 2, 1])
with col_emp:
    # Default Flex Energy. As demais ficam disponiveis mas exibem aviso de "modelo nao adaptado".
    emp_idx = 0
    emp_options = ["Flex Energy"] + [e for e in EMPRESAS if e != "Flex Energy"]
    empresa = st.selectbox("Empresa", emp_options, index=emp_idx, key="fech_empresa",
                           format_func=lambda e: EMPRESA_LABELS.get(e, e))

with col_sem:
    hoje = date.today()
    semana_atual_seg, _ = _semana_de(hoje)
    # opcoes: ultimas 8 semanas
    semanas_opts = [(semana_atual_seg - timedelta(weeks=i)) for i in range(8)]
    def _fmt_sem(seg: date):
        dom = seg + timedelta(days=6)
        return f"Sem {seg.isocalendar().week:02d} · {seg.strftime('%d/%m')}–{dom.strftime('%d/%m')}"
    sem_sel = st.selectbox("Semana", semanas_opts, index=0, key="fech_semana", format_func=_fmt_sem)

with col_acoes:
    st.write("")
    st.write("")
    if st.button("🔄 Recarregar SF", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

sem_seg, sem_dom = _semana_de(sem_sel)
sem_seg_ant, sem_dom_ant = sem_seg - timedelta(days=7), sem_dom - timedelta(days=7)
mes_a, mes_m = sem_seg.year, sem_seg.month
du_h = dias_uteis_ate_hoje(mes_a, mes_m) if (mes_a, mes_m) == (hoje.year, hoje.month) else dias_uteis_no_mes(mes_a, mes_m)
du_t = dias_uteis_no_mes(mes_a, mes_m)
# Mes corrente do MTD (data fim da semana selecionada)
mtd_inicio = date(mes_a, mes_m, 1)
mtd_fim = sem_dom

# Cor da empresa (banner)
cor_emp = CORES.get(empresa, {}).get("primaria", "#EC8500")
logo_emp = get_logo_b64(empresa)
logo_html = (
    f'<img src="{logo_emp}" style="height:36px;width:36px;border-radius:8px;object-fit:cover" alt=""/>'
    if logo_emp else
    f'<div style="height:36px;width:36px;border-radius:8px;background:{cor_emp};display:flex;align-items:center;justify-content:center;color:white;font-weight:800">{empresa[:1]}</div>'
)

st.markdown(f"""
<div style="background:linear-gradient(90deg,{cor_emp}18,transparent);border-left:4px solid {cor_emp};
            padding:14px 18px;border-radius:8px;margin:6px 0 22px 0;
            display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap">
  <div style="display:flex;align-items:center;gap:12px">
    {logo_html}
    <div>
      <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px">Empresa em foco</div>
      <div style="font-size:1.4rem;font-weight:800;color:{cor_emp};line-height:1.1">{EMPRESA_LABELS.get(empresa, empresa)}</div>
    </div>
  </div>
  <div style="text-align:right;font-family:ui-monospace,monospace;font-size:0.75rem;color:var(--text-secondary)">
    <div>Semana: <b style="color:var(--text)">{sem_seg.strftime('%d/%m/%Y')} a {sem_dom.strftime('%d/%m/%Y')}</b></div>
    <div>MTD: <b style="color:var(--text)">{MESES_PT_FULL.get(mes_m,'')} {mes_a}</b> · DU {du_h}/{du_t}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# Aviso para empresas ainda nao adaptadas
if empresa != "Flex Energy":
    st.warning(
        f"⚠ O modelo de fechamento foi desenhado a partir do template **Flex Energy** "
        f"(medida primaria em kWh, sub-segmentos Interno/Externo/Representantes/Media Tensao). "
        f"Para **{EMPRESA_LABELS.get(empresa, empresa)}**, as queries estao ativas mas os "
        f"sub-segmentos especificos serao mapeados no proximo ciclo. Use a visao geral abaixo "
        f"para acompanhar a estrutura base."
    )


# ============================================================
# Carregar dados Salesforce
# ============================================================

with st.spinner("Carregando Salesforce..."):
    try:
        # Leads
        df_leads_sem = get_leads_periodo(empresa, sem_seg, sem_dom)
        df_leads_sem_ant = get_leads_periodo(empresa, sem_seg_ant, sem_dom_ant)
        df_leads_origem = get_leads_origem_periodo(empresa, sem_seg, sem_dom)
        df_leads_status = get_leads_status_periodo(empresa, sem_seg, sem_dom)
        df_leads_vend = get_leads_vendedor_periodo(empresa, sem_seg, sem_dom)
        # Contas
        contas_sem = get_accounts_criadas_periodo(empresa, sem_seg, sem_dom)
        contas_sem_ant = get_accounts_criadas_periodo(empresa, sem_seg_ant, sem_dom_ant)
        # Oportunidades
        df_opps_sem = get_opps_criadas_periodo(empresa, sem_seg, sem_dom)
        df_opps_sem_ant = get_opps_criadas_periodo(empresa, sem_seg_ant, sem_dom_ant)
        # Vendas (Fechado Ganho)
        df_vendas_sem = get_opps_ganhas_periodo(empresa, sem_seg, sem_dom)
        df_vendas_sem_ant = get_opps_ganhas_periodo(empresa, sem_seg_ant, sem_dom_ant)
        df_vendas_mtd = get_opps_ganhas_periodo(empresa, mtd_inicio, mtd_fim)
        # Pipeline (snapshot atual)
        df_pipeline = get_pipeline_termometro(empresa)
        # Flex Energy: kWh
        if empresa == "Flex Energy":
            kwh_orcado_sem = get_energy_kwh_periodo(sem_seg, sem_dom, ganhas=False)
            kwh_orcado_sem_ant = get_energy_kwh_periodo(sem_seg_ant, sem_dom_ant, ganhas=False)
            kwh_orcado_mtd = get_energy_kwh_periodo(mtd_inicio, mtd_fim, ganhas=False)
            kwh_vendido_sem = get_energy_kwh_periodo(sem_seg, sem_dom, ganhas=True)
            kwh_vendido_mtd = get_energy_kwh_periodo(mtd_inicio, mtd_fim, ganhas=True)
            df_consumo_decl = get_energy_consumo_declarado_periodo(sem_seg, sem_dom)
        else:
            kwh_orcado_sem = kwh_orcado_sem_ant = kwh_orcado_mtd = {"kwh": 0, "opps": 0}
            kwh_vendido_sem = kwh_vendido_mtd = {"kwh": 0, "opps": 0}
            df_consumo_decl = pd.DataFrame()
        sf_ok = True
        sf_err = None
    except Exception as e:
        sf_ok = False
        sf_err = str(e)
        st.error(f"Falha ao consultar Salesforce: {sf_err[:200]}")
        st.stop()


# Totais
leads_total_sem = int(df_leads_sem["total"].sum()) if not df_leads_sem.empty else 0
leads_total_ant = int(df_leads_sem_ant["total"].sum()) if not df_leads_sem_ant.empty else 0
leads_convertidos_sem = int(df_leads_sem[df_leads_sem["IsConverted"] == True]["total"].sum()) if not df_leads_sem.empty and "IsConverted" in df_leads_sem.columns else 0

opps_total_sem = int(df_opps_sem["total"].sum()) if not df_opps_sem.empty else 0
opps_total_ant = int(df_opps_sem_ant["total"].sum()) if not df_opps_sem_ant.empty else 0
opps_valor_sem = float(df_opps_sem["valor"].sum()) if not df_opps_sem.empty and "valor" in df_opps_sem.columns else 0.0

vendas_total_sem = len(df_vendas_sem) if not df_vendas_sem.empty else 0
vendas_total_ant = len(df_vendas_sem_ant) if not df_vendas_sem_ant.empty else 0
vendas_valor_sem = float(df_vendas_sem["Amount"].sum()) if not df_vendas_sem.empty and "Amount" in df_vendas_sem.columns else 0.0
vendas_valor_mtd = float(df_vendas_mtd["Amount"].sum()) if not df_vendas_mtd.empty and "Amount" in df_vendas_mtd.columns else 0.0


# ============================================================
# Chave de persistencia (textos manuais)
# ============================================================

PKEY = _persist_key(empresa, sem_seg)


# ============================================================
# KPI HERO · LINHA 1 (semana vs semana anterior)
# ============================================================

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;
            font-family:ui-monospace,monospace;font-size:10px;text-transform:uppercase;letter-spacing:.18em;
            color:var(--text);font-weight:600;margin:8px 0 6px 0;padding-bottom:5px;border-bottom:1px solid var(--border)">
  <span>Indicadores da semana</span>
  <span style="color:{cor_emp};font-style:italic;font-size:11px;text-transform:none;letter-spacing:.1em">
    comparativo vs semana anterior · {sem_seg_ant.strftime('%d/%m')}–{sem_dom_ant.strftime('%d/%m')}
  </span>
</div>
""", unsafe_allow_html=True)


def kpi_card(label, value, delta_pct, accent="#1a1a2e", caption_extra=""):
    delta_html = ""
    if delta_pct is None:
        delta_html = '<span style="color:var(--text-muted);font-family:ui-monospace,monospace;font-size:0.7rem">→ —</span>'
    else:
        col = _delta_color(delta_pct)
        delta_html = (
            f'<span style="color:{col};font-family:ui-monospace,monospace;font-size:0.72rem;font-weight:700">'
            f'{_delta_str(delta_pct)}</span>'
            f' <span style="color:var(--text-muted);font-size:0.6rem;text-transform:uppercase;letter-spacing:1px">vs sem. ant.</span>'
        )
    extra = f'<div style="font-size:0.65rem;color:var(--text-muted);margin-top:3px">{caption_extra}</div>' if caption_extra else ""
    return (
        '<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;'
        'padding:14px 16px;min-height:110px;display:flex;flex-direction:column;justify-content:space-between">'
        f'<div><div style="font-family:ui-monospace,monospace;font-size:10px;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:1.8rem;font-weight:800;color:{accent};line-height:1;letter-spacing:-0.5px;'
        f'font-feature-settings:\'tnum\'">{value}</div></div>'
        f'<div style="margin-top:8px">{delta_html}{extra}</div>'
        '</div>'
    )


c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card("Leads gerados", _fmt(leads_total_sem),
                         _delta_pct(leads_total_sem, leads_total_ant), cor_emp), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Contas criadas", _fmt(contas_sem),
                         _delta_pct(contas_sem, contas_sem_ant), cor_emp), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Orcamentos gerados", _fmt(opps_total_sem),
                         _delta_pct(opps_total_sem, opps_total_ant), cor_emp,
                         caption_extra=_fv(opps_valor_sem)), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Vendas fechadas", _fmt(vendas_total_sem),
                         _delta_pct(vendas_total_sem, vendas_total_ant), cor_emp,
                         caption_extra=_fv(vendas_valor_sem)), unsafe_allow_html=True)


# ============================================================
# KPI HERO · LINHA 2 (Volume & Ticket medio · MTD)
# ============================================================

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;
            font-family:ui-monospace,monospace;font-size:10px;text-transform:uppercase;letter-spacing:.18em;
            color:var(--text);font-weight:600;margin:18px 0 6px 0;padding-bottom:5px;border-bottom:1px solid var(--border)">
  <span>Volume &amp; ticket medio · {'kWh primario · Flex Energy' if empresa == 'Flex Energy' else 'R$'}</span>
  <span style="color:{cor_emp};font-style:italic;font-size:11px;text-transform:none;letter-spacing:.1em">
    ticket medio sempre acumulado no mes (MTD)
  </span>
</div>
""", unsafe_allow_html=True)

if empresa == "Flex Energy":
    vol_orc_sem = kwh_orcado_sem["kwh"]
    vol_orc_sem_ant = kwh_orcado_sem_ant["kwh"]
    vol_orc_mtd = kwh_orcado_mtd["kwh"]
    ticket_orc_mtd = (vol_orc_mtd / kwh_orcado_mtd["opps"]) if kwh_orcado_mtd["opps"] > 0 else 0
    vol_ven_sem = kwh_vendido_sem["kwh"]
    vol_ven_mtd = kwh_vendido_mtd["kwh"]
    ticket_ven_mtd = (vol_ven_mtd / kwh_vendido_mtd["opps"]) if kwh_vendido_mtd["opps"] > 0 else 0
    fmt = _fk
    unidade_label = "kWh"
else:
    vol_orc_sem = opps_valor_sem
    vol_orc_sem_ant = float(df_opps_sem_ant["valor"].sum()) if not df_opps_sem_ant.empty and "valor" in df_opps_sem_ant.columns else 0.0
    # MTD orcado eh complexo; aproximacao: somar valores das opps do MTD
    df_opps_mtd = get_opps_criadas_periodo(empresa, mtd_inicio, mtd_fim)
    opps_mtd_qtd = int(df_opps_mtd["total"].sum()) if not df_opps_mtd.empty else 0
    vol_orc_mtd = float(df_opps_mtd["valor"].sum()) if not df_opps_mtd.empty and "valor" in df_opps_mtd.columns else 0.0
    ticket_orc_mtd = (vol_orc_mtd / opps_mtd_qtd) if opps_mtd_qtd > 0 else 0
    vol_ven_sem = vendas_valor_sem
    vol_ven_mtd = vendas_valor_mtd
    ticket_ven_mtd = (vol_ven_mtd / len(df_vendas_mtd)) if not df_vendas_mtd.empty else 0
    fmt = _fv
    unidade_label = "R$"


def kpi_card_volume(label, value, secondary_label, secondary_value, accent):
    return (
        '<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;'
        'padding:14px 16px;min-height:110px;display:flex;flex-direction:column;justify-content:space-between">'
        f'<div><div style="font-family:ui-monospace,monospace;font-size:10px;color:var(--text-muted);'
        f'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:1.6rem;font-weight:800;color:{accent};line-height:1;letter-spacing:-0.5px;'
        f'font-feature-settings:\'tnum\'">{value}</div></div>'
        f'<div style="margin-top:8px;font-family:ui-monospace,monospace;font-size:0.7rem;color:var(--text-muted)">'
        f'<span style="text-transform:uppercase;letter-spacing:1px">{secondary_label}</span> '
        f'<b style="color:var(--text-secondary)">{secondary_value}</b></div>'
        '</div>'
    )


c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card_volume("Orcamentos · Volume semana", fmt(vol_orc_sem),
                                "Acumulado mes", fmt(vol_orc_mtd), cor_emp), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card_volume("Orcamentos · Ticket medio MTD", fmt(ticket_orc_mtd),
                                "Volume MTD", fmt(vol_orc_mtd), cor_emp), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card_volume("Vendas · Volume semana", fmt(vol_ven_sem),
                                "Acumulado mes", fmt(vol_ven_mtd), cor_emp), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card_volume("Vendas · Ticket medio MTD", fmt(ticket_ven_mtd),
                                "Volume MTD", fmt(vol_ven_mtd), cor_emp), unsafe_allow_html=True)


# ============================================================
# Helper: section header
# ============================================================

def section_head(num, titulo, desc):
    st.markdown(f"""
    <div style="display:flex;align-items:baseline;gap:14px;margin:34px 0 16px 0;
                padding-bottom:6px;border-bottom:1px solid var(--text)">
      <span style="font-family:ui-monospace,monospace;font-size:11px;color:{cor_emp};
                   font-weight:700;letter-spacing:1.2px">§ {num}</span>
      <h2 style="font-size:1.5rem;font-weight:700;letter-spacing:-0.4px;margin:0;color:var(--text)">{titulo}</h2>
      <span style="margin-left:auto;font-size:0.75rem;color:var(--text-muted);font-style:italic;max-width:50%;text-align:right">{desc}</span>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# § 01 LEADS
# ============================================================

section_head("01", "Leads", "Origem, distribuicao entre vendedores, tratativa e status atual")

# A · Origem
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin-bottom:10px">A · Origem dos leads na semana</div>', unsafe_allow_html=True)

# Buckets para o painel
def _origem_bucket(src):
    if not src:
        return "Outro"
    src_l = str(src).lower()
    if "exact" in src_l:
        return "Exact Sales · Pre-Vendas"
    if "meta" in src_l or "google" in src_l:
        return "Trafego Pago · SDR2"
    if "indica" in src_l:
        return "Indicacao / Carteira"
    if "prospec" in src_l:
        return "Prospeccao Ativa"
    return "Outro"

if not df_leads_origem.empty:
    df_o = df_leads_origem.copy()
    df_o["LeadSource"] = df_o["LeadSource"].fillna("Outro")
    df_o["bucket"] = df_o["LeadSource"].apply(_origem_bucket)
    df_buckets = df_o.groupby("bucket", as_index=False)["total"].sum()
    total_origem = int(df_buckets["total"].sum())
    df_buckets["pct"] = df_buckets["total"].apply(lambda v: f"{v/total_origem*100:.0f}%" if total_origem > 0 else "0%")
    # Ordenar pela ordem padrao do template
    ordem = ["Exact Sales · Pre-Vendas", "Trafego Pago · SDR2", "Indicacao / Carteira", "Prospeccao Ativa", "Outro"]
    df_buckets["ord"] = df_buckets["bucket"].apply(lambda b: ordem.index(b) if b in ordem else 99)
    df_buckets = df_buckets.sort_values("ord").drop(columns=["ord"])
    df_buckets = df_buckets.rename(columns={"bucket": "Origem", "total": "Quantidade", "pct": "% do total"})
    st.dataframe(df_buckets[["Origem", "Quantidade", "% do total"]], hide_index=True, use_container_width=True)
else:
    st.info("Sem leads no periodo selecionado.")

# B · Distribuicao entre vendedores
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin:22px 0 10px 0">B · Distribuicao entre vendedores</div>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<div style="font-family:ui-monospace,monospace;font-size:10px;color:{cor_emp};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">↳ Flex Energy: sub-segmento Interno / Externo / Representantes / Media Tensao (TODO: mapa de Owner→segmento)</div>', unsafe_allow_html=True)

if not df_leads_vend.empty:
    df_v = df_leads_vend.copy()
    # df_leads_vend tem vendedor (alias de Owner.Name), Status, IsConverted, total
    # Fallback se a coluna nao existir com alias
    if "vendedor" not in df_v.columns:
        for cand in ["Owner.Name", "Name", "expr0"]:
            if cand in df_v.columns:
                df_v = df_v.rename(columns={cand: "vendedor"})
                break
        else:
            df_v["vendedor"] = "—"
    df_v["vendedor"] = df_v["vendedor"].fillna("(sem proprietario)")
    df_v["recebidos"] = df_v["total"]
    df_v["tratados"] = df_v.apply(lambda r: r["total"] if r.get("Status") and r.get("Status") != "Aberto" else 0, axis=1)
    df_v["convertidos"] = df_v.apply(lambda r: r["total"] if r.get("IsConverted") else 0, axis=1)
    agg = df_v.groupby("vendedor", as_index=False).agg({
        "recebidos": "sum", "tratados": "sum", "convertidos": "sum"
    })
    agg = agg.sort_values("recebidos", ascending=False).head(20)
    agg["% Tratativa"] = agg.apply(lambda r: f"{r['tratados']/r['recebidos']*100:.0f}%" if r["recebidos"] > 0 else "—", axis=1)
    agg["% Conversao"] = agg.apply(lambda r: f"{r['convertidos']/r['recebidos']*100:.0f}%" if r["recebidos"] > 0 else "—", axis=1)
    agg = agg.rename(columns={
        "vendedor": "Vendedor",
        "recebidos": "Leads recebidos",
        "tratados": "Tratados",
        "convertidos": "Convertidos p/ Conta",
    })
    st.dataframe(agg[["Vendedor", "Leads recebidos", "Tratados", "% Tratativa", "Convertidos p/ Conta", "% Conversao"]],
                 hide_index=True, use_container_width=True)
else:
    st.info("Sem distribuicao por vendedor no periodo.")

# B.1 · Consumo declarado kWh (exclusivo Flex Energy)
if empresa == "Flex Energy":
    st.markdown(f'<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:{cor_emp};margin:22px 0 10px 0">B.1 · Consumo declarado · <b>kWh</b> · exclusivo Flex Energy</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem;color:var(--text-muted);font-style:italic;margin-bottom:10px">Volume em kWh eh a medida primaria. Ticket medio considerado como <b>acumulado mensal (MTD)</b>.</div>', unsafe_allow_html=True)
    if not df_consumo_decl.empty:
        df_kc = df_consumo_decl.copy()
        # Fallback se alias vendedor nao veio
        if "vendedor" not in df_kc.columns:
            for cand in ["Owner.Name", "Name", "expr0"]:
                if cand in df_kc.columns:
                    df_kc = df_kc.rename(columns={cand: "vendedor"})
                    break
            else:
                df_kc["vendedor"] = "—"
        df_kc["consumo_medio"] = df_kc.apply(lambda r: r["total_kwh"] / r["total_leads"] if r["total_leads"] > 0 else 0, axis=1)
        df_kc = df_kc.rename(columns={
            "vendedor": "Vendedor",
            "total_leads": "Leads na semana",
            "total_kwh": "Consumo total (kWh)",
            "consumo_medio": "Consumo medio/lead (kWh)",
        })
        df_kc["Consumo total (kWh)"] = df_kc["Consumo total (kWh)"].apply(lambda v: f"{v:,.0f}".replace(",", "."))
        df_kc["Consumo medio/lead (kWh)"] = df_kc["Consumo medio/lead (kWh)"].apply(lambda v: f"{v:,.0f}".replace(",", "."))
        st.dataframe(df_kc[["Vendedor", "Leads na semana", "Consumo total (kWh)", "Consumo medio/lead (kWh)"]],
                     hide_index=True, use_container_width=True)
        st.caption(f"Ticket medio kWh MTD (Flex Energy, base Opps criadas): **{_fk(ticket_orc_mtd)}**")
    else:
        st.info("Sem leads com consumo declarado na semana.")

# C · Status dos leads ao fim da semana
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin:22px 0 10px 0">C · Status dos leads ao fim da semana</div>', unsafe_allow_html=True)
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
        ("Desqualificados", desqualif, "leads", "#ef4444"),
        ("Sem acao ⚠", sem_acao, "SLA estourado / em aberto", "#dc2626"),
    ]
    cols = st.columns(5)
    for col, (label, qtd, sub, c) in zip(cols, buckets):
        with col:
            st.markdown(
                f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center">'
                f'<div style="font-family:ui-monospace,monospace;font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">{label}</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{c};line-height:1">{qtd}</div>'
                f'<div style="font-size:0.65rem;color:var(--text-muted);margin-top:3px">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# Observacoes
with st.expander("📝 Observacoes · Leads", expanded=False):
    _txt(PKEY, "Analise da semana", placeholder="Qualidade dos leads, gargalos na tratativa, padroes na origem, comportamento Pre-Vendas/SDR2…",
         height=80, key_suffix="obs_leads")


# ============================================================
# § 02 CONTAS
# ============================================================

section_head("02", "Contas", "Criacao, equiparacao com leads convertidos e qualidade do cadastro")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin-bottom:10px">A · Volume vs Leads</div>', unsafe_allow_html=True)
    diff = contas_sem - leads_convertidos_sem
    diff_color = "#10b981" if abs(diff) <= 1 else "#f59e0b"
    df_va = pd.DataFrame({
        "Indicador": [
            "Leads convertidos p/ Conta",
            "Contas criadas no Salesforce",
            "Diferenca (esperado ~0)",
        ],
        "Valor": [
            leads_convertidos_sem,
            contas_sem,
            diff,
        ],
    })
    st.dataframe(df_va, hide_index=True, use_container_width=True)
    if abs(diff) > 1:
        st.warning(f"⚠ Diferenca de {diff:+d} entre leads convertidos e contas criadas - verificar conversao manual ou contas sem origem em lead.")

with col_b:
    st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin-bottom:10px">B · Qualidade do cadastro (snapshot)</div>', unsafe_allow_html=True)
    qual = get_qualidade_contas_energy(sem_seg, sem_dom) if empresa == "Flex Energy" else None
    if qual and qual["total"] > 0:
        total_q = qual["total"]
        df_qual = pd.DataFrame({
            "Criterio": ["Razao Social preenchida", "Setor / Classificacao", "Endereco completo"],
            "Conformes": [qual["razao_social_ok"], qual["setor_ok"], qual["endereco_ok"]],
            "Inconformes": [
                total_q - qual["razao_social_ok"],
                total_q - qual["setor_ok"],
                total_q - qual["endereco_ok"],
            ],
        })
        st.dataframe(df_qual, hide_index=True, use_container_width=True)
        st.caption(f"Base: {total_q} contas {empresa} criadas no periodo")
    else:
        st.info("Sem contas no periodo ou criterios indisponiveis.")

# Observacoes
with st.expander("📝 Observacoes · Contas", expanded=False):
    _txt(PKEY, "Aderencia leads x contas, padroes de erro no cadastro, reforco de processo…",
         height=70, key_suffix="obs_contas")


# ============================================================
# § 03 OPORTUNIDADES
# ============================================================

section_head("03", "Oportunidades", "Producao semanal + pipeline em aberto · termometro de negociacao")

# A · Producao da semana
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin-bottom:10px">A · Producao da semana por vendedor</div>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<div style="font-family:ui-monospace,monospace;font-size:10px;color:{cor_emp};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">↳ Flex Energy: discriminar por Interno / Externo / Representantes / Media Tensao · medida primaria em <b>kWh</b></div>', unsafe_allow_html=True)
if not df_opps_sem.empty:
    df_p = df_opps_sem.copy()
    # Fallback se alias vendedor nao veio
    if "vendedor" not in df_p.columns:
        for cand in ["Owner.Name", "Name", "expr0"]:
            if cand in df_p.columns:
                df_p = df_p.rename(columns={cand: "vendedor"})
                break
        else:
            df_p["vendedor"] = "—"
    df_p["vendedor"] = df_p["vendedor"].fillna("(sem proprietario)")
    agg_p = df_p.groupby("vendedor", as_index=False).agg({"total": "sum", "valor": "sum"})
    # Fase predominante por vendedor
    fase_pred = df_p.sort_values("total", ascending=False).groupby("vendedor")["StageName"].first().to_dict()
    agg_p["Fase predominante"] = agg_p["vendedor"].map(fase_pred)
    agg_p["Ticket medio"] = agg_p.apply(lambda r: f"R$ {r['valor']/r['total']:,.0f}".replace(",", ".") if r["total"] > 0 and r["valor"] else "—", axis=1)
    agg_p = agg_p.sort_values("total", ascending=False).head(20)
    agg_p = agg_p.rename(columns={"vendedor": "Vendedor", "total": "Orcamentos criados", "valor": "Volume R$"})
    agg_p["Volume R$"] = agg_p["Volume R$"].apply(_fv)
    st.dataframe(agg_p[["Vendedor", "Orcamentos criados", "Volume R$", "Ticket medio", "Fase predominante"]],
                 hide_index=True, use_container_width=True)
    # Total + MTD destacado
    total_sem_orc = int(df_p["total"].sum())
    total_sem_val = float(df_p["valor"].sum())
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">'
        f'<div style="background:var(--bg-overlay);padding:10px 14px;border-radius:8px;font-size:0.85rem">'
        f'<b>Total semanal:</b> {total_sem_orc} orcamentos · {_fv(total_sem_val)}'
        f'</div>'
        f'<div style="background:{cor_emp}18;border-left:4px solid {cor_emp};padding:10px 14px;border-radius:8px;font-size:0.85rem">'
        f'<b style="color:{cor_emp}">Acumulado MTD:</b> '
        f'{int(df_opps_mtd["total"].sum()) if (empresa != "Flex Energy" and not df_opps_mtd.empty) else kwh_orcado_mtd["opps"]} opps · '
        f'{_fk(kwh_orcado_mtd["kwh"]) if empresa == "Flex Energy" else _fv(vol_orc_mtd)} · '
        f'ticket medio: {_fk(ticket_orc_mtd) if empresa == "Flex Energy" else _fv(ticket_orc_mtd)}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Sem oportunidades criadas no periodo.")

# B · Pipeline em aberto · termometro
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin:22px 0 10px 0">B · Pipeline em aberto · termometro de negociacao</div>', unsafe_allow_html=True)
buckets_pipe = {
    "Indo para contrato": {"qtd": 0, "vol": 0.0, "dot": "#10b981"},
    "Quente · negociacao": {"qtd": 0, "vol": 0.0, "dot": cor_emp},
    "Morno · contato ativo": {"qtd": 0, "vol": 0.0, "dot": "#f59e0b"},
    "Frio · contato passivo (ODR)": {"qtd": 0, "vol": 0.0, "dot": "#6b9bd1"},
}
if not df_pipeline.empty:
    for _, r in df_pipeline.iterrows():
        fase = r.get("fase")
        temp = r.get("temp") if "temp" in r.index else None
        qtd = int(r.get("total", 0))
        vol = float(r.get("volume_kwh", r.get("volume_rs", 0)) or 0)
        if fase == "Contrato":
            buckets_pipe["Indo para contrato"]["qtd"] += qtd
            buckets_pipe["Indo para contrato"]["vol"] += vol
        elif fase == "Negociacao" or temp == "Quente":
            buckets_pipe["Quente · negociacao"]["qtd"] += qtd
            buckets_pipe["Quente · negociacao"]["vol"] += vol
        elif fase == "Contato Ativo" or temp == "Morno":
            buckets_pipe["Morno · contato ativo"]["qtd"] += qtd
            buckets_pipe["Morno · contato ativo"]["vol"] += vol
        elif fase == "Contato Passivo" or temp == "Frio":
            buckets_pipe["Frio · contato passivo (ODR)"]["qtd"] += qtd
            buckets_pipe["Frio · contato passivo (ODR)"]["vol"] += vol

cols_t = st.columns(4)
for col, (label, b) in zip(cols_t, buckets_pipe.items()):
    vol_fmt = _fk(b["vol"]) if empresa == "Flex Energy" else _fv(b["vol"])
    with col:
        st.markdown(
            f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;min-height:110px">'
            f'<div style="font-family:ui-monospace,monospace;font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;display:flex;align-items:center;gap:6px">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{b["dot"]}"></span>{label}</div>'
            f'<div style="font-size:1.7rem;font-weight:800;color:var(--text);line-height:1">{b["qtd"]}</div>'
            f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:6px;font-family:ui-monospace,monospace">Volume: <b style="color:var(--text-secondary)">{vol_fmt}</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# C · ODR (manual no template - mantido como inputs persistidos)
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin:22px 0 10px 0">C · Atuacao do ODR · resgate de oportunidades frias</div>', unsafe_allow_html=True)
with st.expander("Preencher / editar dados ODR", expanded=False):
    odr_cols = st.columns(2)
    with odr_cols[0]:
        odr_trab_sem = _num(PKEY, "Trabalhadas pelo ODR · semana", key_suffix="odr_trab_sem")
        odr_reat_sem = _num(PKEY, "Reativadas (esquentaram) · semana", key_suffix="odr_reat_sem")
        odr_conv_sem = _num(PKEY, "Convertidas em venda · semana", key_suffix="odr_conv_sem")
        odr_desc_sem = _num(PKEY, "Descartadas definitivamente · semana", key_suffix="odr_desc_sem")
    with odr_cols[1]:
        odr_trab_mtd = _num(PKEY, "Trabalhadas pelo ODR · MTD", key_suffix="odr_trab_mtd")
        odr_reat_mtd = _num(PKEY, "Reativadas · MTD", key_suffix="odr_reat_mtd")
        odr_conv_mtd = _num(PKEY, "Convertidas em venda · MTD", key_suffix="odr_conv_mtd")
        odr_desc_mtd = _num(PKEY, "Descartadas · MTD", key_suffix="odr_desc_mtd")
df_odr = pd.DataFrame({
    "Indicador": ["Trabalhadas pelo ODR", "Reativadas (esquentaram)", "Convertidas em venda", "Descartadas definitivamente"],
    "Semana": [int(st.session_state.get(f"{PKEY}__odr_trab_sem", 0)), int(st.session_state.get(f"{PKEY}__odr_reat_sem", 0)),
               int(st.session_state.get(f"{PKEY}__odr_conv_sem", 0)), int(st.session_state.get(f"{PKEY}__odr_desc_sem", 0))],
    "MTD": [int(st.session_state.get(f"{PKEY}__odr_trab_mtd", 0)), int(st.session_state.get(f"{PKEY}__odr_reat_mtd", 0)),
            int(st.session_state.get(f"{PKEY}__odr_conv_mtd", 0)), int(st.session_state.get(f"{PKEY}__odr_desc_mtd", 0))],
})
st.dataframe(df_odr, hide_index=True, use_container_width=True)

with st.expander("📝 Observacoes · Oportunidades & Pipeline", expanded=False):
    _txt(PKEY, "Movimentacao do pipeline, opps de destaque, gargalos por fase, performance ODR, alertas de esfriamento…",
         height=80, key_suffix="obs_opps")


# ============================================================
# § 04 VENDAS · META
# ============================================================

section_head("04", "Vendas · Ritmo de Meta", "O que entrou na semana e o pace acumulado contra a meta")

# Bloco de meta
col_m1, col_m2 = st.columns([3, 2])
with col_m1:
    meta_mtd_input = st.number_input(
        f"Meta mensal · {'kWh' if empresa == 'Flex Energy' else 'R$'}",
        value=float(st.session_state.get(f"{PKEY}__meta_mensal", 0.0)),
        step=10000.0,
        key=f"ni_{PKEY}__meta_mensal",
        help="Meta total mensal da empresa. Use 0 se ainda nao houver meta configurada.",
    )
    st.session_state[f"{PKEY}__meta_mensal"] = meta_mtd_input
with col_m2:
    realizado_mtd = vol_ven_mtd
    fmt_loc = _fk if empresa == "Flex Energy" else _fv
    if meta_mtd_input > 0:
        pct_meta = realizado_mtd / meta_mtd_input * 100
        ritmo = (realizado_mtd / du_h) * du_t if du_h > 0 else 0
        pct_ritmo = ritmo / meta_mtd_input * 100 if meta_mtd_input > 0 else 0
    else:
        pct_meta = 0
        pct_ritmo = 0
        ritmo = 0

st.markdown(f"""
<div style="background:linear-gradient(135deg,#1a1a2e 0%,#2a3340 100%);color:#fafafa;
            padding:22px 26px;border-radius:10px;display:grid;grid-template-columns:1fr 320px;gap:24px;align-items:center;margin-top:8px">
  <div>
    <div style="font-family:ui-monospace,monospace;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;opacity:0.7;margin-bottom:6px">
      Atingimento da meta · {MESES_PT_FULL.get(mes_m, '')} {mes_a}
    </div>
    <div style="display:flex;gap:24px;align-items:baseline">
      <div style="font-size:2.4rem;font-weight:800;letter-spacing:-1px;line-height:1">{pct_meta:.0f}%</div>
      <div style="font-family:ui-monospace,monospace;font-size:0.8rem;opacity:0.8">
        Realizado / Meta<br>
        <b style="color:{cor_emp};font-size:1rem;display:block;margin-top:2px">{fmt_loc(realizado_mtd)} / {fmt_loc(meta_mtd_input)}</b>
      </div>
    </div>
    <div style="font-family:ui-monospace,monospace;font-size:0.7rem;opacity:0.75;margin-top:8px;text-transform:uppercase;letter-spacing:1px">
      Ritmo previsto p/ fim do mes: <b>{pct_ritmo:.0f}%</b> ({fmt_loc(ritmo)})
    </div>
  </div>
  <div>
    <div style="height:32px;background:rgba(250,250,247,0.1);border-radius:6px;overflow:hidden">
      <div style="height:100%;background:{cor_emp};width:{min(pct_meta, 100):.0f}%;display:flex;align-items:center;padding:0 10px;font-family:ui-monospace,monospace;font-size:11px;font-weight:700;color:#fff">
        {pct_meta:.0f}%
      </div>
    </div>
    <div style="text-align:center;margin-top:8px;font-family:ui-monospace,monospace;font-size:0.7rem;opacity:0.85">
      Dia util <b>{du_h}</b> de <b>{du_t}</b>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# A · Vendas da semana
st.markdown('<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--text-muted);margin:22px 0 10px 0">A · Vendas da semana (Fechado Ganho)</div>', unsafe_allow_html=True)
if empresa == "Flex Energy":
    st.markdown(f'<div style="font-family:ui-monospace,monospace;font-size:10px;color:{cor_emp};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">↳ Flex Energy: medida primaria em <b>kWh</b> · sub-segmentacao Interno/Externo/Repres./MT por Tipo_de_Conta_ENERGY__c</div>', unsafe_allow_html=True)
if not df_vendas_sem.empty:
    df_vs = df_vendas_sem.copy()
    cols_show = []
    df_vs["Vendedor"] = df_vs.get("Owner.Name", "—")
    df_vs["Cliente"] = df_vs.get("Account.Name", "—")
    df_vs["Ticket R$"] = df_vs["Amount"].apply(_fv) if "Amount" in df_vs.columns else "—"
    df_vs["Data fechamento"] = pd.to_datetime(df_vs["CloseDate"]).dt.strftime("%d/%m/%Y") if "CloseDate" in df_vs.columns else "—"
    if "Tipo_de_Conta_ENERGY__c" in df_vs.columns:
        df_vs["Segmento"] = df_vs["Tipo_de_Conta_ENERGY__c"].fillna("—")
        cols_show = ["Vendedor", "Segmento", "Cliente", "Ticket R$", "Data fechamento"]
    else:
        cols_show = ["Vendedor", "Cliente", "Ticket R$", "Data fechamento"]
    st.dataframe(df_vs[cols_show], hide_index=True, use_container_width=True)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">'
        f'<div style="background:var(--bg-overlay);padding:10px 14px;border-radius:8px;font-size:0.85rem">'
        f'<b>Total semanal:</b> {vendas_total_sem} vendas · {_fv(vendas_valor_sem)}'
        + (f' · {_fk(kwh_vendido_sem["kwh"])}' if empresa == "Flex Energy" else '')
        + f'</div>'
        f'<div style="background:{cor_emp}18;border-left:4px solid {cor_emp};padding:10px 14px;border-radius:8px;font-size:0.85rem">'
        f'<b style="color:{cor_emp}">Acumulado MTD:</b> '
        f'{len(df_vendas_mtd)} vendas · {_fv(vendas_valor_mtd)}'
        + (f' · {_fk(kwh_vendido_mtd["kwh"])}' if empresa == "Flex Energy" else '')
        + f' · ticket medio: {fmt_loc(ticket_ven_mtd)}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Sem vendas (Fechado Ganho) no periodo selecionado.")

with st.expander("📝 Observacoes · Vendas", expanded=False):
    _txt(PKEY, "Destaques, vendas atipicas, mix de produtos/segmentos, riscos para meta…",
         height=80, key_suffix="obs_vendas")


# ============================================================
# § 05 FUNIL DE CONVERSAO
# ============================================================

section_head("05", "Funil de Conversao", "Lead → Conta → Oportunidade → Em negociacao → Venda")

leads_q = leads_total_sem
contas_q = contas_sem
opps_q = opps_total_sem
neg_q = int(df_opps_sem[df_opps_sem["StageName"].isin(["Negociacao", "Contrato"])]["total"].sum()) if not df_opps_sem.empty else 0
vendas_q = vendas_total_sem

base = max(leads_q, 1)
funnel_data = [
    ("Leads", leads_q, 100, None),
    ("Contas", contas_q, contas_q/base*100, (contas_q/leads_q*100) if leads_q > 0 else 0),
    ("Oportunidades", opps_q, opps_q/base*100, (opps_q/contas_q*100) if contas_q > 0 else 0),
    ("Em negociacao", neg_q, neg_q/base*100, (neg_q/opps_q*100) if opps_q > 0 else 0),
    ("Vendas", vendas_q, vendas_q/base*100, (vendas_q/neg_q*100) if neg_q > 0 else 0),
]
funnel_colors = ["#1a1a2e", "#2a3340", "#4a5568", "#718096", cor_emp]
for (label, qtd, pct, conv), color in zip(funnel_data, funnel_colors):
    conv_str = f"↳ {conv:.0f}%" if conv is not None else "base"
    bar_width = max(min(pct, 100), 5)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:150px 1fr 100px 90px;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">'
        f'<div style="font-weight:700;font-size:0.9rem">{label}</div>'
        f'<div style="height:22px;background:var(--bg-subtle);border-radius:4px;overflow:hidden">'
        f'<div style="height:100%;background:{color};width:{bar_width}%;display:flex;align-items:center;padding:0 8px;color:#fff;font-family:ui-monospace,monospace;font-size:11px;font-weight:700">{qtd}</div>'
        f'</div>'
        f'<div style="font-family:ui-monospace,monospace;font-size:0.9rem;font-weight:700;text-align:right">{pct:.0f}%</div>'
        f'<div style="font-family:ui-monospace,monospace;font-size:0.75rem;color:var(--text-muted);text-align:right">{conv_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with st.expander("📝 Observacoes · Funil", expanded=False):
    _txt(PKEY, "Onde esta o maior afunilamento? Perda em Lead → Conta (cadastro) ou Opp → Venda (proposta/preco)?",
         height=70, key_suffix="obs_funil")


# ============================================================
# § 06 COMPARATIVO 4 SEMANAS
# ============================================================

section_head("06", "Comparativo · Ultimas 4 Semanas", "Tendencia mensal · evolucao das principais metricas")

# Coletar dados das 4 semanas (atual + 3 anteriores)
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
            vol_orc_v = kwh_o
            vol_v = kwh_v
        out.append({
            "seg": seg, "dom": dom,
            "leads": leads, "orc": orc, "vol_orc": vol_orc_v,
            "vendas": vendas, "vol_vendas": vol_v,
            "conv": (vendas / leads * 100) if leads > 0 else 0,
        })
    return out

compare = _build_compare(empresa, sem_dom)
labels = [f"Sem {c['seg'].isocalendar().week:02d}" for c in compare]
labels[-1] = labels[-1] + " (atual)"

def _trend_arrow(vals):
    if len(vals) < 2:
        return "—"
    delta = vals[-1] - vals[0]
    if delta > 0:
        return f'<span style="color:#10b981">↑</span>'
    if delta < 0:
        return f'<span style="color:#ef4444">↓</span>'
    return "→"

linhas_cmp = [
    ("Leads", [c["leads"] for c in compare], _fmt),
    ("Orcamentos", [c["orc"] for c in compare], _fmt),
    (f"Volume orcado ({'kWh' if empresa == 'Flex Energy' else 'R$'})", [c["vol_orc"] for c in compare], (_fk if empresa == "Flex Energy" else _fv)),
    ("Vendas (qtd)", [c["vendas"] for c in compare], _fmt),
    (f"Volume vendido ({'kWh' if empresa == 'Flex Energy' else 'R$'})", [c["vol_vendas"] for c in compare], (_fk if empresa == "Flex Energy" else _fv)),
    ("Conv. Lead → Venda", [c["conv"] for c in compare], lambda v: f"{v:.1f}%"),
]
header_html = '<div style="display:grid;grid-template-columns:170px repeat(4,1fr) 80px;gap:0;border:1px solid var(--text);font-size:0.82rem">'
header_html += '<div style="background:var(--text);color:var(--bg);padding:8px 10px;font-family:ui-monospace,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:1px">Indicador</div>'
for lb in labels:
    header_html += f'<div style="background:var(--text);color:var(--bg);padding:8px 10px;font-family:ui-monospace,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:1px;text-align:right">{lb}</div>'
header_html += '<div style="background:var(--text);color:var(--bg);padding:8px 10px;font-family:ui-monospace,monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:1px;text-align:center">Tend.</div>'
for nome, vals, formatter in linhas_cmp:
    header_html += f'<div style="padding:8px 10px;background:var(--bg-overlay);font-weight:700;border-top:1px solid var(--border)">{nome}</div>'
    for idx, v in enumerate(vals):
        bg = "background:#fef3c7;" if idx == len(vals) - 1 else ""
        try:
            v_fmt = formatter(v)
        except Exception:
            v_fmt = "—"
        header_html += f'<div style="padding:8px 10px;font-family:ui-monospace,monospace;text-align:right;border-top:1px solid var(--border);{bg}">{v_fmt}</div>'
    header_html += f'<div style="padding:8px 10px;text-align:center;font-family:ui-monospace,monospace;border-top:1px solid var(--border);font-weight:700">{_trend_arrow(vals)}</div>'
header_html += '</div>'
st.markdown(header_html, unsafe_allow_html=True)


# ============================================================
# § 07 RETROSPECTIVA · § 08 NOTAS · § 09 ALERTA
# ============================================================

section_head("07", "Retrospectiva da Semana", "Preenchido antes da reuniao de segunda · base para discussao")

retro_cols = st.columns(2)
with retro_cols[0]:
    _txt(PKEY, "01 · Como a semana foi?", placeholder="Sintese geral em 2-3 frases: ritmo, clima, eventos relevantes…", height=90, key_suffix="retro_1")
    _txt(PKEY, "03 · O que nao funcionou?", placeholder="Gargalos, falhas de processo, oportunidades perdidas, atritos…", height=90, key_suffix="retro_3")
    _txt(PKEY, "05 · Acoes pendentes", placeholder="O que ficou para tras - e por que. Responsavel e motivo.", height=90, key_suffix="retro_5")
with retro_cols[1]:
    _txt(PKEY, "02 · O que funcionou bem?", placeholder="Boas praticas, vendedores em destaque, processos que fluiram…", height=90, key_suffix="retro_2")
    _txt(PKEY, "04 · Acoes realizadas", placeholder="O que foi executado da semana anterior - vinculado as pendencias.", height=90, key_suffix="retro_4")
    _txt(PKEY, "06 · Acoes para a semana atual", placeholder="Compromissos firmados na segunda.", height=90, key_suffix="retro_6")

section_head("08", "Notas da Reuniao · Segunda-feira", "Preenchido durante o alinhamento com os gestores")
nc = st.columns(2)
with nc[0]:
    _txt(PKEY, "Decisoes tomadas", placeholder="O que foi decidido - direcao, ajustes de meta, mudancas de processo…", height=100, key_suffix="notas_decisoes")
with nc[1]:
    _txt(PKEY, "Pontos de discussao & feedback dos gestores", placeholder="O que cada gestor levantou, divergencias, sugestoes, contexto adicional…", height=100, key_suffix="notas_feedback")

section_head("09", "Alerta", "Algo critico que precisa de atencao imediata")
alerta = st.text_area(
    "Destaque critico da semana",
    value=st.session_state.get(f"{PKEY}__alerta", ""),
    placeholder="SOMENTE para alertas que exigem acao imediata: risco de meta, cliente importante perdido, gargalo grave, escalonamento. Deixe em branco se nada se aplicar.",
    height=80,
    key=f"ta_{PKEY}__alerta",
)
st.session_state[f"{PKEY}__alerta"] = alerta
if alerta.strip():
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#fdf3d4 0%,#fce8e3 100%);border:2px solid {cor_emp};'
        f'border-left:6px solid {cor_emp};padding:18px 22px;margin-top:10px;border-radius:6px;'
        f'display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:start">'
        f'<div style="font-size:2.4rem;font-weight:700;line-height:1;color:{cor_emp};font-family:Georgia,serif">!</div>'
        f'<div>'
        f'<div style="font-family:ui-monospace,monospace;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:{cor_emp};font-weight:700;margin-bottom:6px">Destaque critico da semana</div>'
        f'<div style="font-size:1rem;line-height:1.5;color:#1a1a2e;font-weight:500">{alerta}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

# ============================================================
# Footer
# ============================================================
st.markdown(
    f'<div style="margin-top:36px;padding-top:18px;border-top:1px solid var(--border);'
    f'display:flex;justify-content:space-between;align-items:end;gap:24px;font-size:0.7rem;color:var(--text-muted);font-family:ui-monospace,monospace">'
    f'<div>GFlex Empresas · Fechamento Semanal Comercial · v1.0<br>'
    f'Modelo Flex Energy · estrutura compativel com automacao Salesforce</div>'
    f'<div style="font-style:italic;color:var(--text-secondary)">Persistencia local via st.session_state · cache SF 5 min</div>'
    f'</div>',
    unsafe_allow_html=True,
)
