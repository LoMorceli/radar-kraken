import csv
import json
from datetime import timedelta

from radar import coletar
from radar.ativos import ATIVOS
from radar.horario import em_brasilia, ultimo_fechamento_ny
from tests.conftest import GRAVADO_EM

# um instante no começo da hora da gravação: +5 min fica na mesma hora, +60 min vira hora nova
BASE = GRAVADO_EM.replace(minute=10, second=0)


def _linhas(pasta):
    with (pasta / "historico.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_cria_os_arquivos(kraken_gravada, tmp_path):
    retrato = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    salvo = json.loads((tmp_path / "precos.json").read_text(encoding="utf-8"))
    assert salvo["coletado_em_utc"] == coletar.iso(GRAVADO_EM)
    assert salvo["coletado_em_brasilia"] == em_brasilia(GRAVADO_EM).isoformat()
    assert salvo["fechamento_ny_utc"] == coletar.iso(ultimo_fechamento_ny(GRAVADO_EM))
    assert len(salvo["ativos"]) == len(ATIVOS) == 15
    assert "_historico_gravado" not in salvo
    assert retrato["_historico_gravado"] is True
    assert len(_linhas(tmp_path)) == 15


def test_variacao_das_acoes_e_desde_o_fechamento_de_ny(kraken_gravada, tmp_path):
    nv = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)["ativos"]["nvda"]
    assert nv["fechamento_ny_usd"] is not None
    assert nv["var_ref_usd"] == nv["fechamento_ny_usd"]
    assert nv["var_ref_desc"] == "desde o fechamento de Nova York"
    assert nv["var_pct"] == round((nv["preco_usd"] / nv["fechamento_ny_usd"] - 1) * 100, 2)


def test_variacao_das_criptos_e_em_24_horas(kraken_gravada, tmp_path):
    btc = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)["ativos"]["btc"]
    hora = GRAVADO_EM.replace(minute=0, second=0) - timedelta(hours=24)
    assert btc["var_ref_em"] == coletar.iso(hora)
    assert btc["ref_24h_usd"] is not None and btc["var_ref_desc"] == "em 24 horas"
    assert btc["var_pct"] == round((btc["preco_usd"] / btc["ref_24h_usd"] - 1) * 100, 2)
    assert "fechamento_ny_usd" not in btc


def test_historico_uma_vez_por_hora(kraken_gravada, tmp_path):
    coletar.coletar(agora=BASE, pasta=tmp_path)
    segundo = coletar.coletar(agora=BASE + timedelta(minutes=5), pasta=tmp_path)
    assert segundo["_historico_gravado"] is False
    assert len(_linhas(tmp_path)) == 15
    coletar.coletar(agora=BASE + timedelta(minutes=60), pasta=tmp_path)
    linhas = _linhas(tmp_path)
    assert len(linhas) == 30
    assert len({l["hora_utc"] for l in linhas}) == 2


def test_referencias_sao_guardadas_e_nao_buscadas_a_cada_5_minutos(kraken_gravada, tmp_path):
    def ohlc():
        return [p for e, p in kraken_gravada if e == "OHLC"]

    coletar.coletar(agora=BASE, pasta=tmp_path)
    assert len(ohlc()) == 15  # 10 fechamentos de NY + 5 preços de 24h atrás
    coletar.coletar(agora=BASE + timedelta(minutes=5), pasta=tmp_path)
    assert len(ohlc()) == 15  # usou os arquivos guardados
    coletar.coletar(agora=BASE + timedelta(minutes=60), pasta=tmp_path)
    assert len(ohlc()) == 20  # hora nova: só as 5 criptos de novo


def test_mostra_15_linhas_em_portugues(kraken_gravada, tmp_path, capsys):
    coletar.mostrar(coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path))
    saida = capsys.readouterr().out
    for a in ATIVOS:
        assert f"\n{a['ticker']:<8}" in saida
    assert "15 de 15 ativos." in saida
    assert f"{em_brasilia(GRAVADO_EM):%d/%m/%Y %H:%M} (Brasília)" in saida
