"""Data e hora no fuso do campus.

Datas/horas são gravadas no banco como hora local de São Paulo, sem informação
de fuso. O servidor roda em UTC, por isso nunca usar datetime.now() sem fuso.
"""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def agora():
    """Hora local de São Paulo, sem fuso (formato usado no banco)."""
    return datetime.now(FUSO).replace(tzinfo=None, microsecond=0)


def fechamento_padrao(dia: date) -> datetime:
    """RN02: por padrão o formulário fecha às 23h59 do dia da atividade."""
    return datetime.combine(dia, time(23, 59))


# Filtros de template (registrados em create_app).

def formatar_data(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def formatar_hora(valor):
    return valor.strftime("%H:%M") if valor else ""


def formatar_data_hora(valor):
    return valor.strftime("%d/%m/%Y %H:%M") if valor else ""


def formatar_hora_extenso(valor):
    """Ex.: 23h59."""
    return valor.strftime("%Hh%M") if valor else ""
