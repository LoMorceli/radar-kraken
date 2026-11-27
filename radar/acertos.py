"""Taxa de acerto: quanto o preço andou 7, 30 e 90 dias depois de cada sinal.

A conta é sempre "se tivesse comprado no preço do sinal": positivo = o preço subiu depois.
O preço "N dias depois" é o fechamento do candle diário da Kraken (dia em UTC) que contém
esse momento. Só entra na conta quando os N dias já passaram.

    python -m radar.acertos     # recalcula e grava dados/acertos.json

Resultado passado não garante resultado futuro. Não é recomendação de investimento.
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone

from radar import kraken, sinais
from radar.ativos import ATIVOS
from radar.coletar import PASTA_DADOS, iso
from radar.formato import var

PRAZOS = (7, 30, 90)
POR_ID = {a["id"]: a for a in ATIVOS}


def _chave(s):
    return f"{s['data_utc']}|{s['id']}|{s['regra_id']}"


def preco_no_momento(lista_candles, momento):
    """Fechamento do candle diário que contém `momento` (o último que começou até ali)."""
    alvo = momento.timestamp()
    antes = [c for c in lista_candles if int(c[0]) <= alvo]
    return float(antes[-1][4]) if antes else None


def _resumo(linhas):
    resumo = {}
    for n in PRAZOS:
        com = [l["depois"][str(n)] for l in linhas if l["depois"].get(str(n))]
        positivos = [d for d in com if d["var_pct"] > 0]
        resumo[str(n)] = {
            "com_resultado": len(com),
            "aguardando": len(linhas) - len(com),
            "no_positivo": len(positivos),
            "media_pct": round(sum(d["var_pct"] for d in com) / len(com), 2) if com else None,
        }
    return resumo


def calcular(lista_sinais, agora, anterior=None, pausa=1.0):
    """Monta o conteúdo de acertos.json. Reaproveita o que já foi calculado em `anterior`
    (um prazo que já passou não muda mais) e só busca na Kraken o que falta."""
    antigos = {l["chave"]: l for l in (anterior or {}).get("sinais", [])}
    cache_candles = {}
    linhas = []
    for s in lista_sinais:
        k = _chave(s)
        depois = dict(antigos.get(k, {}).get("depois", {}))
        for n in PRAZOS:
            if depois.get(str(n)) or agora < s["quando"] + timedelta(days=n):
                continue
            ativo = POR_ID.get(s["id"])
            if ativo is None:
                continue
            if s["id"] not in cache_candles:
                if cache_candles:
                    time.sleep(pausa)  # educação com a API pública
                cache_candles[s["id"]] = kraken.candles(ativo["par"], ativo["classe"], 1440)
            preco = preco_no_momento(cache_candles[s["id"]], s["quando"] + timedelta(days=n))
            if preco is not None:
                depois[str(n)] = {"preco_usd": preco,
                                  "var_pct": round((preco / s["preco_usd"] - 1) * 100, 2)}
        linhas.append({"chave": k, "data_utc": s["data_utc"], "data_brasilia": s["data_brasilia"],
                       "id": s["id"], "ticker": s["ticker"], "regra_id": s["regra_id"],
                       "tipo": s["tipo"], "sentido": s.get("sentido", ""),
                       "preco_usd": s["preco_usd"], "depois": depois})
    return {"calculado_em_utc": iso(agora), "conta": "se tivesse comprado no preço do sinal",
            "prazos_dias": list(PRAZOS), "resumo": _resumo(linhas), "sinais": linhas}


def obter(agora, pasta=PASTA_DADOS, pausa=1.0):
    """Recalcula e grava dados/acertos.json. Devolve o conteúdo."""
    arquivo = pasta / "acertos.json"
    anterior = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None
    dados = calcular(sinais.ler(pasta), agora, anterior, pausa)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dados


def main():
    agora = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        dados = obter(agora)
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    print(f"Sinais no histórico: {len(dados['sinais'])}.")
    for n, r in dados["resumo"].items():
        media = var(r["media_pct"])
        print(f"{n:>3} dias depois: {r['no_positivo']} de {r['com_resultado']} no positivo, "
              f"média {media} ({r['aguardando']} ainda aguardando).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
