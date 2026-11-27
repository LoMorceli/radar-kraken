"""Grava respostas reais da API pública da Kraken em tests/fixtures/, para os testes
rodarem sem internet. Rode de novo só se o formato da API mudar:

    python -m scripts.gravar_fixtures
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from radar import kraken
from radar.ativos import CRIPTO, XSTOCK, da_classe

PASTA = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def salvar(nome, dados):
    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / nome).write_text(json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gravado", nome)


def ohlc(par, classe, intervalo, ultimos=None):
    dados = kraken._baixar("OHLC", kraken._params(classe, [par]) | {"interval": intervalo})
    if ultimos:
        for chave in dados["result"]:
            if chave != "last":
                dados["result"][chave] = dados["result"][chave][-ultimos:]
    return dados


def main():
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    for classe in (CRIPTO, XSTOCK):
        params = kraken._params(classe, [a["par"] for a in da_classe(classe)])
        if classe == CRIPTO:  # o /AssetPairs não lista xStocks
            salvar(f"assetpairs_{classe}.json", kraken._baixar("AssetPairs", params))
        salvar(f"ticker_{classe}.json", kraken._baixar("Ticker", params))

    salvar("ohlc60_nvdax.json", ohlc("NVDAx/USD", XSTOCK, 60, ultimos=120))  # fechamento de NY
    salvar("ohlc60_xbtusd.json", ohlc("XBTUSD", CRIPTO, 60, ultimos=72))  # preço de 24h atrás
    salvar("ohlc1440_xbtusd.json", ohlc("XBTUSD", CRIPTO, 1440))  # topos (720 dias)
    salvar("ohlc1440_spyx.json", ohlc("SPYx/USD", XSTOCK, 1440))
    salvar("gravado_em.json", {"gravado_em_utc": agora.isoformat()})


if __name__ == "__main__":
    main()
