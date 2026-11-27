import json
from datetime import datetime
from pathlib import Path

import pytest

from radar import kraken

FIXTURES = Path(__file__).parent / "fixtures"


def carregar(nome):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


# Momento em que as respostas foram gravadas: os testes "vivem" nesse instante.
GRAVADO_EM = datetime.fromisoformat(carregar("gravado_em.json")["gravado_em_utc"])


@pytest.fixture
def kraken_gravada(monkeypatch):
    """Troca a internet pelas respostas gravadas em tests/fixtures/. Conta as chamadas."""
    chamadas = []

    def falso(endpoint, params):
        chamadas.append((endpoint, dict(params)))
        xstock = params.get("asset_class") == "tokenized_asset"
        if endpoint == "AssetPairs":
            return carregar("assetpairs_cripto.json")
        if endpoint == "Ticker":
            return carregar("ticker_xstock.json" if xstock else "ticker_cripto.json")
        if endpoint == "OHLC":
            diario = params.get("interval") == 1440
            if xstock:
                return carregar("ohlc1440_spyx.json" if diario else "ohlc60_nvdax.json")
            return carregar("ohlc1440_xbtusd.json" if diario else "ohlc60_xbtusd.json")
        raise AssertionError(f"chamada inesperada: {endpoint}")

    monkeypatch.setattr(kraken, "_baixar", falso)
    monkeypatch.setattr(kraken._time, "sleep", lambda s: None)
    from radar import coletar, topos
    monkeypatch.setattr(coletar.time, "sleep", lambda s: None)
    monkeypatch.setattr(topos.time, "sleep", lambda s: None)
    return chamadas
