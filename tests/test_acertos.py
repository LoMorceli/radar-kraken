import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

from radar import acertos, avisar, kraken, relatorio, sinais

T0 = datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc)
DIA = 86400


def _candles_diarios(inicio, precos):
    """Candles diários falsos: um por dia a partir de `inicio` (00:00 UTC), fechando em `precos`."""
    base = int(inicio.replace(hour=0, minute=0, second=0).timestamp())
    return [[base + i * DIA, "0", "0", "0", str(p), "0", "0", 1] for i, p in enumerate(precos)]


@pytest.fixture
def candles_falsos(monkeypatch):
    """BTC sobe 1 dólar por dia a partir de 100; GOOGLx cai 1 por dia a partir de 300."""
    chamadas = []

    def falso(par, classe, intervalo):
        chamadas.append(par)
        assert intervalo == 1440
        if par == "XBTUSD":
            return _candles_diarios(T0, [100 + i for i in range(120)])
        return _candles_diarios(T0, [300 - i for i in range(120)])

    monkeypatch.setattr(kraken, "candles", falso)
    return chamadas


def _resultado(id_="btc", ticker="BTC", regra_id="variacao", tipo="variacao", preco=100.0, v=-8.0):
    return {"id": id_, "ticker": ticker, "regra_id": regra_id, "tipo": tipo, "preco_usd": preco,
            "variacao_pct": v, "disparou": True,
            "motivo": f"{ticker} a US$ {preco}, queda de 8%. Não é recomendação de investimento."}


def test_registra_sinal_no_csv(tmp_path):
    sinais.registrar(tmp_path, _resultado(), T0)
    sinais.registrar(tmp_path, _resultado("googl", "GOOGLx", "preco", "abaixo_de", 268.5, None),
                     T0 + timedelta(hours=1))
    with open(tmp_path / "sinais.csv", encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    assert [l["ticker"] for l in linhas] == ["BTC", "GOOGLx"]
    assert linhas[0]["sentido"] == "queda" and linhas[1]["sentido"] == ""
    assert linhas[0]["data_brasilia"] == "2026-08-01 12:00"
    lidos = sinais.ler(tmp_path)
    assert lidos[1]["preco_usd"] == 268.5 and lidos[1]["quando"] == T0 + timedelta(hours=1)


def test_aviso_enviado_vira_sinal_e_o_nao_enviado_nao(tmp_path):
    from radar.telegram import ErroTelegram
    avisar.avisar([_resultado()], tmp_path, T0, enviar_fn=lambda t: None)
    assert len(sinais.ler(tmp_path)) == 1

    def falha(texto):
        raise ErroTelegram("sem rede")
    avisar.avisar([_resultado("eth", "ETH")], tmp_path, T0, enviar_fn=falha)
    assert len(sinais.ler(tmp_path)) == 1  # o da ETH não saiu, então não conta


def test_sem_telegram_nao_grava_sinal(tmp_path):
    avisar.avisar([_resultado()], tmp_path, T0, enviar_fn=None)
    assert sinais.ler(tmp_path) == []


def test_calcula_7_30_e_90_dias_so_quando_passaram(tmp_path, candles_falsos):
    sinais.registrar(tmp_path, _resultado(preco=100.0), T0)
    dados = acertos.obter(T0 + timedelta(days=31), tmp_path, pausa=0)
    depois = dados["sinais"][0]["depois"]
    assert depois["7"] == {"preco_usd": 107.0, "var_pct": 7.0}
    assert depois["30"] == {"preco_usd": 130.0, "var_pct": 30.0}
    assert "90" not in depois  # ainda não passaram 90 dias
    r = dados["resumo"]
    assert r["7"] == {"com_resultado": 1, "aguardando": 0, "no_positivo": 1, "media_pct": 7.0}
    assert r["90"]["com_resultado"] == 0 and r["90"]["aguardando"] == 1
    salvo = json.loads((tmp_path / "acertos.json").read_text(encoding="utf-8"))
    assert salvo == dados


def test_queda_conta_como_negativo_e_media(tmp_path, candles_falsos):
    sinais.registrar(tmp_path, _resultado(preco=100.0), T0)  # BTC: +7% em 7 dias
    sinais.registrar(tmp_path, _resultado("googl", "GOOGLx", "preco", "abaixo_de", 300.0, None), T0)
    r = acertos.obter(T0 + timedelta(days=8), tmp_path, pausa=0)["resumo"]["7"]
    assert r["com_resultado"] == 2 and r["no_positivo"] == 1
    assert r["media_pct"] == round((7.0 + (293 / 300 - 1) * 100) / 2, 2)


def test_nao_busca_de_novo_o_que_ja_foi_calculado(tmp_path, candles_falsos):
    sinais.registrar(tmp_path, _resultado(preco=100.0), T0)
    acertos.obter(T0 + timedelta(days=8), tmp_path, pausa=0)
    assert len(candles_falsos) == 1
    acertos.obter(T0 + timedelta(days=9), tmp_path, pausa=0)
    assert len(candles_falsos) == 1  # o prazo de 7 dias já estava pronto; 30 e 90 ainda não chegaram


def test_relatorio_sem_nenhum_sinal_ainda_tem_numeros(tmp_path, candles_falsos):
    texto = relatorio.relatorio(agora=T0, pasta=tmp_path)
    assert "Sinais nesta semana: 0" in texto
    assert "Desde o começo: 0 sinal(is)." in texto
    assert "01/08/2026, 12:00 (Brasília)" in texto
    assert texto.endswith("Não é recomendação de investimento.")


def test_relatorio_com_sinais(tmp_path, candles_falsos):
    sinais.registrar(tmp_path, _resultado(preco=100.0), T0)
    sinais.registrar(tmp_path, _resultado("googl", "GOOGLx", "preco", "abaixo_de", 300.0, None),
                     T0 + timedelta(days=9))
    enviados = []
    texto = relatorio.relatorio(agora=T0 + timedelta(days=10), pasta=tmp_path, enviar_fn=enviados.append)
    assert enviados == [texto]
    assert "Sinais nesta semana: 1." in texto  # o da BTC foi há 10 dias, fora da semana
    assert "- GOOGLx (preço) em 10/08, 12:00: US$ 300,00" in texto
    assert "Desde o começo: 2 sinal(is)." in texto
    assert "- 7 dias depois: 1 de 1 no positivo (média +7,00%); 1 ainda sem 7 dias." in texto
    assert "- 30 dias depois: ainda nenhum sinal com 30 dias completos." in texto
    assert len(texto) < 4096


def test_relatorio_sem_dado_pessoal(tmp_path, candles_falsos):
    sinais.registrar(tmp_path, _resultado(), T0)
    texto = relatorio.relatorio(agora=T0 + timedelta(days=8), pasta=tmp_path).lower()
    for proibido in ("lorenzo", "@", "carteira", "saldo", "r$"):
        assert proibido not in texto
