"""Horários: Brasília e fechamento da bolsa de Nova York.

Sem bibliotecas extras: o horário de verão dos EUA segue uma regra fixa
(começa no 2º domingo de março e termina no 1º domingo de novembro, às 2h locais),
e Brasília está em UTC-3 o ano todo desde 2019.
"""
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import yaml

BRASILIA = timezone(timedelta(hours=-3), "Brasília")
ARQUIVO_FERIADOS = Path(__file__).resolve().parent.parent / "config" / "feriados_eua.yaml"


def _domingo(ano, mes, ordem):
    """O n-ésimo domingo do mês (ordem 1 = primeiro)."""
    d = date(ano, mes, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=ordem - 1)


def fuso_ny(momento_utc):
    """Diferença de Nova York para o UTC naquele instante (-4 no verão, -5 no inverno)."""
    ano = momento_utc.year
    inicio = datetime.combine(_domingo(ano, 3, 2), time(7), timezone.utc)  # 2h em NY = 7h UTC
    fim = datetime.combine(_domingo(ano, 11, 1), time(6), timezone.utc)  # 2h em NY = 6h UTC
    return timezone(timedelta(hours=-4 if inicio <= momento_utc < fim else -5))


def em_brasilia(momento_utc):
    return momento_utc.astimezone(BRASILIA)


def carregar_feriados(caminho=ARQUIVO_FERIADOS):
    """Lê os dias sem pregão e os pregões curtos (fecham às 13h de NY)."""
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    fechados = {date.fromisoformat(str(d)) for d in dados.get("fechados", [])}
    curtos = {date.fromisoformat(str(d)) for d in dados.get("pregao_curto", [])}
    return fechados, curtos


def ultimo_fechamento_ny(agora_utc, feriados=None):
    """Instante (em UTC) do último fechamento da bolsa de Nova York até `agora_utc`.

    Fechamento normal às 16h de NY; em pregão curto, às 13h.
    Pula fins de semana e feriados da lista em config/feriados_eua.yaml.
    """
    fechados, curtos = feriados if feriados is not None else carregar_feriados()
    dia = agora_utc.astimezone(fuso_ny(agora_utc)).date()
    for _ in range(15):
        if dia.weekday() < 5 and dia not in fechados:
            hora = 13 if dia in curtos else 16
            # usa o fuso do meio-dia daquele dia, que já tem o horário de verão certo
            fuso = fuso_ny(datetime.combine(dia, time(17), timezone.utc))
            fechamento = datetime.combine(dia, time(hora), fuso).astimezone(timezone.utc)
            if fechamento <= agora_utc:
                return fechamento
        dia -= timedelta(days=1)
    raise ValueError("Nenhum fechamento de Nova York nos últimos 15 dias: confira config/feriados_eua.yaml")
