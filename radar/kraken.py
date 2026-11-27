"""Acesso à API PÚBLICA da Kraken (só leitura, sem conta e sem chave).

Este módulo nunca usa os endpoints privados: o programa não compra, não vende
e não mexe em dinheiro.
"""
import time as _time
from datetime import timedelta

import requests

from radar.ativos import CRIPTO, XSTOCK, da_classe

BASE = "https://api.kraken.com/0/public/"
TIMEOUT = 15
# Erros da Kraken que passam sozinhos: vale tentar de novo depois de uma pausa curta.
ERROS_PASSAGEIROS = ("EAPI:Rate limit", "EService:Unavailable", "EService:Busy", "EGeneral:Temporary")


class ErroKraken(Exception):
    pass


def _baixar(endpoint, params):
    """Faz a requisição e devolve o JSON. Separado para os testes trocarem por arquivos gravados."""
    resposta = requests.get(BASE + endpoint, params=params, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json()


def chamar(endpoint, params, tentativas=3, espera=2.0):
    """Chama um endpoint público e devolve o campo `result`, tentando de novo em erros passageiros."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            dados = _baixar(endpoint, params)
        except (requests.RequestException, ValueError) as erro:
            ultimo_erro = f"falha de conexão: {erro}"
        else:
            erros = dados.get("error") or []
            if not erros:
                return dados["result"]
            ultimo_erro = "; ".join(erros)
            if not any(e.startswith(ERROS_PASSAGEIROS) for e in erros):
                break  # erro definitivo (par errado, por exemplo): não adianta insistir
        if tentativa < tentativas:
            _time.sleep(espera * tentativa)
    raise ErroKraken(f"{endpoint} {params}: {ultimo_erro}")


def _params(classe, pares):
    p = {"pair": ",".join(pares)}
    if classe == XSTOCK:
        p["asset_class"] = "tokenized_asset"
    return p


def _mapa_chaves(classe, pares):
    """Liga cada par pedido (XBTUSD, NVDAx/USD) à chave que a Kraken usa na resposta (XXBTZUSD...).

    Usa /AssetPairs (altname e wsname) em vez de nomes fixos no código.
    """
    info = chamar("AssetPairs", _params(classe, pares))
    mapa = {}
    for chave, dados in info.items():
        for nome in (chave, dados.get("altname"), dados.get("wsname")):
            if nome in pares:
                mapa[nome] = chave
    return mapa


def _ler_ticker(t):
    return {
        "preco_usd": float(t["c"][0]),
        "abertura_utc_usd": float(t["o"]),
        "max_24h_usd": float(t["h"][1]),
        "min_24h_usd": float(t["l"][1]),
    }


def buscar_precos():
    """Último preço, abertura do dia (UTC) e máxima/mínima de 24h dos 15 ativos.

    Devolve (precos, faltando): `precos` é {id: {...}}, `faltando` é a lista de ids
    que a Kraken não devolveu.
    """
    precos, faltando = {}, []
    for classe in (CRIPTO, XSTOCK):
        ativos = da_classe(classe)
        pares = [a["par"] for a in ativos]
        # O /AssetPairs não lista xStocks, mas o Ticker delas já responde com o nome pedido.
        mapa = _mapa_chaves(classe, pares) if classe == CRIPTO else {}
        ticker = chamar("Ticker", _params(classe, pares))
        for a in ativos:
            chave = mapa.get(a["par"], a["par"])
            if chave in ticker:
                precos[a["id"]] = _ler_ticker(ticker[chave])
            else:
                faltando.append(a["id"])
    return precos, faltando


def candles(par, classe, intervalo):
    """Candles OHLC de um par: lista de [início (s), abertura, máxima, mínima, fechamento, ...].
    `intervalo` em minutos (60 = 1 hora, 1440 = 1 dia). A Kraken devolve até 720."""
    resultado = chamar("OHLC", _params(classe, [par]) | {"interval": intervalo})
    for chave, lista in resultado.items():
        if chave != "last":
            return lista
    return []


def _candle_que_comeca(lista, inicio_utc):
    alvo = int(inicio_utc.timestamp())
    return next((c for c in lista if int(c[0]) == alvo), None)


def fechamento_em(par, fechamento_utc):
    """Preço de uma xStock no fechamento de Nova York: o fechamento do candle de 1 hora
    que termina naquele horário. Devolve None se o candle não estiver na resposta."""
    c = _candle_que_comeca(candles(par, XSTOCK, 60), fechamento_utc - timedelta(hours=1))
    return float(c[4]) if c else None


def abertura_da_hora(par, classe, hora_utc):
    """Preço de abertura do candle de 1 hora que começa em `hora_utc` (None se não houver)."""
    c = _candle_que_comeca(candles(par, classe, 60), hora_utc)
    return float(c[1]) if c else None
