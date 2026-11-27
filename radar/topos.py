"""Topos de cada ativo, calculados pelos candles diários da Kraken (até 720 dias).

    python -m radar.topos

Grava dados/topos.json, recalculado uma vez por dia (dia em UTC):
- máxima de 12 meses: a maior máxima diária dos últimos 365 dias;
- máxima de todo o histórico disponível (até 720 dias). Para cripto é o "recorde"
  que o painel mostra; as xStocks só existem desde meados de 2025.
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from radar import kraken
from radar.ativos import ATIVOS
from radar.coletar import PASTA_DADOS, iso
from radar.formato import usd

DIAS_12_MESES = 365


def _dia(segundos):
    return datetime.fromtimestamp(int(segundos), timezone.utc).date().isoformat()


def calcular_topo(candles_diarios, agora):
    """Recebe os candles diários de um ativo e devolve as máximas (None se não houver candles)."""
    if not candles_diarios:
        return None
    limite = (agora - timedelta(days=DIAS_12_MESES)).timestamp()
    ultimos_12m = [c for c in candles_diarios if int(c[0]) >= limite]
    maior_12m = max(ultimos_12m, key=lambda c: float(c[2]))
    maior_tudo = max(candles_diarios, key=lambda c: float(c[2]))
    return {
        "max_12m_usd": float(maior_12m[2]),
        "max_12m_data": _dia(maior_12m[0]),
        "max_historico_usd": float(maior_tudo[2]),
        "max_historico_data": _dia(maior_tudo[0]),
        "historico_desde": _dia(candles_diarios[0][0]),
        "dias_de_historico": len(candles_diarios),
    }


def obter_topos(agora=None, pasta=PASTA_DADOS, pausa=1.0):
    """Topos de todos os ativos. Só consulta a Kraken se ainda não calculou hoje (UTC)."""
    agora = agora or datetime.now(timezone.utc).replace(microsecond=0)
    arquivo = pasta / "topos.json"
    hoje = agora.date().isoformat()
    if arquivo.exists():
        salvo = json.loads(arquivo.read_text(encoding="utf-8"))
        if salvo.get("dia_utc") == hoje and all(salvo["ativos"].get(a["id"]) for a in ATIVOS):
            return salvo
    ativos = {}
    for n, a in enumerate(ATIVOS):
        if n:
            time.sleep(pausa)  # 15 consultas uma vez por dia, com calma
        try:
            ativos[a["id"]] = calcular_topo(kraken.candles(a["par"], a["classe"], 1440), agora)
        except kraken.ErroKraken as erro:
            print(f"Aviso: sem candles diários de {a['ticker']}: {erro}", file=sys.stderr)
            ativos[a["id"]] = None
    resultado = {"dia_utc": hoje, "calculado_em_utc": iso(agora), "fonte": "Kraken (API pública), candles diários",
                 "ativos": ativos}
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")
    return resultado


def main():
    topos = obter_topos()
    print(f"Topos calculados em {topos['calculado_em_utc']} (candles diários da Kraken)\n")
    print(f"{'Ativo':<8}{'Máx. 12 meses':>18}{'em':>12}{'Máx. histórico':>18}{'em':>12}")
    for a in ATIVOS:
        t = topos["ativos"].get(a["id"])
        if not t:
            print(f"{a['ticker']:<8}{'sem dados':>18}")
            continue
        print(f"{a['ticker']:<8}{usd(t['max_12m_usd']):>18}{t['max_12m_data']:>12}"
              f"{usd(t['max_historico_usd']):>18}{t['max_historico_data']:>12}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
