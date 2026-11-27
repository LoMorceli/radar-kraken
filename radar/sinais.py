"""Histórico de sinais: cada aviso enviado no Telegram vira uma linha em dados/sinais.csv.

Colunas: data_utc, data_brasilia, id, ticker, regra_id, tipo, sentido, preco_usd, motivo.
"sentido" só é preenchido nas regras de variação ("alta" ou "queda").
"""
import csv

from radar.coletar import de_iso, iso
from radar.horario import em_brasilia

COLUNAS = ["data_utc", "data_brasilia", "id", "ticker", "regra_id", "tipo", "sentido", "preco_usd", "motivo"]


def registrar(pasta, resultado, agora):
    """Acrescenta um sinal (um aviso que foi enviado) ao dados/sinais.csv."""
    arquivo = pasta / "sinais.csv"
    novo = not arquivo.exists()
    sentido = ""
    if resultado.get("tipo") == "variacao" and resultado.get("variacao_pct") is not None:
        sentido = "alta" if resultado["variacao_pct"] > 0 else "queda"
    linha = {
        "data_utc": iso(agora),
        "data_brasilia": em_brasilia(agora).strftime("%Y-%m-%d %H:%M"),
        "id": resultado["id"],
        "ticker": resultado["ticker"],
        "regra_id": resultado["regra_id"],
        "tipo": resultado["tipo"],
        "sentido": sentido,
        "preco_usd": resultado["preco_usd"],
        "motivo": resultado["motivo"],
    }
    with open(arquivo, "a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)


def ler(pasta):
    """Lê dados/sinais.csv. Devolve uma lista de dicionários, com preço como número e data como datetime."""
    arquivo = pasta / "sinais.csv"
    if not arquivo.exists():
        return []
    with open(arquivo, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        l["preco_usd"] = float(l["preco_usd"])
        l["quando"] = de_iso(l["data_utc"])
    return linhas
