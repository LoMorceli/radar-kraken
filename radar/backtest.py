"""Teste das regras no passado (backtest), com os candles diários da Kraken (até 720 dias).

    python -m radar.backtest     # gera relatorios/backtest.md

Como funciona, em poucas palavras:
- Para cada dia do passado, usa o preço de fechamento do dia e vê se a regra estaria disparada.
- Conta um "disparo" quando a regra passa de não disparada para disparada (igual aos avisos).
- Para cada disparo, olha o preço 30 e 90 dias depois ("se tivesse comprado no dia do disparo").
- Compara com comprar todo mês, no dia 1º, o mesmo valor, medido do mesmo jeito (30 e 90 dias depois).

Simplificações (explicadas também no relatório):
- variação: de um fechamento diário para o seguinte (no radar de verdade, cripto usa 24 horas e
  ações usam o fechamento de Nova York, que são parecidos mas não iguais);
- % abaixo do topo: topo = máxima diária dos até 365 dias anteriores (só a partir de 90 dias de dados).

Resultado passado não garante resultado futuro. Não é recomendação de investimento.
"""
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from radar import kraken, regras
from radar.ativos import ATIVOS
from radar.formato import num, usd, var

PRAZOS = (30, 90)
MIN_DIAS_TOPO = 90
POUCOS = 3  # com menos disparos que isso (com resultado), não dá para tirar conclusão
ARQUIVO = Path(__file__).resolve().parent.parent / "relatorios" / "backtest.md"


def dias_de(lista_candles):
    """Converte candles da Kraken em [{dia, fechamento, maxima}], em ordem."""
    return [{"dia": datetime.fromtimestamp(int(c[0]), timezone.utc).date(),
             "fechamento": float(c[4]), "maxima": float(c[2])} for c in lista_candles]


def condicao(regra, dias, i):
    """A regra estaria disparada no dia i? Devolve (disparada, sentido) ou (None, '') sem dados."""
    tipo, preco = regra["tipo"], dias[i]["fechamento"]
    if tipo == "abaixo_de":
        return preco < float(regra["valor_usd"]), ""
    if tipo == "ate_pct_acima_de":
        return preco <= float(regra["referencia_usd"]) * (1 + float(regra["pct"]) / 100), ""
    if tipo == "pct_abaixo_topo":
        if i < MIN_DIAS_TOPO:
            return None, ""
        topo = max(d["maxima"] for d in dias[max(0, i - 364):i + 1])
        return preco <= topo * (1 - float(regra["pct"]) / 100), ""
    if tipo == "variacao":
        if i == 0:
            return None, ""
        v = (preco / dias[i - 1]["fechamento"] - 1) * 100
        return abs(v) >= float(regra["pct"]), ("alta" if v > 0 else "queda")
    raise ValueError(f"tipo de regra desconhecido: {tipo}")


def disparos(regra, dias):
    """Dias em que a regra passou de não disparada para disparada: lista de (i, sentido).
    O primeiro dia com dados só define o estado inicial (não conta como disparo)."""
    saida, antes = [], None
    for i in range(len(dias)):
        agora, sentido = condicao(regra, dias, i)
        if agora is None:
            continue
        if agora and antes is False:
            saida.append((i, sentido))
        antes = agora
    return saida


def resultado_depois(dias, i, n):
    """Variação (%) do fechamento do dia i até o dia i+n; None se ainda não passaram n dias."""
    j = i + n
    if j >= len(dias):
        return None
    return (dias[j]["fechamento"] / dias[i]["fechamento"] - 1) * 100


def compras_mensais(dias):
    """Índices dos dias 1º de cada mês (a compra mensal de mesmo valor)."""
    return [i for i, d in enumerate(dias) if d["dia"].day == 1]


def resumo(indices, dias):
    """Para cada prazo: quantos têm resultado, quantos no positivo e a média (%)."""
    r = {}
    for n in PRAZOS:
        vals = [v for v in (resultado_depois(dias, i, n) for i in indices) if v is not None]
        r[n] = {"com_resultado": len(vals), "no_positivo": sum(v > 0 for v in vals),
                "media_pct": round(sum(vals) / len(vals), 2) if vals else None}
    return r


def veredito(regra_r, mensal_r):
    """Compara a média de 90 dias (ou 30, se não houver 90) com a da compra mensal."""
    for n in (90, 30):
        a, b = regra_r[n], mensal_r[n]
        if a["com_resultado"] >= POUCOS and b["media_pct"] is not None:
            melhor = a["media_pct"] > b["media_pct"]
            return (f"melhor que comprar todo mês ({n} dias)" if melhor
                    else f"não foi melhor que comprar todo mês ({n} dias)")
    return "poucos disparos para concluir"


def testar(ativo, regras_do_ativo, dias):
    """Testa todas as regras de um ativo. Devolve uma lista de linhas para o relatório."""
    mensal = resumo(compras_mensais(dias), dias)
    linhas = []
    for regra in regras_do_ativo:
        todos = disparos(regra, dias)
        grupos = {"": todos} if regra["tipo"] != "variacao" else {
            "queda": [x for x in todos if x[1] == "queda"],
            "alta": [x for x in todos if x[1] == "alta"]}
        for sentido, lista in grupos.items():
            r = resumo([i for i, _ in lista], dias)
            linhas.append({"ativo": ativo, "regra": regra, "sentido": sentido,
                           "disparos": len(lista), "datas": [dias[i]["dia"] for i, _ in lista],
                           "resultado": r, "mensal": mensal, "veredito": veredito(r, mensal),
                           "desde": dias[0]["dia"], "ate": dias[-1]["dia"]})
    return linhas


def _descricao(regra, sentido):
    t = regra["tipo"]
    if t == "abaixo_de":
        return f"preço abaixo de {usd(float(regra['valor_usd']))}"
    if t == "ate_pct_acima_de":
        return f"até {num(float(regra['pct']), 0)}% acima de {usd(float(regra['referencia_usd']))}"
    if t == "pct_abaixo_topo":
        return f"{num(float(regra['pct']), 0)}% abaixo da máxima de 12 meses"
    return f"variação de {num(float(regra['pct']), 0)}% em 1 dia ({sentido})"


def _celula(r):
    if r["com_resultado"] == 0:
        return "—"
    return f"{var(r['media_pct'])} ({r['no_positivo']} de {r['com_resultado']} no positivo)"


def montar_markdown(linhas, gerado_em):
    partes = [
        "# Teste das regras no passado (backtest)",
        "",
        f"Gerado em {gerado_em:%d/%m/%Y} com os candles diários da Kraken (API pública). "
        "Cada regra do `config/gatilhos.yaml` foi aplicada aos preços de fechamento de cada dia.",
        "",
        "## Como ler",
        "",
        "- **Disparos**: quantas vezes a regra passou de \"não disparada\" para \"disparada\".",
        "- **30 dias / 90 dias**: quanto o preço andou depois de cada disparo, em média, "
        "se você tivesse comprado no dia do disparo. Entre parênteses, quantos ficaram no positivo.",
        "- **Comprar todo mês**: a mesma conta para quem compra o mesmo valor todo dia 1º, sem regra nenhuma. "
        "É a comparação que importa: **se a regra não for melhor que isso, ela não está ajudando.**",
        f"- Com menos de {POUCOS} disparos com resultado, não dá para concluir nada.",
        "",
        "## Cuidado antes de tirar conclusões",
        "",
        "- São poucos dados: cripto tem cerca de 2 anos na Kraken, e as xStocks existem desde agosto de 2025 "
        "(AMDx desde janeiro de 2026).",
        "- Os limites de preço (ex.: GOOGLx abaixo de US$ 270) foram escolhidos agora, olhando os preços de agora. "
        "Testar esses números no passado é injusto com eles (para mais ou para menos).",
        "- Variação aqui é de um fechamento diário para o seguinte; no radar de verdade, cripto usa 24 horas e "
        "ações usam o fechamento de Nova York.",
        "- O que funcionou no passado pode não funcionar no futuro. Use este teste para **descartar regras ruins**, "
        "não para ter certeza das boas.",
        "",
        "## Resultado por regra",
        "",
        "| Ativo | Regra | Disparos | 30 dias depois | 90 dias depois | Comprar todo mês (30 / 90 dias) | Conclusão |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in linhas:
        m = l["mensal"]
        partes.append(
            f"| {l['ativo']['ticker']} | {_descricao(l['regra'], l['sentido'])} | {l['disparos']} | "
            f"{_celula(l['resultado'][30])} | {_celula(l['resultado'][90])} | "
            f"{var(m[30]['media_pct'])} / {var(m[90]['media_pct'])} | {l['veredito']} |")
    partes += ["", "## Período de cada ativo", ""]
    vistos = set()
    for l in linhas:
        a = l["ativo"]
        if a["id"] not in vistos:
            vistos.add(a["id"])
            partes.append(f"- {a['ticker']}: {l['desde']:%d/%m/%Y} a {l['ate']:%d/%m/%Y}.")
    partes += ["", "Resultado passado não garante resultado futuro. Não é recomendação de investimento.", ""]
    return "\n".join(partes)


def rodar(hoje=None, arquivo=ARQUIVO, pausa=1.0):
    hoje = hoje or date.today()
    todas = regras.carregar_regras()
    linhas = []
    for n, ativo in enumerate(ATIVOS):
        if n:
            time.sleep(pausa)  # educação com a API pública
        dias = dias_de(kraken.candles(ativo["par"], ativo["classe"], 1440))
        if dias:
            linhas += testar(ativo, todas.get(ativo["id"], []), dias)
    texto = montar_markdown(linhas, hoje)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")
    return linhas, texto


def main():
    try:
        linhas, _ = rodar()
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    print(f"Relatório gravado em {ARQUIVO} ({len(linhas)} linhas de regra).")
    for l in linhas:
        print(f"{l['ativo']['ticker']:<8}{_descricao(l['regra'], l['sentido']):<45}"
              f"{l['disparos']:>3} disparos  {l['veredito']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
