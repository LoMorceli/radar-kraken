"""Coleta os preços dos 15 ativos na Kraken e grava em dados/.

    python -m radar.coletar

- dados/precos.json: o último retrato (horário em UTC e em Brasília).
- dados/historico.csv: uma linha por ativo por hora (a primeira coleta de cada hora).
- dados/fechamento_ny.json: preço das xStocks no último fechamento de Nova York,
  buscado uma vez por pregão (não a cada 5 minutos).
"""
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from radar import kraken
from radar.ativos import ATIVOS, XSTOCK, da_classe
from radar.horario import em_brasilia, ultimo_fechamento_ny

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"
COLUNAS_HISTORICO = ["hora_utc", "id", "preco_usd", "abertura_utc_usd", "max_24h_usd",
                     "min_24h_usd", "fechamento_ny_usd"]


def _iso(momento):
    return momento.isoformat(timespec="seconds").replace("+00:00", "Z")


def _pct(atual, base):
    if atual is None or not base:
        return None
    return round((atual / base - 1) * 100, 2)


def obter_fechamentos(agora, pasta, feriados=None, pausa=0.5):
    """Preço de cada xStock no último fechamento de NY, guardado em fechamento_ny.json.
    Só consulta a Kraken quando muda o pregão de referência."""
    fechamento = ultimo_fechamento_ny(agora, feriados)
    arquivo = pasta / "fechamento_ny.json"
    ids = [a["id"] for a in da_classe(XSTOCK)]
    if arquivo.exists():
        salvo = json.loads(arquivo.read_text(encoding="utf-8"))
        if salvo.get("fechamento_ny_utc") == _iso(fechamento) and all(
                salvo.get("precos", {}).get(i) is not None for i in ids):
            return fechamento, salvo["precos"]
    precos = {}
    for n, ativo in enumerate(da_classe(XSTOCK)):
        if n:
            time.sleep(pausa)  # não martelar a API
        try:
            precos[ativo["id"]] = kraken.fechamento_em(ativo["par"], fechamento)
        except kraken.ErroKraken as erro:
            print(f"Aviso: sem fechamento de NY para {ativo['ticker']}: {erro}", file=sys.stderr)
            precos[ativo["id"]] = None
    arquivo.write_text(json.dumps({"fechamento_ny_utc": _iso(fechamento), "precos": precos},
                                  indent=1, ensure_ascii=False), encoding="utf-8")
    return fechamento, precos


def montar_retrato(agora, precos, faltando, fechamento, fech_precos):
    ativos = {}
    for a in ATIVOS:
        p = precos.get(a["id"])
        if p is None:
            continue
        item = {"ticker": a["ticker"], "par": a["par"], "classe": a["classe"], **p,
                "var_abertura_utc_pct": _pct(p["preco_usd"], p["abertura_utc_usd"])}
        if a["classe"] == XSTOCK:
            f = fech_precos.get(a["id"])
            item["fechamento_ny_usd"] = f
            item["var_fechamento_ny_pct"] = _pct(p["preco_usd"], f)
        ativos[a["id"]] = item
    return {
        "coletado_em_utc": _iso(agora),
        "coletado_em_brasilia": em_brasilia(agora).isoformat(timespec="seconds"),
        "fonte": "Kraken (API pública)",
        "fechamento_ny_utc": _iso(fechamento),
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
    retrato = montar_retrato(agora, precos, faltando, fechamento, fech_precos)
    (pasta / "precos.json").write_text(json.dumps(retrato, indent=1, ensure_ascii=False), encoding="utf-8")
    retrato["_historico_gravado"] = acrescentar_historico(retrato, agora, pasta)
    return retrato


# ---------- saída na tela, em português ----------

def _num(valor, casas=2):
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _usd(valor):
    if valor is None:
        return "—"
    return "US$ " + _num(valor, 4 if valor < 10 else 2)


def _var(pct):
    return "—" if pct is None else ("+" if pct > 0 else "") + _num(pct) + "%"


def mostrar(retrato):
    bsb = datetime.fromisoformat(retrato["coletado_em_brasilia"])
    fech = em_brasilia(datetime.fromisoformat(retrato["fechamento_ny_utc"].replace("Z", "+00:00")))
    print(f"Preços da Kraken (API pública), coletados em {bsb:%d/%m/%Y %H:%M} (Brasília)")
    print(f"Variação: cripto desde a abertura do dia em UTC (21h de Brasília); "
          f"xStocks desde o fechamento de Nova York de {fech:%d/%m} ({fech:%H:%M} de Brasília).\n")
    print(f"{'Ativo':<8}{'Preço':>16}{'Variação':>11}{'Mín 24h':>16}{'Máx 24h':>16}")
    for a in retrato["ativos"].values():
        var = a.get("var_fechamento_ny_pct") if a["classe"] == XSTOCK else a["var_abertura_utc_pct"]
        print(f"{a['ticker']:<8}{_usd(a['preco_usd']):>16}{_var(var):>11}"
              f"{_usd(a['min_24h_usd']):>16}{_usd(a['max_24h_usd']):>16}")
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
