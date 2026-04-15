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
