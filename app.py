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
        get_opps_ganhas_mensal_por_empresa, get_energy_kwh_mensal,
        get_flex_tendas_licitacao_ganhas_mensal,
    )
    with st.spinner("Carregando ranking do mes..."):
        df_g = get_opps_ganhas_mensal_por_empresa()
        df_kwh = get_energy_kwh_mensal()
        df_lic = get_flex_tendas_licitacao_ganhas_mensal()

    # Mes atual e mes anterior
    m_a = m - 1 if m > 1 else 12
    a_a = a if m > 1 else a - 1
    du_anterior_total = dias_uteis_no_mes(a_a, m_a)

    cur_g = df_g[(df_g['ano']==a) & (df_g['mes']==m)] if not df_g.empty else df_g
    ant_g = df_g[(df_g['ano']==a_a) & (df_g['mes']==m_a)] if not df_g.empty else df_g
    cur_k = df_kwh[(df_kwh['ano']==a) & (df_kwh['mes']==m)] if not df_kwh.empty else df_kwh
    ant_k = df_kwh[(df_kwh['ano']==a_a) & (df_kwh['mes']==m_a)] if not df_kwh.empty else df_kwh
    energy_kwh_mes = float(cur_k['total_kwh'].sum()) if not cur_k.empty else 0
    energy_kwh_ant = float(ant_k['total_kwh'].sum()) if not ant_k.empty else 0

    # Licitacao Flex Tendas no mes atual (fica ESTATICA — nao projeta)
    cur_lic = df_lic[(df_lic['ano']==a) & (df_lic['mes']==m)] if not df_lic.empty else df_lic
    tendas_lic_qtd = int(cur_lic['total'].sum()) if not cur_lic.empty else 0
    tendas_lic_val = float(cur_lic['valor'].sum()) if not cur_lic.empty else 0

    # mapas mes anterior por empresa
    ant_qtd = {}; ant_val = {}
    if not ant_g.empty:
        for _, r in ant_g.iterrows():
            ant_qtd[r['Empresa_Proprietaria__c']] = int(r['total'])
            ant_val[r['Empresa_Proprietaria__c']] = float(r['valor'])

    # ========================================
    # RANKING DE TODAS EMPRESAS POR VENDAS NO MES + FORECAST
    # Forecast: rate atual (qtd/DU_decorrido) * DU_total_mes
    # Variacao: (projecao - mes_anterior) / mes_anterior
    # ========================================
    rank_data = []
    rank_g = cur_g.groupby('Empresa_Proprietaria__c').agg({'total':'sum','valor':'sum'}).reset_index() if not cur_g.empty else pd.DataFrame()
    cur_g_map = {r['Empresa_Proprietaria__c']: (int(r['total']), float(r['valor'])) for _, r in rank_g.iterrows()}

    for emp in EMPRESAS:
        is_energy = (emp == "Flex Energy")
        is_tendas = (emp == "Flex Tendas")
        qtd, val = cur_g_map.get(emp, (0, 0.0))
        volume_atual = energy_kwh_mes if is_energy else val
        volume_anterior = energy_kwh_ant if is_energy else ant_val.get(emp, 0.0)
        qtd_anterior = ant_qtd.get(emp, 0)

        # Forecast (so faz sentido se ja passou pelo menos 1 DU)
        forecast_note = ""
        if du_h > 0 and du_t > 0:
            if is_tendas:
                # Tendas: licitacao e ESTATICA (4 contratos enormes nao se prevem),
                # so "outras origens" sao multiplicadas pelo rate de DU
                out_qtd = max(0, qtd - tendas_lic_qtd)
                out_val = max(0, val - tendas_lic_val)
                # outras projetadas
                out_qtd_proj = (out_qtd / du_h) * du_t
                out_val_proj = (out_val / du_h) * du_t
                # somar com licitacao estatica
                forecast_qtd = round(tendas_lic_qtd + out_qtd_proj)
                forecast_vol = tendas_lic_val + out_val_proj
                forecast_note = "Licitação fixada · só Outras projetam"
            else:
                forecast_qtd = round((qtd / du_h) * du_t)
                forecast_vol = (volume_atual / du_h) * du_t
        else:
            forecast_qtd = qtd
            forecast_vol = volume_atual

        # Variacao da projecao vs total mes anterior
        var_vol_pct = ((forecast_vol - volume_anterior) / volume_anterior * 100) if volume_anterior > 0 else None

        rank_data.append({
            "empresa": emp, "qtd": qtd, "valor": val,
            "volume_atual": volume_atual,
            "volume_atual_fmt": _fk(energy_kwh_mes) if is_energy else _fv(val),
            "unidade": "kWh" if is_energy else "R$",
            "forecast_qtd": int(forecast_qtd),
            "forecast_vol": forecast_vol,
            "forecast_vol_fmt": _fk(forecast_vol) if is_energy else _fv(forecast_vol),
            "forecast_note": forecast_note,
            "qtd_anterior": qtd_anterior,
            "volume_anterior_fmt": _fk(volume_anterior) if is_energy else _fv(volume_anterior),
            "var_vol_pct": var_vol_pct,
            "is_energy": is_energy,
            "is_tendas": is_tendas,
        })

    # Ordena por qtd (universal); desempata por volume
    rank_data.sort(key=lambda x: (-x['qtd'], -x['volume_atual']))

    def _vbadge(p):
        if p is None: return '<span style="color:var(--text-muted);font-size:0.65rem">—</span>'
        pos = p > 0
        col = "#059669" if pos else "#dc2626"
        bg = "#10b98118" if pos else "#dc262618"
        arrow = "↑" if pos else "↓"
        sign = "+" if pos else ""
        return (
            f'<span style="display:inline-flex;align-items:center;gap:2px;padding:1px 6px;'
            f'border-radius:5px;background:{bg};color:{col};font-size:0.62rem;font-weight:700;'
            f'font-feature-settings:\'tnum\'">{arrow} {sign}{p:.0f}%</span>'
        )

    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    # Cor de destaque pro forecast — roxo (contrasta com a cor da empresa)
    FC_COLOR = "#7c3aed"  # purple-600
    FC_COLOR_BG = "#7c3aed10"
    rows_html = ""
    for i, r in enumerate(rank_data):
        cor = CORES.get(r['empresa'], {}).get("primaria", "#999")
        label = EMPRESA_LABELS.get(r['empresa'], r['empresa'])
        pos = medals[i] if i < 3 else f'<span style="color:var(--text-muted);font-weight:700;font-size:0.9rem">#{i+1}</span>'
        note_html = (
            f'<div style="font-size:0.55rem;color:#B45309;font-weight:700;margin-top:1px;'
            f'text-transform:uppercase;letter-spacing:0.4px">⚖ {r["forecast_note"]}</div>'
        ) if r["forecast_note"] else ""
        rows_html += (
            '<div style="background:var(--bg-card);border-radius:12px;box-shadow:var(--shadow-md);'
            f'border-left:4px solid {cor};margin-bottom:10px;overflow:hidden">'
            # Header: posicao + nome
            '<div style="display:flex;align-items:center;gap:14px;padding:12px 16px 8px 16px">'
            f'<div style="font-size:1.5rem;width:36px;text-align:center">{pos}</div>'
            f'<div style="flex:1"><div style="font-weight:700;color:var(--text);font-size:1rem;letter-spacing:-0.2px">{label}</div>'
            f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:1px">{r["qtd"]} vendas realizadas · unidade {r["unidade"]}</div></div>'
            '</div>'
            # Grid 2 colunas: REALIZADO | PROJETADO
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid var(--border)">'
            # REALIZADO
            f'<div style="padding:14px 16px;background:{cor}08;border-right:1px solid var(--border)">'
            f'<div style="font-size:0.6rem;color:{cor};text-transform:uppercase;font-weight:700;letter-spacing:0.6px;margin-bottom:6px;display:flex;align-items:center;gap:5px">'
            f'{icon("target",11,cor)} Realizado · {du_h}/{du_t} DU</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:{cor};line-height:1;font-feature-settings:\'tnum\';letter-spacing:-0.5px">{r["volume_atual_fmt"]}</div>'
            f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:5px">{r["qtd"]} vendas no mês</div>'
            '</div>'
            # PROJETADO (destaque diferente — cor roxa, fonte serif italica)
            f'<div style="padding:14px 16px;background:{FC_COLOR_BG};position:relative">'
            f'<div style="font-size:0.6rem;color:{FC_COLOR};text-transform:uppercase;font-weight:700;letter-spacing:0.6px;margin-bottom:6px;display:flex;align-items:center;gap:5px">'
            f'{icon("trending-up",11,FC_COLOR)} Projeção fim do mês</div>'
            f'<div style="font-size:1.5rem;font-weight:800;color:{FC_COLOR};line-height:1;font-feature-settings:\'tnum\';letter-spacing:-0.5px">{r["forecast_vol_fmt"]}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;margin-top:5px;flex-wrap:wrap">'
            f'<span style="font-size:0.7rem;color:var(--text-secondary);font-feature-settings:\'tnum\'">{r["forecast_qtd"]} vendas projetadas</span>'
            f'{_vbadge(r["var_vol_pct"])}'
            '</div>'
            f'{note_html}'
            '</div>'
            '</div>'
            # Footer: comparativo mes anterior
            f'<div style="padding:7px 16px;background:var(--bg-overlay);border-top:1px solid var(--border);'
            f'font-size:0.62rem;color:var(--text-muted);text-align:right">'
            f'{MESES_PT_FULL.get(m_a,"")} (real): {r["qtd_anterior"]} vendas · {r["volume_anterior_fmt"]}'
            '</div>'
            '</div>'
        )

    st.markdown(
        '<h3 class="gx-h3" style="display:flex;align-items:center;gap:8px">'
        f'{icon("chart",18,"var(--accent)")} RANKING + FORECAST DO MES</h3>'
        f'<p class="gx-subtle">Ordenado por <b>vendas em {MESES_PT_FULL.get(m,"")} {a}</b> ({du_h}/{du_t} DU) · Projeção pro fim do mês baseada no rate atual · Flex Energy em kWh</p>'
        f'{rows_html}',
        unsafe_allow_html=True,
    )
except Exception as e:
    st.warning(f"Ranking indisponivel no momento ({str(e)[:80]}). Acesse uma secao para ver detalhes.")

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
