import csv
import json
from datetime import timedelta

from radar import coletar
from radar.ativos import ATIVOS
from tests.conftest import GRAVADO_EM


def _linhas(pasta):
    with (pasta / "historico.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_cria_os_arquivos(kraken_gravada, tmp_path):
    retrato = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    salvo = json.loads((tmp_path / "precos.json").read_text(encoding="utf-8"))
    assert salvo["coletado_em_utc"] == "2026-11-27T13:35:20Z"
    assert salvo["coletado_em_brasilia"] == "2026-11-27T10:35:20-03:00"
    assert salvo["fechamento_ny_utc"] == "2026-11-25T21:00:00Z"
    assert len(salvo["ativos"]) == len(ATIVOS) == 15
    assert "_historico_gravado" not in salvo
    assert retrato["_historico_gravado"] is True
    assert len(_linhas(tmp_path)) == 15


def test_variacoes(kraken_gravada, tmp_path):
    a = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)["ativos"]
    nv = a["nvda"]
    assert nv["fechamento_ny_usd"] is not None
    assert nv["var_fechamento_ny_pct"] == round((nv["preco_usd"] / nv["fechamento_ny_usd"] - 1) * 100, 2)
    assert "var_fechamento_ny_pct" not in a["btc"]  # cripto usa só a abertura em UTC
    assert a["btc"]["var_abertura_utc_pct"] is not None


def test_historico_uma_vez_por_hora(kraken_gravada, tmp_path):
    coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    segundo = coletar.coletar(agora=GRAVADO_EM + timedelta(minutes=5), pasta=tmp_path)
    assert segundo["_historico_gravado"] is False
    assert len(_linhas(tmp_path)) == 15
    coletar.coletar(agora=GRAVADO_EM + timedelta(minutes=30), pasta=tmp_path)  # 14:05 UTC: hora nova
    linhas = _linhas(tmp_path)
    assert len(linhas) == 30
    assert {l["hora_utc"] for l in linhas} == {"2026-11-27T13:00Z", "2026-11-27T14:00Z"}


def test_fechamento_de_ny_so_e_buscado_uma_vez_por_pregao(kraken_gravada, tmp_path):
    coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    ohlc = sum(1 for e, _ in kraken_gravada if e == "OHLC")
    assert ohlc == 10  # uma vez para cada xStock
    coletar.coletar(agora=GRAVADO_EM + timedelta(minutes=5), pasta=tmp_path)
    assert sum(1 for e, _ in kraken_gravada if e == "OHLC") == 10  # usou o arquivo guardado


def test_mostra_15_linhas_em_portugues(kraken_gravada, tmp_path, capsys):
    coletar.mostrar(coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path))
    saida = capsys.readouterr().out
    for a in ATIVOS:
        assert f"\n{a['ticker']:<8}" in saida
    assert "15 de 15 ativos." in saida
    assert "27/11/2026 10:35 (Brasília)" in saida


def test_formato_brasileiro_dos_numeros():
    assert coletar._usd(61586.0) == "US$ 61.586,00"
    assert coletar._usd(0.97931) == "US$ 0,9793"
    assert coletar._var(1.2) == "+1,20%"
    assert coletar._var(-3.456) == "-3,46%"
    assert coletar._var(None) == "—"
