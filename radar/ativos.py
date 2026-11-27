"""Os 15 ativos acompanhados, com os mesmos ids do painel do claude.ai."""

CRIPTO = "cripto"
XSTOCK = "xstock"

# id do painel -> par na Kraken. Para cripto o par é o "altname" (XBTUSD);
# para xStocks é o nome com barra (NVDAx/USD), que exige asset_class=tokenized_asset.
ATIVOS = [
    {"id": "btc", "par": "XBTUSD", "classe": CRIPTO, "ticker": "BTC"},
    {"id": "eth", "par": "ETHUSD", "classe": CRIPTO, "ticker": "ETH"},
    {"id": "sol", "par": "SOLUSD", "classe": CRIPTO, "ticker": "SOL"},
    {"id": "xrp", "par": "XRPUSD", "classe": CRIPTO, "ticker": "XRP"},
    {"id": "bnb", "par": "BNBUSD", "classe": CRIPTO, "ticker": "BNB"},
    {"id": "nvda", "par": "NVDAx/USD", "classe": XSTOCK, "ticker": "NVDAx"},
    {"id": "amd", "par": "AMDx/USD", "classe": XSTOCK, "ticker": "AMDx"},
    {"id": "googl", "par": "GOOGLx/USD", "classe": XSTOCK, "ticker": "GOOGLx"},
    {"id": "meta", "par": "METAx/USD", "classe": XSTOCK, "ticker": "METAx"},
    {"id": "msft", "par": "MSFTx/USD", "classe": XSTOCK, "ticker": "MSFTx"},
    {"id": "aapl", "par": "AAPLx/USD", "classe": XSTOCK, "ticker": "AAPLx"},
    {"id": "amzn", "par": "AMZNx/USD", "classe": XSTOCK, "ticker": "AMZNx"},
    {"id": "tsla", "par": "TSLAx/USD", "classe": XSTOCK, "ticker": "TSLAx"},
    {"id": "spx", "par": "SPYx/USD", "classe": XSTOCK, "ticker": "SPYx"},
    {"id": "ndx", "par": "QQQx/USD", "classe": XSTOCK, "ticker": "QQQx"},
]


def da_classe(classe):
    return [a for a in ATIVOS if a["classe"] == classe]
