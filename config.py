"""
Configuracao central do dashboard GFlex.
Cores, constantes, credenciais e mapeamentos.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Salesforce (OAuth via Connected App) ---
SF_CLIENT_ID = os.getenv("SF_CLIENT_ID", "")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET", "")
SF_REFRESH_TOKEN = os.getenv("SF_REFRESH_TOKEN", "")
SF_INSTANCE_URL = os.getenv("SF_INSTANCE_URL", "https://gflex-empresas.my.salesforce.com")
SF_DOMAIN = os.getenv("SF_DOMAIN", "login")

# --- Empresas ---
EMPRESAS = [
    "Flex Energy",
    "GF2 Solu\u00e7\u00f5es Integradas",
    "Flex Tendas",
    "Flex Medi\u00e7\u00f5es",
    "MEC Estruturas Met\u00e1licas",
    "Flex Solar",
]

EMPRESA_LABELS = {
    "Flex Energy": "Flex Energy",
    "GF2 Solu\u00e7\u00f5es Integradas": "GF2 Solucoes",
    "Flex Tendas": "Flex Locacoes (Tendas)",
    "Flex Medi\u00e7\u00f5es": "Flex Medi\u00e7\u00f5es",
    "MEC Estruturas Met\u00e1licas": "MEC Estruturas",
    "Flex Solar": "Flex Solar",
}

# Mapeamento empresa -> arquivo de logo
EMPRESA_LOGOS = {
    "Flex Energy": "flex_energy.png",
    "GF2 Solu\u00e7\u00f5es Integradas": "gf2.png",
    "Flex Tendas": "flex_tendas.png",
    "Flex Medi\u00e7\u00f5es": "flex_medicoes.png",
    "MEC Estruturas Met\u00e1licas": "mec.png",
    "Flex Solar": "flex_solar.png",
}

import base64 as _b64
from pathlib import Path as _Path

_logo_cache = {}

def get_logo_b64(empresa: str) -> str:
    """Retorna a logo da empresa como string base64 (para usar em <img src=...> HTML)."""
    if empresa in _logo_cache:
        return _logo_cache[empresa]
    fname = EMPRESA_LOGOS.get(empresa)
    if not fname:
        return ""
    path = _Path(__file__).parent / "assets" / "logos" / fname
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        b64 = _b64.b64encode(f.read()).decode("ascii")
    result = f"data:image/png;base64,{b64}"
    _logo_cache[empresa] = result
    return result

# --- Cores por empresa (manual da marca) ---
CORES = {
    "GFlex": {"primaria": "#1a1a2e", "secundaria": "#EC8500", "fundo": "#f5f5f5"},
    "Flex Energy": {"primaria": "#EC8500", "secundaria": "#F7C42D", "fundo": "#f5f5f5"},
    "GF2 Solu\u00e7\u00f5es Integradas": {"primaria": "#004A9D", "secundaria": "#ffffff", "fundo": "#ffffff"},
    "Flex Tendas": {"primaria": "#3f469c", "secundaria": "#ffffff", "fundo": "#ffffff"},
    "Flex Medi\u00e7\u00f5es": {"primaria": "#517e45", "secundaria": "#ffffff", "fundo": "#ffffff"},
    "MEC Estruturas Met\u00e1licas": {"primaria": "#151515", "secundaria": "#555555", "fundo": "#ffffff"},
    "Flex Solar": {"primaria": "#FF8728", "secundaria": "#f1f3f4", "fundo": "#f1f3f4"},
}

# Lista de cores primarias na ordem das empresas (para graficos)
CORES_EMPRESAS_LISTA = [
    CORES[e]["primaria"] for e in EMPRESAS
]

# --- Fases de Oportunidades (pipeline padrao) ---
FASES_PIPELINE = [
    "Novo",
    "Em An\u00e1lise",
    "Contato Ativo",
    "Contato Passivo",
    "Negocia\u00e7\u00e3o",
    "Contrato",
    "Em Cota\u00e7\u00e3o",
    "Fechado Ganho",
    "Fechado Perdido",
]

# --- Status de Leads ---
STATUS_LEADS = [
    "Aberto",
    "Em Contato",
    "Em Interacao",
    "Transferencia Vendedor",
    "Objecao Comercial",
    "Aceite",
    "Recuperacao",
    "Stand-by Retrabalho",
    "Item Updated",
    "Transferencia Troca",
    "Fechado Convertido",
    "Fechado Nao Convertido",
]

# --- Origens de Leads ---
ORIGENS_LEADS = [
    "Exact Sales",
    "Website",
    "Meta ADS",
    "Feira",
    "Instagram",
    "Google Ads",
    "Prospeccao Ativa",
    "Indicacao",
    "Tabela",
]

# --- Status de OS por empresa ---
STATUS_OS = {
    "Flex Energy": ["Aberta", "Assinado", "Validado", "Aguardando Aprovacao", "Cancelada"],
    "GF2 Solu\u00e7\u00f5es Integradas": ["Aguardando Aprovacao", "Aberta", "Em Producao", "Em Separacao", "Em Rota de Entrega", "Entregue com Pendencia", "Entregue", "Validado", "Cancelada"],
    "Flex Tendas": ["Aguardando Aprovacao", "Aberta", "Em Producao", "Em Montagem", "Cancelada"],
    "Flex Medi\u00e7\u00f5es": ["Aguardando Aprovacao"],
    "Flex Solar": ["Aberta", "Em Compras", "Em Instalacao", "Finalizada"],
    "MEC Estruturas Met\u00e1licas": [],
}

# --- Status de Pagamento ---
STATUS_PAGAMENTO = ["Em aberto", "Atrasado", "Inadimplente", "Pago", "Cancelado"]

# --- Engajamento Comercial (niveis por empresa) ---
ENGAJAMENTO_CONFIG = {
    "Flex Energy": {"campo": "Engajamento_Comercial__c", "dias": [3, 7, 15, 30, 45]},
    "GF2 Solu\u00e7\u00f5es Integradas": {"campo": "Engajamento_Comercial__c", "dias": [7, 15, 30, 45, 60]},
    "MEC Estruturas Met\u00e1licas": {"campo": "Engajamento_Comercial__c", "dias": [7, 15, 30, 45, 60]},
    "Flex Tendas": {"campo": "Engajamento_Comercial__c", "dias": [2, 5, 12, 20, 30]},
    "Flex Medi\u00e7\u00f5es": {"campo": "Engajamento_Comercial__c", "dias": [2, 5, 12, 20, 30]},
    "Flex Solar": {"campo": "Engajamento_Comercial__c", "dias": [7, 15, 30, 45, 60]},
}

# --- Motivos de Perda (Oportunidades) ---
MOTIVOS_PERDA_OPP = [
    "Abandono",
    "Cliente final nao fechou",
    "Concessionaria de Energia",
    "Fator Externo",
    "Fechou com concorrente",
    "Prazo de entrega nao atendeu",
    "Produto fora do catalogo",
    "Produto indisponivel",
]

# --- Campos especificos por empresa (para queries dinamicas) ---
CAMPOS_LEAD_ESPECIFICOS = {
    "Flex Energy": [
        "Consumo_Declarado_kW__c",
        "Fatura_Concessionaria__c",
        "concessionaria_energia__c",
        "Padrao_Negocio__c",
        "Fatura_Referencia__c",
    ],
    "Flex Tendas": [
        "Qual_estrutura_voce_precisa__c",
        "Qual_o_tipo_de_projeto__c",
        "Interesse_Comercial__c",
    ],
    "MEC Estruturas Met\u00e1licas": [
        "Que_tipo_de_estrutura_voce_precisa__c",
        "Qual_o_estagio_do_seu_projeto__c",
    ],
    "Flex Medi\u00e7\u00f5es": [
        "Qualificacao_de_Servico__c",
        "Qualificacao_de_Setor__c",
        "Qualificacao_de_Urgencia__c",
    ],
    "Flex Solar": [
        "Potencia_Estimada__c",
        "Previsao_de_Instalcao__c",
    ],
    "GF2 Solu\u00e7\u00f5es Integradas": [
        "Estagio_do_Projeto__c",
    ],
}

CAMPOS_OPP_ESPECIFICOS = {
    "Flex Energy": [
        "Temperatura_da_Oportunidade_Energy__c",
        "Faixa_de_Consumo_ENERGY__c",
        "Pontos_de_Conexao_ENERGY__c",
        "Etapa_de_Contrato_ENERGY__c",
        "Tipo_de_Conta_ENERGY__c",
    ],
    "Flex Tendas": [
        "Motivo_da_Locacao_TENDAS__c",
        "Tipo_de_Locacao_TENDAS__c",
        "Metragem__c",
    ],
    "Flex Medi\u00e7\u00f5es": [
        "Interesse_Comercial_MEDICOES__c",
        "Tipo_de_Servico_MEDICOES__c",
        "Obrigatoriedade_MEDICOES__c",
    ],
    "Flex Solar": [
        "Quantidade_de_Modulos__c",
    ],
    "GF2 Solu\u00e7\u00f5es Integradas": [],
    "MEC Estruturas Met\u00e1licas": [],
}

# --- Cache TTL ---
CACHE_TTL_SECONDS = 300  # 5 minutos

# --- Periodos pre-definidos ---
from datetime import date, timedelta
import calendar

def get_periodo(nome: str) -> tuple[date, date]:
    hoje = date.today()
    if nome == "Ultimo mes":
        return hoje - timedelta(days=30), hoje
    elif nome == "Ultimo trimestre":
        return hoje - timedelta(days=90), hoje
    elif nome == "Ultimo semestre":
        return hoje - timedelta(days=180), hoje
    elif nome == "Ano atual":
        return date(hoje.year, 1, 1), hoje
    elif nome == "Tudo":
        return date(2020, 1, 1), hoje
    return hoje - timedelta(days=30), hoje


# --- Dias uteis ---
# Feriados nacionais Brasil 2025-2026 (fixos + moveis)
FERIADOS_BR = {
    # 2025
    date(2025, 1, 1), date(2025, 3, 3), date(2025, 3, 4),  # Carnaval
    date(2025, 4, 18),  # Sexta-feira Santa
    date(2025, 4, 21), date(2025, 5, 1), date(2025, 6, 19),  # Corpus Christi
    date(2025, 9, 7), date(2025, 10, 12), date(2025, 11, 2),
    date(2025, 11, 15), date(2025, 12, 25),
    # 2026
    date(2026, 1, 1), date(2026, 2, 16), date(2026, 2, 17),  # Carnaval
    date(2026, 4, 3),  # Sexta-feira Santa
    date(2026, 4, 21), date(2026, 5, 1), date(2026, 6, 4),  # Corpus Christi
    date(2026, 9, 7), date(2026, 10, 12), date(2026, 11, 2),
    date(2026, 11, 15), date(2026, 12, 25),
}


def dias_uteis_no_mes(ano: int, mes: int) -> int:
    """Total de dias uteis (seg-sex, sem feriados) no mes inteiro."""
    total = 0
    _, dias = calendar.monthrange(ano, mes)
    for dia in range(1, dias + 1):
        d = date(ano, mes, dia)
        if d.weekday() < 5 and d not in FERIADOS_BR:
            total += 1
    return total


def dias_uteis_ate_hoje(ano: int, mes: int) -> int:
    """Dias uteis decorridos no mes ate hoje (inclusive)."""
    hoje = date.today()
    total = 0
    _, dias = calendar.monthrange(ano, mes)
    limite = min(hoje.day, dias)
    for dia in range(1, limite + 1):
        d = date(ano, mes, dia)
        if d.weekday() < 5 and d not in FERIADOS_BR:
            total += 1
    return total


MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

MESES_PT_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
