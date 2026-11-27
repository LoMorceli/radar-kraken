"""Compara os preços com as regras de config/gatilhos.yaml e diz quais dispararam.

    python -m radar.regras

Cada resultado traz o motivo em português, com números e data, e termina com
"Não é recomendação de investimento." O programa só avisa: nunca compra nem vende.
"""
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

from radar.ativos import ATIVOS
from radar.formato import num, pct, usd
from radar.horario import em_brasilia

ARQUIVO_REGRAS = Path(__file__).resolve().parent.parent / "config" / "gatilhos.yaml"
FINAL = "Confira as notícias antes de decidir. Não é recomendação de investimento."
CAMPOS = {
    "abaixo_de": ["valor_usd"],
    "ate_pct_acima_de": ["referencia_usd", "referencia_desc", "pct"],
    "pct_abaixo_topo": ["pct"],
    "variacao": ["pct"],
}


class ErroRegras(ValueError):
    pass


def carregar_regras(caminho=ARQUIVO_REGRAS):
    """Devolve {id do ativo: [regras]}, juntando as regras do ativo com as padrão da classe dele."""
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    padroes, por_ativo = dados.get("padroes", {}), dados.get("ativos", {})
    ids_validos = {a["id"] for a in ATIVOS}
    desconhecidos = set(por_ativo) - ids_validos
    if desconhecidos:
        raise ErroRegras(f"gatilhos.yaml tem ativos que não existem: {', '.join(sorted(desconhecidos))}")
    regras = {}
    for a in ATIVOS:
        lista = list(por_ativo.get(a["id"]) or []) + list(padroes.get(a["classe"]) or [])
        vistos = set()
        for r in lista:
            tipo = r.get("tipo")
            if tipo not in CAMPOS:
                raise ErroRegras(f"{a['id']}: tipo de regra desconhecido: {tipo!r}")
            faltam = [c for c in CAMPOS[tipo] + ["id", "gatilho"] if c not in r]
            if faltam:
                raise ErroRegras(f"{a['id']}: a regra {tipo} precisa de: {', '.join(faltam)}")
            if r["id"] in vistos:
                raise ErroRegras(f"{a['id']}: duas regras com o mesmo id {r['id']!r}")
            vistos.add(r["id"])
        regras[a["id"]] = lista
    return regras


def _quando(texto_iso):
    return em_brasilia(datetime.fromisoformat(texto_iso.replace("Z", "+00:00")))


def _data_br(texto_dia):
    return date.fromisoformat(texto_dia).strftime("%d/%m/%Y")


def avaliar_regra(regra, ativo, topo, coletado_em):
    """Avalia uma regra para um ativo. `ativo` é o item de precos.json; `topo`, o de topos.json."""
    preco, nome, tipo = ativo["preco_usd"], ativo["ticker"], regra["tipo"]
    quando = f"Preço da Kraken em {_quando(coletado_em):%d/%m/%Y, %H:%M} (Brasília)."
    r = {"regra_id": regra["id"], "tipo": tipo, "preco_usd": preco, "limite_usd": None,
         "falta_pct": None, "disparou": False}

    if tipo == "abaixo_de":
        limite = float(regra["valor_usd"])
        r |= {"limite_usd": limite, "disparou": preco < limite,
              "falta_pct": round((1 - limite / preco) * 100, 2)}
        if r["disparou"]:
            r["motivo"] = (f"{nome} a {usd(preco)}, abaixo de {usd(limite)} "
                           f"({pct(abs(r['falta_pct']))} abaixo do limite).")

    elif tipo == "ate_pct_acima_de":
        ref = float(regra["referencia_usd"])
        limite = ref * (1 + float(regra["pct"]) / 100)
        acima = (preco / ref - 1) * 100
        r |= {"limite_usd": round(limite, 4), "disparou": preco <= limite,
              "falta_pct": round((1 - limite / preco) * 100, 2)}
        if r["disparou"]:
            lado = f"{pct(acima)} acima" if acima >= 0 else f"{pct(-acima)} abaixo"
            r["motivo"] = f"{nome} a {usd(preco)}, {lado} da {regra['referencia_desc']} ({usd(ref)})."

    elif tipo == "pct_abaixo_topo":
        if not topo:
            r["motivo_sem_dados"] = "sem máxima de 12 meses calculada"
            return r
        maxima = topo["max_12m_usd"]
        limite = maxima * (1 - float(regra["pct"]) / 100)
        queda = (1 - preco / maxima) * 100
        r |= {"limite_usd": round(limite, 4), "disparou": preco <= limite, "queda_do_topo_pct": round(queda, 2),
              "falta_pct": round((1 - limite / preco) * 100, 2)}
        if r["disparou"]:
            r["motivo"] = (f"{nome} a {usd(preco)}, {pct(queda)} abaixo da máxima de 12 meses "
                           f"({usd(maxima)} em {_data_br(topo['max_12m_data'])}).")

    elif tipo == "variacao":
        v, ref = ativo.get("var_pct"), ativo.get("var_ref_usd")
        if v is None:
            r["motivo_sem_dados"] = "sem preço de referência para a variação"
            return r
        r |= {"variacao_pct": v, "disparou": abs(v) >= float(regra["pct"])}
        if r["disparou"]:
            sentido = "alta" if v > 0 else "queda"
            desde = ativo["var_ref_desc"]
            em = _quando(ativo["var_ref_em"])
            if desde == "em 24 horas":
                base = f"(era {usd(ref)} em {em:%d/%m, %H:%M})"
            else:
                base = f"de {em:%d/%m} ({usd(ref)})"
            r["motivo"] = f"{nome} a {usd(preco)}, {sentido} de {pct(abs(v))} {desde} {base}."

    if r["disparou"]:
        r["motivo"] += f" Gatilho: {regra['gatilho']}. {quando} {FINAL}"
    return r


def avaliar(retrato, topos, regras):
    """Avalia todas as regras de todos os ativos. Devolve uma lista de resultados."""
    resultados = []
    for a in ATIVOS:
        ativo = retrato["ativos"].get(a["id"])
        if ativo is None:
            continue
        topo = (topos or {}).get("ativos", {}).get(a["id"])
        for regra in regras.get(a["id"], []):
            r = avaliar_regra(regra, ativo, topo, retrato["coletado_em_utc"])
            resultados.append({"id": a["id"], "ticker": a["ticker"], **r})
    return resultados


def disparados(resultados):
    return [r for r in resultados if r["disparou"]]


def _situacao(r):
    if r["disparou"]:
        return "DISPAROU"
    if r.get("motivo_sem_dados"):
        return "sem dados: " + r["motivo_sem_dados"]
    if r["tipo"] == "variacao":
        return f"não disparou (variação {num(r['variacao_pct'])}%)"
    return f"não disparou (falta cair {pct(r['falta_pct'])})"


def mostrar(resultados):
    print(f"{'Ativo':<8}{'Regra':<20}{'Preço':>15}{'Limite':>15}  Situação")
    for r in resultados:
        print(f"{r['ticker']:<8}{r['tipo']:<20}{usd(r['preco_usd']):>15}{usd(r['limite_usd']):>15}  {_situacao(r)}")
    lista = disparados(resultados)
    print(f"\nGatilhos disparados agora: {len(lista)}.")
    for r in lista:
        print("\n- " + r["motivo"])


def main():
    from radar import coletar, kraken, topos
    try:
        retrato = coletar.coletar()
        tops = topos.obter_topos()
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    mostrar(avaliar(retrato, tops, carregar_regras()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
