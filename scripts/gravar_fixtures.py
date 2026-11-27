"""Grava respostas reais da API pública da Kraken em tests/fixtures/, para os testes
rodarem sem internet. Rode de novo só se o formato da API mudar:

    python -m scripts.gravar_fixtures
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from radar import kraken
from radar.ativos import CRIPTO, XSTOCK, da_classe
from radar.horario import ultimo_fechamento_ny

PASTA = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def salvar(nome, dados):
    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / nome).write_text(json.dumps(dados, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gravado", nome)


def main():
    for classe in (CRIPTO, XSTOCK):
        params = kraken._params(classe, [a["par"] for a in da_classe(classe)])
        if classe == CRIPTO:  # o /AssetPairs não lista xStocks
            salvar(f"assetpairs_{classe}.json", kraken._baixar("AssetPairs", params))
        salvar(f"ticker_{classe}.json", kraken._baixar("Ticker", params))

    ohlc = kraken._baixar("OHLC", kraken._params(XSTOCK, ["NVDAx/USD"]) | {"interval": 60})
    for chave in ohlc["result"]:
        if chave != "last":
            ohlc["result"][chave] = ohlc["result"][chave][-120:]  # últimas 120 horas bastam
    salvar("ohlc60_nvdax.json", ohlc)

    agora = datetime.now(timezone.utc)
    salvar("gravado_em.json", {"gravado_em_utc": agora.isoformat(timespec="seconds"),
                               "ultimo_fechamento_ny_utc": ultimo_fechamento_ny(agora).isoformat()})


if __name__ == "__main__":
    main()
