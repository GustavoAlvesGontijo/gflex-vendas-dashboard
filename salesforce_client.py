"""
Cliente Salesforce para o dashboard GFlex.
Conexao via simple_salesforce + queries SOQL com cache Streamlit.
"""
import pandas as pd
import requests
import streamlit as st
from simple_salesforce import Salesforce
from datetime import date
from config import (
    SF_CLIENT_ID, SF_CLIENT_SECRET, SF_REFRESH_TOKEN,
    SF_INSTANCE_URL, SF_DOMAIN,
    CAMPOS_LEAD_ESPECIFICOS, CAMPOS_OPP_ESPECIFICOS, CACHE_TTL_SECONDS,
)


import time as _time

def _get_secret(key: str, fallback: str = "") -> str:
    """Busca credencial: primeiro st.secrets (Cloud), depois config.py (.env local)."""
    try:
        return st.secrets["salesforce"][key]
    except Exception:
        return fallback


# Conexao SF com renovacao automatica de token
_sf_connection = None
_sf_token_time = 0
_SF_TOKEN_TTL = 5400  # 90 minutos (token dura ~2h, renovamos antes)


def _create_sf_connection() -> Salesforce:
    """Cria nova conexao SF com token fresco."""
    client_id = _get_secret("SF_CLIENT_ID", SF_CLIENT_ID)
    client_secret = _get_secret("SF_CLIENT_SECRET", SF_CLIENT_SECRET)
    refresh_token = _get_secret("SF_REFRESH_TOKEN", SF_REFRESH_TOKEN)
    domain = _get_secret("SF_DOMAIN", SF_DOMAIN)
    instance = _get_secret("SF_INSTANCE_URL", SF_INSTANCE_URL)

    token_url = f"https://{domain}.salesforce.com/services/oauth2/token"
    resp = requests.post(token_url, data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }, verify=False)
    resp.raise_for_status()
    token_data = resp.json()
    access_token = token_data["access_token"]
    instance_url = token_data.get("instance_url", instance)

    session = requests.Session()
    session.verify = False

    return Salesforce(
        instance_url=instance_url,
        session_id=access_token,
        session=session,
    )


def get_sf_connection() -> Salesforce:
    """Retorna conexao SF, renovando o token se expirou."""
    global _sf_connection, _sf_token_time
    now = _time.time()
    if _sf_connection is None or (now - _sf_token_time) > _SF_TOKEN_TTL:
        _sf_connection = _create_sf_connection()
        _sf_token_time = now
    return _sf_connection


def _reset_sf_connection():
    """Forca renovacao do token na proxima chamada."""
    global _sf_connection, _sf_token_time
    _sf_connection = None
    _sf_token_time = 0


def _query_to_df(soql: str) -> pd.DataFrame:
    """Executa SOQL e retorna DataFrame. Renova token se sessao expirou."""
    try:
        sf = get_sf_connection()
        result = sf.query_all(soql)
    except Exception as e:
        if "INVALID_SESSION_ID" in str(e) or "Session expired" in str(e):
            _reset_sf_connection()
            sf = get_sf_connection()
            result = sf.query_all(soql)
        else:
            raise
    records = result.get("records", [])
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "attributes" in df.columns:
        df = df.drop(columns=["attributes"])
    # Flatten nested dicts (ex: Owner.Name)
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, dict)).any():
            nested = pd.json_normalize(df[col])
            nested.columns = [f"{col}.{c}" for c in nested.columns]
            if f"{col}.attributes" in nested.columns:
                nested = nested.drop(columns=[f"{col}.attributes"])
            df = df.drop(columns=[col]).join(nested)
    return df


def _format_date(d: date) -> str:
    return d.strftime("%Y-%m-%dT00:00:00Z")


# ============================================================
# LEADS
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_por_empresa() -> pd.DataFrame:
    """Contagem de leads agrupados por Empresa Proprietaria."""
    soql = """
        SELECT Empresa_Proprietaria__c, COUNT(Id) total
        FROM Lead
        GROUP BY Empresa_Proprietaria__c
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_por_status(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads agrupados por status, com filtros opcionais."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Status, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY Status
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_por_origem(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads agrupados por LeadSource."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT LeadSource, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY LeadSource
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_por_rating(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads agrupados por Rating (temperatura)."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Rating, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY Rating
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_motivo_descarte(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Top motivos de descarte de leads."""
    where = ["Status = 'Fechado Nao Convertido'", "Motivo_do_Descarte__c != null"]
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    soql = f"""
        SELECT Motivo_do_Descarte__c, COUNT(Id) total
        FROM Lead
        WHERE {' AND '.join(where)}
        GROUP BY Motivo_do_Descarte__c
        ORDER BY COUNT(Id) DESC
        LIMIT 15
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_conversao_por_empresa(data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads totais e convertidos por empresa (para taxa de conversao)."""
    where = []
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Empresa_Proprietaria__c, IsConverted, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY Empresa_Proprietaria__c, IsConverted
    """
    return _query_to_df(soql)


# ============================================================
# LEADS — MENSAL (para Visao Geral mes a mes)
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_mensal_por_empresa() -> pd.DataFrame:
    """Leads criados por empresa+mes, com contagem de convertidos."""
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               IsConverted, COUNT(Id) total
        FROM Lead
        WHERE CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate), IsConverted
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_convertidos_no_mes_por_empresa() -> pd.DataFrame:
    """Leads convertidos por empresa+mes da CONVERSAO (ConvertedDate).
    Diferente de get_leads_mensal que usa CreatedDate.
    Aqui pegamos: quantos leads foram convertidos naquele mes, independente de quando foram criados.
    """
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(ConvertedDate) mes, CALENDAR_YEAR(ConvertedDate) ano,
               COUNT(Id) total
        FROM Lead
        WHERE IsConverted = true AND ConvertedDate >= 2025-01-01
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(ConvertedDate), CALENDAR_YEAR(ConvertedDate)
        ORDER BY CALENDAR_YEAR(ConvertedDate), CALENDAR_MONTH(ConvertedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_contas_mensal_por_empresa() -> pd.DataFrame:
    """Contas criadas por empresa+mes.
    ATENCAO: Na Account o campo esta escrito 'Empresa_Proprieteria__c' (typo no SF).
    """
    soql = """
        SELECT Empresa_Proprieteria__c,
               CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               COUNT(Id) total
        FROM Account
        WHERE CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY Empresa_Proprieteria__c, CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    df = _query_to_df(soql)
    # Normalizar nome do campo para manter consistencia
    if "Empresa_Proprieteria__c" in df.columns:
        df = df.rename(columns={"Empresa_Proprieteria__c": "Empresa_Proprietaria__c"})
    return df


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_mensal_por_empresa() -> pd.DataFrame:
    """Oportunidades criadas por empresa+mes com valor."""
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_ganhas_mensal_por_empresa() -> pd.DataFrame:
    """Oportunidades ganhas por empresa+mes com valor."""
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(CloseDate) mes, CALENDAR_YEAR(CloseDate) ano,
               COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE StageName = 'Fechado Ganho' AND CloseDate >= 2025-01-01
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(CloseDate), CALENDAR_YEAR(CloseDate)
        ORDER BY CALENDAR_YEAR(CloseDate), CALENDAR_MONTH(CloseDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_energy_kwh_mensal() -> pd.DataFrame:
    """kWh vendidos pela Flex Energy por mes (via OpportunityLineItem.Quantity).
    Produto unico da Energy: Quilowatt Hora/Mes.
    """
    soql = """
        SELECT CALENDAR_MONTH(Opportunity.CloseDate) mes,
               CALENDAR_YEAR(Opportunity.CloseDate) ano,
               SUM(Quantity) total_kwh
        FROM OpportunityLineItem
        WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
        AND Opportunity.StageName = 'Fechado Ganho'
        AND Opportunity.CloseDate >= 2025-01-01
        GROUP BY CALENDAR_MONTH(Opportunity.CloseDate), CALENDAR_YEAR(Opportunity.CloseDate)
        ORDER BY CALENDAR_YEAR(Opportunity.CloseDate), CALENDAR_MONTH(Opportunity.CloseDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_energy_kwh_orcado_mensal() -> pd.DataFrame:
    """kWh orcado pela Flex Energy por mes (TODAS as opps criadas, nao so ganhas).
    Usa CreatedDate da Opportunity (quando o orcamento foi feito).
    """
    soql = """
        SELECT CALENDAR_MONTH(Opportunity.CreatedDate) mes,
               CALENDAR_YEAR(Opportunity.CreatedDate) ano,
               SUM(Quantity) total_kwh
        FROM OpportunityLineItem
        WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
        AND Opportunity.CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY CALENDAR_MONTH(Opportunity.CreatedDate), CALENDAR_YEAR(Opportunity.CreatedDate)
        ORDER BY CALENDAR_YEAR(Opportunity.CreatedDate), CALENDAR_MONTH(Opportunity.CreatedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_origem_mensal_por_empresa() -> pd.DataFrame:
    """Leads por empresa+origem+mes."""
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               LeadSource, COUNT(Id) total
        FROM Lead
        WHERE CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate), LeadSource
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_os_mensal_por_empresa() -> pd.DataFrame:
    """OS criadas por empresa+mes."""
    soql = """
        SELECT Empresa_Proprietaria__c,
               CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               COUNT(Id) total
        FROM Ordem_de_Servico__c
        WHERE CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY Empresa_Proprietaria__c, CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


# ============================================================
# LICITACAO — slice especial Flex Tendas (LeadSource='Licitacao')
# Ticket medio ~26x maior que demais origens — exige segmentacao.
# Doc: _Brain/Empresa/Flex Locacoes - Negocio Completo.md
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_flex_tendas_licitacao_opps_mensal() -> pd.DataFrame:
    """Opps Flex Tendas com LeadSource='Licitacao' por mes (CreatedDate)."""
    soql = """
        SELECT CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE Empresa_Proprietaria__c = 'Flex Tendas'
        AND LeadSource = 'Licitacao'
        AND CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_flex_tendas_licitacao_ganhas_mensal() -> pd.DataFrame:
    """Opps Flex Tendas Licitacao ganhas por mes (CloseDate)."""
    soql = """
        SELECT CALENDAR_MONTH(CloseDate) mes, CALENDAR_YEAR(CloseDate) ano,
               COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE Empresa_Proprietaria__c = 'Flex Tendas'
        AND LeadSource = 'Licitacao'
        AND StageName = 'Fechado Ganho'
        AND CloseDate >= 2025-01-01
        GROUP BY CALENDAR_MONTH(CloseDate), CALENDAR_YEAR(CloseDate)
        ORDER BY CALENDAR_YEAR(CloseDate), CALENDAR_MONTH(CloseDate)
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_flex_tendas_licitacao_pipeline() -> pd.DataFrame:
    """Pipeline aberto Flex Tendas Licitacao por fase."""
    soql = """
        SELECT StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE Empresa_Proprietaria__c = 'Flex Tendas'
        AND LeadSource = 'Licitacao'
        AND StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')
        GROUP BY StageName
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_flex_tendas_licitacao_leads_mensal() -> pd.DataFrame:
    """Leads Flex Tendas com LeadSource='Licitacao' por mes."""
    soql = """
        SELECT CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano,
               COUNT(Id) total
        FROM Lead
        WHERE Empresa_Proprietaria__c = 'Flex Tendas'
        AND LeadSource = 'Licitacao'
        AND CreatedDate >= 2025-01-01T00:00:00Z
        GROUP BY CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


# ============================================================
# PIPELINE ABERTO (opps em negociacao/contrato)
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_pipeline_aberto_por_empresa() -> pd.DataFrame:
    """Pipeline aberto por empresa e fase (todas as fases exceto Fechado).
    Exclui usuario Pos Venda GFlex do pipeline da Energy.
    """
    soql = """
        SELECT Empresa_Proprietaria__c, StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')
        AND Owner.Name != 'Pos Venda GFlex'
        GROUP BY Empresa_Proprietaria__c, StageName
        ORDER BY Empresa_Proprietaria__c
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_energy_pipeline_kwh() -> dict:
    """kWh do pipeline da Energy por fase (via OpportunityLineItem).
    Exclui pos-venda.
    """
    soql = """
        SELECT Opportunity.StageName fase, SUM(Quantity) total_kwh
        FROM OpportunityLineItem
        WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
        AND Opportunity.StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')
        AND Opportunity.Owner.Name != 'Pos Venda GFlex'
        GROUP BY Opportunity.StageName
    """
    df = _query_to_df(soql)
    result = {}
    if not df.empty:
        for _, r in df.iterrows():
            result[r["fase"]] = float(r["total_kwh"]) if r["total_kwh"] else 0
    return result


# ============================================================
# PERFORMANCE POR ORIGEM (Ads/Combustiveis)
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_origens_funil_por_empresa(data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads por empresa+origem com status de conversao (para funil origem->opp->venda)."""
    where = []
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Empresa_Proprietaria__c, LeadSource, IsConverted, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY Empresa_Proprietaria__c, LeadSource, IsConverted
        ORDER BY Empresa_Proprietaria__c, COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_por_origem_empresa(data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Oportunidades por empresa+origem+fase (para saber quantas orcaram e venderam por origem)."""
    where = []
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Empresa_Proprietaria__c, LeadSource, StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        {where_clause}
        GROUP BY Empresa_Proprietaria__c, LeadSource, StageName
        ORDER BY Empresa_Proprietaria__c, COUNT(Id) DESC
    """
    return _query_to_df(soql)


# ============================================================
# OPORTUNIDADES
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_por_empresa_fase() -> pd.DataFrame:
    """Oportunidades agrupadas por empresa e fase."""
    soql = """
        SELECT Empresa_Proprietaria__c, StageName, COUNT(Id) total
        FROM Opportunity
        GROUP BY Empresa_Proprietaria__c, StageName
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_pipeline(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Oportunidades por fase com filtros."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        {where_clause}
        GROUP BY StageName
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_motivo_perda(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Motivos de perda de oportunidades."""
    where = ["StageName = 'Fechado Perdido'", "Motivo_da_Perda__c != null"]
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    soql = f"""
        SELECT Motivo_da_Perda__c, COUNT(Id) total
        FROM Opportunity
        WHERE {' AND '.join(where)}
        GROUP BY Motivo_da_Perda__c
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_win_rate_por_empresa(data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Win rate por empresa (Fechado Ganho vs Fechado Perdido)."""
    where = ["(StageName = 'Fechado Ganho' OR StageName = 'Fechado Perdido')"]
    if data_inicio:
        where.append(f"CloseDate >= {_format_date(data_inicio).replace('T00:00:00Z', '')}")
    if data_fim:
        where.append(f"CloseDate <= {_format_date(data_fim).replace('T00:00:00Z', '')}")
    soql = f"""
        SELECT Empresa_Proprietaria__c, StageName, COUNT(Id) total
        FROM Opportunity
        WHERE {' AND '.join(where)}
        GROUP BY Empresa_Proprietaria__c, StageName
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_por_vendedor(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Oportunidades agrupadas por vendedor e fase."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Owner.Name, StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        {where_clause}
        GROUP BY Owner.Name, StageName
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_engajamento(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Distribuicao de engajamento comercial."""
    where = ["StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')"]
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    soql = f"""
        SELECT Engajamento_Comercial__c, COUNT(Id) total
        FROM Opportunity
        WHERE {' AND '.join(where)}
        GROUP BY Engajamento_Comercial__c
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_tendencia(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Oportunidades criadas por mes (tendencia)."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT CALENDAR_MONTH(CreatedDate) mes, CALENDAR_YEAR(CreatedDate) ano, COUNT(Id) total
        FROM Opportunity
        {where_clause}
        GROUP BY CALENDAR_MONTH(CreatedDate), CALENDAR_YEAR(CreatedDate)
        ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
    """
    return _query_to_df(soql)


# ============================================================
# ORDENS DE SERVICO
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_os_por_empresa() -> pd.DataFrame:
    """OS agrupadas por empresa e status."""
    soql = """
        SELECT Empresa_Proprietaria__c, Status__c, COUNT(Id) total
        FROM Ordem_de_Servico__c
        GROUP BY Empresa_Proprietaria__c, Status__c
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_os_resultado_expedicao(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Resultado da expedicao (prazo)."""
    where = ["Resultado_da_Expedicao__c != null"]
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"Data_de_Criacao__c >= {_format_date(data_inicio).replace('T00:00:00Z', '')}")
    if data_fim:
        where.append(f"Data_de_Criacao__c <= {_format_date(data_fim).replace('T00:00:00Z', '')}")
    soql = f"""
        SELECT Resultado_da_Expedicao__c, COUNT(Id) total
        FROM Ordem_de_Servico__c
        WHERE {' AND '.join(where)}
        GROUP BY Resultado_da_Expedicao__c
    """
    return _query_to_df(soql)


# ============================================================
# PAGAMENTOS (GF2 + Tendas)
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_pagamentos_status(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Pagamentos por status e empresa."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"Data_de_Vencimento__c >= {_format_date(data_inicio).replace('T00:00:00Z', '')}")
    if data_fim:
        where.append(f"Data_de_Vencimento__c <= {_format_date(data_fim).replace('T00:00:00Z', '')}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Empresa_Proprietaria__c, Status__c, COUNT(Id) total, SUM(Valor_da_Parcela__c) valor
        FROM Pagamento__c
        {where_clause}
        GROUP BY Empresa_Proprietaria__c, Status__c
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_pagamentos_forma(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Pagamentos por forma de pagamento."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"Data_de_Vencimento__c >= {_format_date(data_inicio).replace('T00:00:00Z', '')}")
    if data_fim:
        where.append(f"Data_de_Vencimento__c <= {_format_date(data_fim).replace('T00:00:00Z', '')}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Forma_de_Pagamento__c, COUNT(Id) total, SUM(Valor_da_Parcela__c) valor
        FROM Pagamento__c
        {where_clause}
        GROUP BY Forma_de_Pagamento__c
        ORDER BY SUM(Valor_da_Parcela__c) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_pagamentos_mes_atual() -> pd.DataFrame:
    """Pagamentos com vencimento no mes atual."""
    soql = """
        SELECT Empresa_Proprietaria__c, Status__c, COUNT(Id) total, SUM(Valor_da_Parcela__c) valor
        FROM Pagamento__c
        WHERE Vencimento_Mes_Atual__c = true
        GROUP BY Empresa_Proprietaria__c, Status__c
    """
    return _query_to_df(soql)


# ============================================================
# VENDEDORES
# ============================================================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_ranking_vendedores(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Ranking de vendedores por oportunidades ganhas."""
    where = ["StageName = 'Fechado Ganho'"]
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CloseDate >= {_format_date(data_inicio).replace('T00:00:00Z', '')}")
    if data_fim:
        where.append(f"CloseDate <= {_format_date(data_fim).replace('T00:00:00Z', '')}")
    soql = f"""
        SELECT Owner.Name, Empresa_Proprietaria__c, COUNT(Id) ganhas, SUM(Amount) valor
        FROM Opportunity
        WHERE {' AND '.join(where)}
        GROUP BY Owner.Name, Empresa_Proprietaria__c
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_por_proprietario(empresa: str = None, data_inicio: date = None, data_fim: date = None) -> pd.DataFrame:
    """Leads por proprietario (atribuicao)."""
    where = []
    if empresa and empresa != "Todas":
        where.append(f"Empresa_Proprietaria__c = '{empresa}'")
    if data_inicio:
        where.append(f"CreatedDate >= {_format_date(data_inicio)}")
    if data_fim:
        where.append(f"CreatedDate <= {_format_date(data_fim)}")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    soql = f"""
        SELECT Owner.Name, Status, COUNT(Id) total
        FROM Lead
        {where_clause}
        GROUP BY Owner.Name, Status
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


# ============================================================
# FECHAMENTO SEMANAL — queries bound to arbitrary date ranges
# Doc: _Brain/Processos/Flex Energy - Fechamento Semanal Comercial.md
# ============================================================

def _date_only(d: date) -> str:
    """Formata data como YYYY-MM-DD (sem timezone) — para campos Date do SF."""
    return d.strftime("%Y-%m-%d")


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Contagem total de leads criados no periodo (com IsConverted para conta de convertidos)."""
    soql = f"""
        SELECT IsConverted, COUNT(Id) total
        FROM Lead
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        GROUP BY IsConverted
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_origem_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Leads por origem (LeadSource) no periodo."""
    soql = f"""
        SELECT LeadSource, COUNT(Id) total
        FROM Lead
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        GROUP BY LeadSource
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_status_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Leads por Status no periodo (snapshot de quem foi criado e onde esta hoje)."""
    soql = f"""
        SELECT Status, COUNT(Id) total
        FROM Lead
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        GROUP BY Status
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_leads_vendedor_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Leads por proprietario com IsConverted no periodo (para tabela de vendedores).
    Usa alias 'vendedor' porque SF aggregate queries achatam Owner.Name de forma inconsistente.
    """
    soql = f"""
        SELECT Owner.Name vendedor, Status, IsConverted, COUNT(Id) total
        FROM Lead
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        GROUP BY Owner.Name, Status, IsConverted
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_energy_consumo_declarado_periodo(data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Flex Energy: consumo declarado em kWh dos leads criados no periodo, por Owner."""
    soql = f"""
        SELECT Owner.Name vendedor, COUNT(Id) total_leads, SUM(Consumo_Declarado_kW__c) total_kwh
        FROM Lead
        WHERE Empresa_Proprietaria__c = 'Flex Energy'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        AND Consumo_Declarado_kW__c != null
        GROUP BY Owner.Name
        ORDER BY SUM(Consumo_Declarado_kW__c) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_accounts_criadas_periodo(empresa: str, data_inicio: date, data_fim: date) -> int:
    """Contas Account criadas no periodo. ATENCAO: campo na Account eh 'Empresa_Proprieteria__c' (typo)."""
    soql = f"""
        SELECT COUNT(Id) total
        FROM Account
        WHERE Empresa_Proprieteria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
    """
    df = _query_to_df(soql)
    if df.empty:
        return 0
    return int(df["total"].iloc[0]) if "total" in df.columns else 0


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_criadas_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Oportunidades criadas no periodo - por Owner e fase predominante."""
    soql = f"""
        SELECT Owner.Name vendedor, StageName, COUNT(Id) total, SUM(Amount) valor
        FROM Opportunity
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND CreatedDate >= {_format_date(data_inicio)}
        AND CreatedDate <= {_format_date(data_fim)}
        AND Owner.Name != 'Pos Venda GFlex'
        GROUP BY Owner.Name, StageName
        ORDER BY COUNT(Id) DESC
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_opps_ganhas_periodo(empresa: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Vendas (Fechado Ganho) no periodo - lista detalhada."""
    soql = f"""
        SELECT Id, Name, Owner.Name, Account.Name, Amount, CloseDate, Tipo_de_Conta_ENERGY__c
        FROM Opportunity
        WHERE Empresa_Proprietaria__c = '{empresa}'
        AND StageName = 'Fechado Ganho'
        AND CloseDate >= {_date_only(data_inicio)}
        AND CloseDate <= {_date_only(data_fim)}
        AND Owner.Name != 'Pos Venda GFlex'
        ORDER BY CloseDate DESC
        LIMIT 500
    """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_energy_kwh_periodo(data_inicio: date, data_fim: date, ganhas: bool = False) -> dict:
    """Flex Energy: soma kWh do periodo. Se ganhas=True, filtra Fechado Ganho com CloseDate; senao Opps criadas no periodo (orcado)."""
    if ganhas:
        soql = f"""
            SELECT SUM(Quantity) total_kwh, COUNT(Id) total_opps
            FROM OpportunityLineItem
            WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
            AND Opportunity.StageName = 'Fechado Ganho'
            AND Opportunity.CloseDate >= {_date_only(data_inicio)}
            AND Opportunity.CloseDate <= {_date_only(data_fim)}
        """
    else:
        soql = f"""
            SELECT SUM(Quantity) total_kwh, COUNT(Id) total_opps
            FROM OpportunityLineItem
            WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
            AND Opportunity.CreatedDate >= {_format_date(data_inicio)}
            AND Opportunity.CreatedDate <= {_format_date(data_fim)}
        """
    df = _query_to_df(soql)
    if df.empty:
        return {"kwh": 0.0, "opps": 0}
    kwh = float(df["total_kwh"].iloc[0]) if df["total_kwh"].iloc[0] else 0.0
    opps = int(df["total_opps"].iloc[0]) if df["total_opps"].iloc[0] else 0
    return {"kwh": kwh, "opps": opps}


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_pipeline_termometro(empresa: str) -> pd.DataFrame:
    """Pipeline em aberto por StageName + Temperatura (exclui pos-venda).
    Volume em kWh para Energy (via OpportunityLineItem), Amount para demais.
    """
    if empresa == "Flex Energy":
        soql = """
            SELECT Opportunity.StageName fase,
                   Opportunity.Temperatura_da_Oportunidade_Energy__c temp,
                   COUNT_DISTINCT(Opportunity.Id) total,
                   SUM(Quantity) volume_kwh
            FROM OpportunityLineItem
            WHERE Opportunity.Empresa_Proprietaria__c = 'Flex Energy'
            AND Opportunity.StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')
            AND Opportunity.Owner.Name != 'Pos Venda GFlex'
            GROUP BY Opportunity.StageName, Opportunity.Temperatura_da_Oportunidade_Energy__c
        """
    else:
        soql = f"""
            SELECT StageName fase, COUNT(Id) total, SUM(Amount) volume_rs
            FROM Opportunity
            WHERE Empresa_Proprietaria__c = '{empresa}'
            AND StageName NOT IN ('Fechado Ganho', 'Fechado Perdido')
            AND Owner.Name != 'Pos Venda GFlex'
            GROUP BY StageName
        """
    return _query_to_df(soql)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_qualidade_contas_energy(data_inicio: date = None, data_fim: date = None) -> dict:
    """Snapshot de qualidade do cadastro de Account (Flex Energy).
    Retorna dict com counts conformes/inconformes por criterio.
    """
    where_extra = ""
    if data_inicio and data_fim:
        where_extra = f"AND CreatedDate >= {_format_date(data_inicio)} AND CreatedDate <= {_format_date(data_fim)}"
    soql_total = f"""
        SELECT COUNT(Id) total
        FROM Account
        WHERE Empresa_Proprieteria__c = 'Flex Energy' {where_extra}
    """
    soql_cnpj = f"""
        SELECT COUNT(Id) total
        FROM Account
        WHERE Empresa_Proprieteria__c = 'Flex Energy' {where_extra}
        AND Name != null
    """
    soql_setor = f"""
        SELECT COUNT(Id) total
        FROM Account
        WHERE Empresa_Proprieteria__c = 'Flex Energy' {where_extra}
        AND Setor__c != null
    """
    soql_endereco = f"""
        SELECT COUNT(Id) total
        FROM Account
        WHERE Empresa_Proprieteria__c = 'Flex Energy' {where_extra}
        AND BillingCity != null AND BillingStreet != null
    """
    def _val(soql):
        df = _query_to_df(soql)
        if df.empty:
            return 0
        return int(df["total"].iloc[0]) if "total" in df.columns and df["total"].iloc[0] else 0
    total = _val(soql_total)
    return {
        "total": total,
        "razao_social_ok": _val(soql_cnpj),
        "setor_ok": _val(soql_setor),
        "endereco_ok": _val(soql_endereco),
    }
