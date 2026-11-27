import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from radar import kraken

FIXTURES = Path(__file__).parent / "fixtures"
# Momento em que as respostas foram gravadas: os testes "vivem" nesse instante.
GRAVADO_EM = datetime(2026, 11, 27, 13, 35, 20, tzinfo=timezone.utc)


def carregar(nome):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


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
            return carregar("ohlc60_nvdax.json")
        raise AssertionError(f"chamada inesperada: {endpoint}")

    monkeypatch.setattr(kraken, "_baixar", falso)
    monkeypatch.setattr(kraken._time, "sleep", lambda s: None)
    from radar import coletar
    monkeypatch.setattr(coletar.time, "sleep", lambda s: None)
    return chamadas
