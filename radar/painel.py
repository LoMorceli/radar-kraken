"""Gera dados/painel.json no formato que o painel "Radar de Investimentos (Kraken)" usa.

    python -m radar.painel

Endereço público (depois do commit):
https://raw.githubusercontent.com/LoMorceli/radar-kraken/main/dados/painel.json

Só preços, topos e gatilhos: nenhum dado pessoal (o repositório é público).
"""
import json
import sys
from urllib.parse import quote

from radar.ativos import ATIVOS, CRIPTO
from radar.coletar import PASTA_DADOS, de_iso
from radar.horario import em_brasilia

FONTE = "Kraken (API pública)"
URL_PUBLICA = "https://raw.githubusercontent.com/LoMorceli/radar-kraken/main/dados/painel.json"


def url_fonte(ativo):
    """Endereço da consulta pública da Kraken que dá o preço deste ativo."""
    base = "https://api.kraken.com/0/public/Ticker?pair=" + quote(ativo["par"], safe="")
    return base if ativo["classe"] == CRIPTO else base + "&asset_class=tokenized_asset"


def _topo(ativo, topo):
    """Cripto: recorde nos candles da Kraken (até 720 dias). Ações e ETFs: máxima de 12 meses.
    É a mesma convenção que o painel já usa."""
    if not topo:
        return None, None, None
    if ativo["classe"] == CRIPTO:
        return topo["max_historico_usd"], "recorde histórico", topo["max_historico_data"]
    return topo["max_12m_usd"], "máxima de 12 meses", topo["max_12m_data"]


def montar(retrato, topos, resultados):
    gat = {}
    for r in resultados:
        gat.setdefault(r["id"], []).append(r)
    data_preco = em_brasilia(de_iso(retrato["coletado_em_utc"])).date().isoformat()
    linhas = []
    for a in ATIVOS:
        p = retrato["ativos"].get(a["id"])
        if p is None:
            continue
        topo_usd, topo_tipo, topo_data = _topo(a, (topos or {}).get("ativos", {}).get(a["id"]))
        queda = round((1 - p["preco_usd"] / topo_usd) * 100, 1) if topo_usd else None
        linha = {
            "id": a["id"],
            "ticker": a["ticker"],
            "preco_usd": p["preco_usd"],
            "data_preco": data_preco,
            "preco_em": retrato["coletado_em_utc"],
            "topo_usd": topo_usd,
            "topo_tipo": topo_tipo,
            "topo_data": topo_data,
            "queda_do_topo_pct": max(queda, 0.0) if queda is not None else None,
            "fonte_preco": FONTE,
            "fonte_preco_url": url_fonte(a),
            "abertura_usd": p["abertura_utc_usd"],
            "max_24h_usd": p["max_24h_usd"],
            "min_24h_usd": p["min_24h_usd"],
            "var_dia_pct": p.get("var_pct"),
            "var_ref_usd": p.get("var_ref_usd"),
            "var_ref_em": p.get("var_ref_em"),
            "var_ref_desc": p.get("var_ref_desc"),
            "gatilhos_disparados": [r["regra_id"] for r in gat.get(a["id"], []) if r["disparou"]],
            "gatilhos": [{"regra": r["regra_id"], "tipo": r["tipo"], "disparou": r["disparou"],
                          "limite_usd": r.get("limite_usd"), "falta_pct": r.get("falta_pct"),
                          "motivo": r.get("motivo")} for r in gat.get(a["id"], [])],
        }
        linhas.append(linha)
    return {
        "atualizado_em_utc": retrato["coletado_em_utc"],
        "atualizado_em_brasilia": retrato["coletado_em_brasilia"],
        "fonte": FONTE,
        "endereco": URL_PUBLICA,
        "observacao": ("Preço e variação vêm da API pública da Kraken. Variação: cripto em 24 horas; "
                       "ações e ETFs desde o último fechamento de Nova York. spx e ndx são o preço em "
                       "dólar do SPYx e do QQQx, não pontos do índice. Não é recomendação de investimento."),
        "ativos": linhas,
    }


def gravar(retrato, topos, resultados, pasta=PASTA_DADOS):
    dados = montar(retrato, topos, resultados)
    (pasta / "painel.json").write_text(json.dumps(dados, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dados


def main():
    from radar import coletar, kraken, regras, topos
    try:
        retrato = coletar.coletar()
        tops = topos.obter_topos()
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    dados = gravar(retrato, tops, regras.avaliar(retrato, tops, regras.carregar_regras()))
    print(f"dados/painel.json gravado com {len(dados['ativos'])} ativos ({dados['atualizado_em_brasilia']}).")
    print(f"Endereço público depois do commit: {URL_PUBLICA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
