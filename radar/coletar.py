"""Coleta os preços dos 15 ativos na Kraken e grava em dados/.

    python -m radar.coletar

- dados/precos.json: o último retrato (horário em UTC e em Brasília).
- dados/historico.csv: uma linha por ativo por hora (a primeira coleta de cada hora).
- dados/fechamento_ny.json: preço das xStocks no último fechamento de Nova York,
  buscado uma vez por pregão (não a cada 5 minutos).
- dados/ref_24h.json: preço das criptos 24 horas antes, buscado uma vez por hora.

Variação usada nos gatilhos: cripto em 24 horas; xStocks desde o último fechamento
de Nova York (igual ao painel do claude.ai).
"""
import csv
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar import kraken
from radar.ativos import ATIVOS, CRIPTO, XSTOCK, da_classe
from radar.formato import usd, var
from radar.horario import em_brasilia, ultimo_fechamento_ny

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"
COLUNAS_HISTORICO = ["hora_utc", "id", "preco_usd", "abertura_utc_usd", "max_24h_usd",
                     "min_24h_usd", "fechamento_ny_usd"]


def iso(momento):
    return momento.isoformat(timespec="seconds").replace("+00:00", "Z")


def de_iso(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def _pct(atual, base):
    if atual is None or not base:
        return None
    return round((atual / base - 1) * 100, 2)


def _guardado(arquivo, chave, valor, ids):
    """Devolve os preços guardados no arquivo se ele é da mesma referência e está completo."""
    if not arquivo.exists():
        return None
    salvo = json.loads(arquivo.read_text(encoding="utf-8"))
    precos = salvo.get("precos", {})
    if salvo.get(chave) == valor and all(precos.get(i) is not None for i in ids):
        return precos
    return None


def _buscar_varios(ativos, buscar, pausa):
    precos = {}
    for n, ativo in enumerate(ativos):
        if n:
            time.sleep(pausa)  # não martelar a API
        try:
            precos[ativo["id"]] = buscar(ativo)
        except kraken.ErroKraken as erro:
            print(f"Aviso: {ativo['ticker']}: {erro}", file=sys.stderr)
            precos[ativo["id"]] = None
    return precos


def obter_fechamentos(agora, pasta, feriados=None, pausa=0.5):
    """Preço de cada xStock no último fechamento de NY. Só consulta a Kraken quando
    muda o pregão de referência."""
    fechamento = ultimo_fechamento_ny(agora, feriados)
    arquivo = pasta / "fechamento_ny.json"
    ativos = da_classe(XSTOCK)
    precos = _guardado(arquivo, "fechamento_ny_utc", iso(fechamento), [a["id"] for a in ativos])
    if precos is None:
        precos = _buscar_varios(ativos, lambda a: kraken.fechamento_em(a["par"], fechamento), pausa)
        arquivo.write_text(json.dumps({"fechamento_ny_utc": iso(fechamento), "precos": precos},
                                      indent=1, ensure_ascii=False), encoding="utf-8")
    return fechamento, precos


def obter_ref_24h(agora, pasta, pausa=0.5):
    """Preço de cada cripto 24 horas antes: a abertura do candle de 1 hora que começou
    24 horas antes do início da hora atual. Só consulta a Kraken uma vez por hora."""
    hora = agora.replace(minute=0, second=0, microsecond=0) - timedelta(hours=24)
    arquivo = pasta / "ref_24h.json"
    ativos = da_classe(CRIPTO)
    precos = _guardado(arquivo, "ref_24h_utc", iso(hora), [a["id"] for a in ativos])
    if precos is None:
        precos = _buscar_varios(ativos, lambda a: kraken.abertura_da_hora(a["par"], CRIPTO, hora), pausa)
        arquivo.write_text(json.dumps({"ref_24h_utc": iso(hora), "precos": precos},
                                      indent=1, ensure_ascii=False), encoding="utf-8")
    return hora, precos


def montar_retrato(agora, precos, faltando, fechamento, fech_precos, hora_24h, ref_precos):
    ativos = {}
    for a in ATIVOS:
        p = precos.get(a["id"])
        if p is None:
            continue
        item = {"ticker": a["ticker"], "par": a["par"], "classe": a["classe"], **p,
                "var_abertura_utc_pct": _pct(p["preco_usd"], p["abertura_utc_usd"])}
        if a["classe"] == XSTOCK:
            ref = fech_precos.get(a["id"])
            item |= {"fechamento_ny_usd": ref, "var_ref_desc": "desde o fechamento de Nova York",
                     "var_ref_usd": ref, "var_ref_em": iso(fechamento)}
        else:
            ref = ref_precos.get(a["id"])
            item |= {"ref_24h_usd": ref, "var_ref_desc": "em 24 horas",
                     "var_ref_usd": ref, "var_ref_em": iso(hora_24h)}
        item["var_pct"] = _pct(p["preco_usd"], ref)  # a variação usada nos gatilhos
        ativos[a["id"]] = item
    return {
        "coletado_em_utc": iso(agora),
        "coletado_em_brasilia": em_brasilia(agora).isoformat(timespec="seconds"),
        "fonte": "Kraken (API pública)",
        "fechamento_ny_utc": iso(fechamento),
        "ref_24h_utc": iso(hora_24h),
        "faltando": faltando,
        "ativos": ativos,
    }


def acrescentar_historico(retrato, agora, pasta):
    """Acrescenta uma linha por ativo, só na primeira coleta de cada hora. Devolve True se gravou."""
    arquivo = pasta / "historico.csv"
    hora = agora.strftime("%Y-%m-%dT%H:00Z")
    novo = not arquivo.exists()
    if not novo:
        with arquivo.open(encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f))
        if linhas and linhas[-1]["hora_utc"] == hora:
            return False
    with arquivo.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_HISTORICO)
        if novo:
            w.writeheader()
        for id_, a in retrato["ativos"].items():
            w.writerow({"hora_utc": hora, "id": id_, "preco_usd": a["preco_usd"],
                        "abertura_utc_usd": a["abertura_utc_usd"], "max_24h_usd": a["max_24h_usd"],
                        "min_24h_usd": a["min_24h_usd"], "fechamento_ny_usd": a.get("fechamento_ny_usd", "")})
    return True


def coletar(agora=None, pasta=PASTA_DADOS, feriados=None):
    agora = agora or datetime.now(timezone.utc).replace(microsecond=0)
    pasta.mkdir(parents=True, exist_ok=True)
    precos, faltando = kraken.buscar_precos()
    fechamento, fech_precos = obter_fechamentos(agora, pasta, feriados)
    hora_24h, ref_precos = obter_ref_24h(agora, pasta)
    retrato = montar_retrato(agora, precos, faltando, fechamento, fech_precos, hora_24h, ref_precos)
    (pasta / "precos.json").write_text(json.dumps(retrato, indent=1, ensure_ascii=False), encoding="utf-8")
    retrato["_historico_gravado"] = acrescentar_historico(retrato, agora, pasta)
    return retrato


def mostrar(retrato):
    bsb = datetime.fromisoformat(retrato["coletado_em_brasilia"])
    fech = em_brasilia(de_iso(retrato["fechamento_ny_utc"]))
    print(f"Preços da Kraken (API pública), coletados em {bsb:%d/%m/%Y %H:%M} (Brasília)")
    print(f"Variação: cripto em 24 horas; xStocks desde o fechamento de Nova York de "
          f"{fech:%d/%m} ({fech:%H:%M} de Brasília).\n")
    print(f"{'Ativo':<8}{'Preço':>16}{'Variação':>11}{'Mín 24h':>16}{'Máx 24h':>16}")
    for a in retrato["ativos"].values():
        print(f"{a['ticker']:<8}{usd(a['preco_usd']):>16}{var(a['var_pct']):>11}"
              f"{usd(a['min_24h_usd']):>16}{usd(a['max_24h_usd']):>16}")
    print(f"\n{len(retrato['ativos'])} de {len(ATIVOS)} ativos.", end=" ")
    if retrato["faltando"]:
        print("A Kraken não devolveu: " + ", ".join(retrato["faltando"]) + ".", end=" ")
    print("Histórico: " + ("linha desta hora gravada." if retrato.get("_historico_gravado")
                           else "esta hora já estava gravada."))


def main():
    try:
        retrato = coletar()
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    mostrar(retrato)
    return 0


if __name__ == "__main__":
    sys.exit(main())
