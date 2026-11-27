from datetime import date, datetime, timedelta, timezone

from radar.horario import carregar_feriados, em_brasilia, fuso_ny, ultimo_fechamento_ny


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_horario_de_verao_de_nova_york():
    assert fuso_ny(utc(2026, 3, 8, 6, 59)).utcoffset(None) == timedelta(hours=-5)
    assert fuso_ny(utc(2026, 3, 8, 7, 0)).utcoffset(None) == timedelta(hours=-4)
    assert fuso_ny(utc(2026, 11, 1, 5, 59)).utcoffset(None) == timedelta(hours=-4)
    assert fuso_ny(utc(2026, 11, 1, 6, 0)).utcoffset(None) == timedelta(hours=-5)


def test_brasilia_e_utc_menos_3():
    assert em_brasilia(utc(2026, 11, 27, 13, 0)).hour == 10


def test_pula_feriado_de_acao_de_gracas():
    # 27/11/2026 de manhã: 26/11 foi feriado, então o último fechamento é 25/11 às 16h de NY
    assert ultimo_fechamento_ny(utc(2026, 11, 27, 13, 35)) == utc(2026, 11, 25, 21, 0)


def test_pregao_curto_fecha_as_13h():
    assert ultimo_fechamento_ny(utc(2026, 11, 27, 17, 59)) == utc(2026, 11, 25, 21, 0)
    assert ultimo_fechamento_ny(utc(2026, 11, 27, 18, 0)) == utc(2026, 11, 27, 18, 0)


def test_fim_de_semana_volta_para_sexta():
    # segunda 30/11/2026 de manhã -> sexta 27/11 (pregão curto, 13h de NY)
    assert ultimo_fechamento_ny(utc(2026, 11, 30, 12, 0)) == utc(2026, 11, 27, 18, 0)


def test_fechamento_no_horario_de_verao():
    assert ultimo_fechamento_ny(utc(2026, 7, 15, 20, 0)) == utc(2026, 7, 15, 20, 0)
    assert ultimo_fechamento_ny(utc(2026, 7, 15, 19, 59)) == utc(2026, 7, 14, 20, 0)


def test_arquivo_de_feriados_e_lido():
    fechados, curtos = carregar_feriados()
    assert date(2026, 12, 25) in fechados
    assert date(2026, 11, 27) in curtos
