import pytest
import requests

from radar import kraken
from radar.ativos import ATIVOS
from tests.conftest import carregar, GRAVADO_EM
from radar.horario import ultimo_fechamento_ny


def test_busca_os_15_precos(kraken_gravada):
    precos, faltando = kraken.buscar_precos()
    assert faltando == []
    assert set(precos) == {a["id"] for a in ATIVOS}
    for p in precos.values():
        assert p["preco_usd"] > 0
        assert p["min_24h_usd"] <= p["max_24h_usd"]


def test_cripto_e_mapeada_pelo_altname(kraken_gravada):
    # a Kraken responde XXBTZUSD para o par pedido XBTUSD
    bruto = carregar("ticker_cripto.json")["result"]["XXBTZUSD"]
    precos, _ = kraken.buscar_precos()
    assert precos["btc"] == {
        "preco_usd": float(bruto["c"][0]),
        "abertura_utc_usd": float(bruto["o"]),
        "max_24h_usd": float(bruto["h"][1]),
        "min_24h_usd": float(bruto["l"][1]),
    }


def test_xstocks_pedem_asset_class(kraken_gravada):
    kraken.buscar_precos()
    pedidos = [p for e, p in kraken_gravada if e == "Ticker" and "NVDAx/USD" in p["pair"]]
    assert pedidos and pedidos[0]["asset_class"] == "tokenized_asset"
    # só 3 chamadas: AssetPairs (cripto), Ticker cripto, Ticker xStocks
    assert len(kraken_gravada) == 3


def test_ativo_que_some_vai_para_faltando(kraken_gravada, monkeypatch):
    original = kraken._baixar

    def sem_tesla(endpoint, params):
        dados = original(endpoint, params)
        if endpoint == "Ticker":
            dados["result"].pop("TSLAx/USD", None)
        return dados

    monkeypatch.setattr(kraken, "_baixar", sem_tesla)
    precos, faltando = kraken.buscar_precos()
    assert faltando == ["tsla"] and len(precos) == 14


def _sequencia(monkeypatch, respostas):
    chamadas = []

    def falso(endpoint, params):
        chamadas.append(endpoint)
        r = respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(kraken, "_baixar", falso)
    monkeypatch.setattr(kraken._time, "sleep", lambda s: None)
    return chamadas


def test_tenta_de_novo_quando_passa_do_limite(monkeypatch):
    chamadas = _sequencia(monkeypatch, [{"error": ["EAPI:Rate limit exceeded"]}, {"error": [], "result": {"ok": 1}}])
    assert kraken.chamar("Ticker", {}) == {"ok": 1}
    assert len(chamadas) == 2


def test_nao_insiste_em_par_errado(monkeypatch):
    chamadas = _sequencia(monkeypatch, [{"error": ["EQuery:Unknown asset pair"]}])
    with pytest.raises(kraken.ErroKraken, match="Unknown asset pair"):
        kraken.chamar("Ticker", {"pair": "XYZ"})
    assert len(chamadas) == 1


def test_desiste_depois_de_3_falhas_de_conexao(monkeypatch):
    erro = requests.ConnectionError("sem internet")
    chamadas = _sequencia(monkeypatch, [erro, erro, erro])
    with pytest.raises(kraken.ErroKraken, match="falha de conexão"):
        kraken.chamar("Ticker", {})
    assert len(chamadas) == 3


def test_fechamento_de_nova_york_pelo_candle_de_1_hora(kraken_gravada):
    fechamento = ultimo_fechamento_ny(GRAVADO_EM)  # 25/11/2026, 21h UTC
    inicio = int(fechamento.timestamp()) - 3600
    candle = next(c for c in carregar("ohlc60_nvdax.json")["result"]["NVDAx/USD"] if c[0] == inicio)
    assert kraken.fechamento_em("NVDAx/USD", fechamento) == float(candle[4])


def test_fechamento_sem_candle_devolve_none(kraken_gravada):
    from datetime import datetime, timezone
    assert kraken.fechamento_em("NVDAx/USD", datetime(2020, 1, 2, 21, tzinfo=timezone.utc)) is None
