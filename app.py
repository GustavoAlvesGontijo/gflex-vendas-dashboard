"""
Dashboard de Vendas GFlex - Pagina Inicial (Home)
Login + sidebar + KPIs consolidados + cards de navegacao.
"""
import streamlit as st
import datetime
from datetime import date
import pandas as pd

from config import (
    EMPRESAS, EMPRESA_LABELS, CORES, get_periodo,
    dias_uteis_no_mes, dias_uteis_ate_hoje, MESES_PT_FULL,
)
from styles import inject_css
from components import page_header, icon, empresa_header

st.set_page_config(page_title="GFlex Vendas", page_icon="\U0001f4ca", layout="wide", initial_sidebar_state="expanded")

# ========================================
# AUTENTICACAO - acesso por senha
# ========================================
def check_password():
    """Verifica se o usuario digitou a senha correta."""
    try:
        correct = st.secrets["app"]["password"]
    except Exception:
        import os as _os
        correct = _os.getenv("APP_PASSWORD", "")
        if not correct:
            st.error("Senha nao configurada. Configure st.secrets ou APP_PASSWORD.")
            st.stop()
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("""
<div style="max-width:400px;margin:80px auto;text-align:center">
<div style="background:#1a1a2e;padding:24px;border-radius:14px;margin-bottom:24px">
<h1 style="color:white;margin:0;font-size:1.6rem">\U0001f4ca GFlex Vendas</h1>
<p style="color:#EC8500;margin:6px 0 0 0;font-size:0.85rem">Painel de Vendas - Acesso Restrito</p>
</div>
</div>
""", unsafe_allow_html=True)
    pwd = st.text_input("Senha de acesso", type="password", key="pwd_input")
    if pwd:
        if pwd == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta")
    return False

if not check_password():
    st.stop()

inject_css()

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:12px 0 16px 0;border-bottom:1px solid var(--border);margin-bottom:14px">'
        '<div style="font-size:1.5rem;font-weight:800;color:var(--text);letter-spacing:-0.5px">GFlex</div>'
        '<div style="color:var(--accent);font-size:0.7rem;font-weight:700;letter-spacing:1.8px;text-transform:uppercase;margin-top:2px">Painel de Vendas</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    opcoes = ["Todas"] + [EMPRESA_LABELS[e] for e in EMPRESAS]
    emp_label = st.selectbox("Empresa", opcoes, index=0, key="filtro_empresa")
    emp_sf = None
    if emp_label != "Todas":
        for sv, lb in EMPRESA_LABELS.items():
            if lb == emp_label: emp_sf = sv; break
    st.session_state["empresa_filtro"] = emp_sf if emp_sf else "Todas"
    if emp_sf and emp_sf in CORES:
        st.markdown(f'<div style="width:100%;height:4px;background:{CORES[emp_sf]["primaria"]};border-radius:2px;margin:4px 0 12px 0"></div>', unsafe_allow_html=True)

    st.markdown("##### Periodo")
    periodo = st.selectbox("Periodo", ["Ultimo mes","Ultimo trimestre","Ultimo semestre","Ano atual","Tudo","Personalizado"], index=1, key="filtro_periodo", label_visibility="collapsed")
    if periodo == "Personalizado":
        c1, c2 = st.columns(2)
        with c1: di = st.date_input("De", key="data_inicio")
        with c2: df = st.date_input("Ate", key="data_fim")
    else:
        di, df = get_periodo(periodo)
    st.session_state["data_inicio"] = di
    st.session_state["data_fim"] = df
    st.markdown(
        '<div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--border);'
        'font-size:0.7rem;color:var(--text-muted);text-align:center">'
        'Salesforce API · Cache 5 min</div>',
        unsafe_allow_html=True,
    )

# ========================================
# HOME - banner + KPIs + nav cards
# ========================================

# Saudacao baseada no horario
hora = datetime.datetime.now().hour
saudacao = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
hoje = date.today()
m, a = hoje.month, hoje.year
du_h = dias_uteis_ate_hoje(a, m)
du_t = dias_uteis_no_mes(a, m)
pct = (du_h/du_t*100) if du_t > 0 else 0

st.markdown(page_header(
    title=f"{saudacao}, Gustavo",
    subtitle=f"{MESES_PT_FULL.get(m,'')} {a} · <span style='color:#F7C42D;font-weight:600'>{du_h} de {du_t} dias uteis</span> ({du_h*100//max(du_t,1)}%)",
    status_bar_pct=pct,
), unsafe_allow_html=True)

# ========================================
# KPIs CONSOLIDADOS DO MES
# ========================================
def _fmt(v):
    try: return f"{int(v):,}".replace(",", ".")
    except: return "-"
def _fv(v):
    try: v = float(v)
    except: return "R$ 0"
    if v >= 1_000_000: return f"R$ {v/1_000_000:.1f}M"
    if v >= 1_000: return f"R$ {v/1_000:.0f}k"
    return f"R$ {v:.0f}"
def _fk(v):
    try: v = float(v)
    except: return "0 kWh"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M kWh"
    if v >= 1_000: return f"{v/1_000:.0f}k kWh"
    return f"{int(v)} kWh"

try:
    from salesforce_client import (
        get_leads_mensal_por_empresa, get_opps_mensal_por_empresa,
        get_opps_ganhas_mensal_por_empresa, get_energy_kwh_mensal,
    )
    with st.spinner("Carregando indicadores do mes..."):
        df_l = get_leads_mensal_por_empresa()
        df_o = get_opps_mensal_por_empresa()
        df_g = get_opps_ganhas_mensal_por_empresa()
        df_kwh = get_energy_kwh_mensal()

    cur_l = df_l[(df_l['ano']==a) & (df_l['mes']==m)] if not df_l.empty else df_l
    cur_o = df_o[(df_o['ano']==a) & (df_o['mes']==m)] if not df_o.empty else df_o
    cur_g = df_g[(df_g['ano']==a) & (df_g['mes']==m)] if not df_g.empty else df_g
    cur_k = df_kwh[(df_kwh['ano']==a) & (df_kwh['mes']==m)] if not df_kwh.empty else df_kwh

    total_leads = int(cur_l['total'].sum()) if not cur_l.empty else 0
    total_orc = int(cur_o['total'].sum()) if not cur_o.empty else 0
    total_vendas = int(cur_g['total'].sum()) if not cur_g.empty else 0
    total_valor = float(cur_g['valor'].sum()) if not cur_g.empty else 0
    total_kwh = float(cur_k['total_kwh'].sum()) if not cur_k.empty else 0

    # 4 KPIs consolidados em grid
    st.markdown(
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px">'
        # Leads
        '<div class="gx-card" style="background:#3b82f60a;border-left:4px solid #3b82f6">'
        f'<div style="display:flex;align-items:center;gap:6px;font-size:0.65rem;color:#1d4ed8;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px">{icon("users",13,"#1d4ed8")} Leads no Mes</div>'
        f'<div style="font-size:1.9rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\';line-height:1">{_fmt(total_leads)}</div>'
        '<div style="font-size:0.65rem;color:var(--text-muted);margin-top:6px">Todas as 6 empresas</div>'
        '</div>'
        # Orcamentos
        '<div class="gx-card" style="background:#8b5cf60a;border-left:4px solid #8b5cf6">'
        f'<div style="display:flex;align-items:center;gap:6px;font-size:0.65rem;color:#6d28d9;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px">{icon("file-text",13,"#6d28d9")} Orcamentos</div>'
        f'<div style="font-size:1.9rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\';line-height:1">{_fmt(total_orc)}</div>'
        '<div style="font-size:0.65rem;color:var(--text-muted);margin-top:6px">Opps criadas no mes</div>'
        '</div>'
        # Vendas
        '<div class="gx-card" style="background:#10b9810a;border-left:4px solid #10b981">'
        f'<div style="display:flex;align-items:center;gap:6px;font-size:0.65rem;color:#047857;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px">{icon("target",13,"#047857")} Vendas</div>'
        f'<div style="font-size:1.9rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\';line-height:1">{_fmt(total_vendas)}</div>'
        f'<div style="font-size:0.65rem;color:var(--text-muted);margin-top:6px">Fechado Ganho · {_fv(total_valor)}</div>'
        '</div>'
        # Energia (Flex Energy)
        '<div class="gx-card" style="background:#EC85000a;border-left:4px solid #EC8500">'
        f'<div style="display:flex;align-items:center;gap:6px;font-size:0.65rem;color:#B45309;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px">{icon("scale",13,"#B45309")} Energia Vendida</div>'
        f'<div style="font-size:1.9rem;font-weight:800;color:var(--text);font-feature-settings:\'tnum\';line-height:1">{_fk(total_kwh)}</div>'
        '<div style="font-size:0.65rem;color:var(--text-muted);margin-top:6px">Flex Energy (kWh)</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================
    # RANKING TOP 3 EMPRESAS POR VENDAS NO MES
    # ========================================
    if not cur_g.empty:
        rank = cur_g.groupby('Empresa_Proprietaria__c').agg({'total':'sum','valor':'sum'}).sort_values('valor', ascending=False).head(3)
        if not rank.empty:
            medals = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇 🥈 🥉
            rows_html = ""
            for i, (emp, r) in enumerate(rank.iterrows()):
                cor = CORES.get(emp, {}).get("primaria", "#999")
                label = EMPRESA_LABELS.get(emp, emp)
                qtd = int(r['total']); val = float(r['valor'])
                rows_html += (
                    '<div style="display:flex;align-items:center;gap:14px;padding:11px 14px;background:var(--bg-card);border-radius:10px;'
                    'box-shadow:var(--shadow-sm);border-left:3px solid '+cor+';margin-bottom:7px">'
                    f'<div style="font-size:1.4rem">{medals[i]}</div>'
                    f'<div style="flex:1"><div style="font-weight:700;color:var(--text);font-size:0.92rem">{label}</div>'
                    f'<div style="font-size:0.7rem;color:var(--text-muted)">{qtd} vendas</div></div>'
                    f'<div style="font-weight:800;color:{cor};font-size:1.05rem;font-feature-settings:\'tnum\'">{_fv(val)}</div>'
                    '</div>'
                )
            st.markdown(
                '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
                f'{icon("chart",18,"var(--accent)")} TOP EMPRESAS NO MES</h3>'
                '<p class="gx-subtle">Ranking por valor de vendas em '+MESES_PT_FULL.get(m,'')+f' {a}</p>'
                f'{rows_html}',
                unsafe_allow_html=True,
            )
except Exception as e:
    st.warning(f"Indicadores indisponiveis no momento ({str(e)[:80]}). Acesse uma secao para ver detalhes.")

# ========================================
# CARDS DE NAVEGACAO
# ========================================
st.markdown(
    '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px;margin-top:28px">'
    f'{icon("list-checks",18,"var(--accent)")} ANALISES DISPONIVEIS</h3>'
    '<p class="gx-subtle">Escolha uma secao para aprofundar</p>',
    unsafe_allow_html=True,
)

NAV = [
    {
        "url": "./visao_geral",
        "icon_name": "chart",
        "color": "#10b981",
        "title": "Visao Geral",
        "desc": "Cards executivos por empresa: Vendido, Negociacao+Contrato, Pipeline. Combustiveis e evolucao mes a mes.",
        "tag": "Pagina principal",
    },
    {
        "url": "./oportunidades",
        "icon_name": "flame",
        "color": "#f97316",
        "title": "Oportunidades",
        "desc": "Pipeline detalhado por fase, ranking de vendedores e funil de conversao por empresa.",
        "tag": None,
    },
    {
        "url": "./vendas",
        "icon_name": "target",
        "color": "#3b82f6",
        "title": "Vendas",
        "desc": "Historico mensal por ano fiscal, comparativo dias uteis e volume vendido (R$ ou kWh).",
        "tag": None,
    },
    {
        "url": "./leads",
        "icon_name": "users",
        "color": "#8b5cf6",
        "title": "Leads",
        "desc": "Funil de conversao por status, origens, %F1 (criados+convertidos), evolucao por empresa.",
        "tag": None,
    },
]

cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px">'
for n in NAV:
    tag_html = (
        f'<span style="display:inline-block;padding:2px 8px;background:{n["color"]}22;color:{n["color"]};'
        f'border-radius:5px;font-size:0.6rem;font-weight:700;letter-spacing:0.4px;text-transform:uppercase;'
        f'margin-left:8px">{n["tag"]}</span>'
    ) if n["tag"] else ""
    cards_html += (
        f'<a href="{n["url"]}" target="_self" style="text-decoration:none;color:inherit">'
        '<div class="gx-card" style="cursor:pointer;transition:transform 0.15s ease, box-shadow 0.15s ease;'
        f'border-left:4px solid {n["color"]};display:flex;flex-direction:column;gap:10px;height:100%">'
        '<div style="display:flex;align-items:center;gap:10px">'
        f'<div style="width:38px;height:38px;border-radius:10px;background:{n["color"]}18;'
        f'display:flex;align-items:center;justify-content:center">{icon(n["icon_name"], 20, n["color"])}</div>'
        f'<div style="flex:1"><div style="font-weight:700;font-size:1.05rem;color:var(--text);letter-spacing:-0.2px">{n["title"]}{tag_html}</div></div>'
        '</div>'
        f'<div style="font-size:0.82rem;color:var(--text-secondary);line-height:1.4">{n["desc"]}</div>'
        f'<div style="margin-top:auto;color:{n["color"]};font-size:0.75rem;font-weight:700;letter-spacing:0.3px">Abrir secao &rarr;</div>'
        '</div>'
        '</a>'
    )
cards_html += '</div>'
st.markdown(cards_html, unsafe_allow_html=True)

# ========================================
# CALLOUT NOVO + RODAPE
# ========================================
st.markdown(
    '<div style="margin-top:28px;padding:14px 18px;background:#FEF3C7;border:1px solid #FDE68A;'
    'border-radius:10px;display:flex;align-items:center;gap:12px">'
    f'{icon("scale",20,"#B45309")}'
    '<div>'
    '<div style="font-weight:700;color:#B45309;font-size:0.88rem">Novo: Segmentacao de Licitacao</div>'
    '<div style="font-size:0.78rem;color:#92400E;margin-top:2px">Cards da Flex Locacoes agora mostram divisao Licitacao vs Outras Origens. '
    'Ticket medio de licitacao e ~26x maior - misturar distorce as metricas.</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div style="margin-top:18px;text-align:center;font-size:0.7rem;color:var(--text-muted)">'
    f'Atualizado em {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")} · '
    'Cache Salesforce: 5 minutos · GFlex Empresas'
    '</div>',
    unsafe_allow_html=True,
)
