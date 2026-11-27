from datetime import date, timedelta

import pytest

from radar import backtest

D0 = date(2025, 1, 1)


def _dias(fechamentos, maximas=None):
    maximas = maximas or fechamentos
    return [{"dia": D0 + timedelta(days=i), "fechamento": float(f), "maxima": float(m)}
            for i, (f, m) in enumerate(zip(fechamentos, maximas))]


ABAIXO = {"id": "preco", "tipo": "abaixo_de", "valor_usd": 100}
VARIACAO = {"id": "variacao", "tipo": "variacao", "pct": 5}
TOPO = {"id": "preco", "tipo": "pct_abaixo_topo", "pct": 10}


def test_so_conta_quando_passa_a_disparar():
    dias = _dias([110, 105, 99, 98, 97, 101, 99])
    assert [i for i, _ in backtest.disparos(ABAIXO, dias)] == [2, 6]


def test_primeiro_dia_nao_conta_como_disparo():
    dias = _dias([90, 95, 101, 99])  # já começa abaixo de 100
    assert [i for i, _ in backtest.disparos(ABAIXO, dias)] == [3]


def test_variacao_separa_alta_e_queda():
    dias = _dias([100, 100, 106, 106, 100, 100])  # +6% no dia 2, -5,66% no dia 4
    assert backtest.disparos(VARIACAO, dias) == [(2, "alta"), (4, "queda")]


def test_topo_so_depois_de_90_dias():
    precos = [100] * 89 + [85, 85, 100, 89]
    dias = _dias(precos)
    assert [i for i, _ in backtest.disparos(TOPO, dias)] == [92]  # dia 89 e 90 ainda sem dados


def test_resultado_30_e_90_dias():
    dias = _dias([100 + i for i in range(100)])
    assert backtest.resultado_depois(dias, 0, 30) == pytest.approx(30.0)
    assert backtest.resultado_depois(dias, 50, 90) is None  # não passaram 90 dias ainda


def test_compra_mensal_e_no_dia_1():
    dias = _dias([100] * 70)
    assert [dias[i]["dia"] for i in backtest.compras_mensais(dias)] == \
        [date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)]


def test_veredito():
    poucos = {30: {"com_resultado": 2, "no_positivo": 2, "media_pct": 9.0},
              90: {"com_resultado": 0, "no_positivo": 0, "media_pct": None}}
    bom = {30: {"com_resultado": 5, "no_positivo": 4, "media_pct": 6.0},
           90: {"com_resultado": 4, "no_positivo": 3, "media_pct": 12.0}}
    mensal = {30: {"com_resultado": 10, "no_positivo": 5, "media_pct": 2.0},
              90: {"com_resultado": 8, "no_positivo": 5, "media_pct": 15.0}}
    assert backtest.veredito(poucos, mensal) == "poucos disparos para concluir"
    assert backtest.veredito(bom, mensal) == "não foi melhor que comprar todo mês (90 dias)"


def test_relatorio_completo_com_candles_gravados(kraken_gravada, tmp_path):
    arquivo = tmp_path / "relatorios" / "backtest.md"
    linhas, texto = backtest.rodar(hoje=date(2026, 11, 27), arquivo=arquivo, pausa=0)
    assert arquivo.read_text(encoding="utf-8") == texto
    assert texto.startswith("# Teste das regras no passado (backtest)")
    assert "Gerado em 27/11/2026" in texto
    assert "| SPYx | 10% abaixo da máxima de 12 meses |" in texto
    assert texto.rstrip().endswith("Não é recomendação de investimento.")
    # cada ativo tem as linhas das suas regras (variação vira duas: queda e alta)
    btc = [l for l in linhas if l["ativo"]["id"] == "btc"]
    assert [l["sentido"] for l in btc] == ["queda", "alta"]


def test_sem_dado_pessoal(kraken_gravada, tmp_path):
    _, texto = backtest.rodar(arquivo=tmp_path / "b.md", pausa=0)
    for proibido in ("lorenzo", "@", "carteira", "saldo", "r$"):
        assert proibido not in texto.lower()
