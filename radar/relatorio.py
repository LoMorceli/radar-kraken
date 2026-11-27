"""Relatório semanal no Telegram (domingo à noite): sinais da semana e taxa de acerto.

    python -m radar.relatorio    # recalcula dados/acertos.json e manda o relatório
                                 # (sem Telegram configurado, só mostra na tela)
"""
import sys
from datetime import datetime, timedelta, timezone

from radar import acertos, kraken, sinais, telegram
from radar.coletar import PASTA_DADOS, de_iso
from radar.formato import usd, var
from radar.horario import em_brasilia

SEMANA = timedelta(days=7)
MAX_LINHAS = 15  # o Telegram aceita até 4096 caracteres por mensagem
FINAL = "Resultado passado não garante resultado futuro. Não é recomendação de investimento."
NOME_REGRA = {"preco": "preço", "variacao": "variação"}


def _linha_sinal(s):
    regra = NOME_REGRA.get(s["regra_id"], s["regra_id"])
    if s.get("sentido"):
        regra += f", {s['sentido']}"
    quando = em_brasilia(s["quando"])
    return f"- {s['ticker']} ({regra}) em {quando:%d/%m, %H:%M}: {usd(s['preco_usd'])}"


def _linha_prazo(n, r):
    if r["com_resultado"] == 0:
        return f"- {n} dias depois: ainda nenhum sinal com {n} dias completos."
    texto = (f"- {n} dias depois: {r['no_positivo']} de {r['com_resultado']} no positivo "
             f"(média {var(r['media_pct'])})")
    if r["aguardando"]:
        texto += f"; {r['aguardando']} ainda sem {n} dias"
    return texto + "."


def montar_texto(lista_sinais, dados_acertos, agora):
    inicio = agora - SEMANA
    da_semana = [s for s in lista_sinais if s["quando"] > inicio]
    ini_br, fim_br = em_brasilia(inicio), em_brasilia(agora)
    partes = [f"Relatório semanal do Radar Kraken ({ini_br:%d/%m} a {fim_br:%d/%m/%Y}).", ""]

    if da_semana:
        partes.append(f"Sinais nesta semana: {len(da_semana)}.")
        partes += [_linha_sinal(s) for s in da_semana[:MAX_LINHAS]]
        if len(da_semana) > MAX_LINHAS:
            partes.append(f"- e mais {len(da_semana) - MAX_LINHAS}.")
    else:
        partes.append("Sinais nesta semana: 0 (nenhum gatilho disparou).")
    partes += ["", f"Desde o começo: {len(lista_sinais)} sinal(is)."]

    if lista_sinais:
        partes.append("Se você tivesse comprado no preço de cada sinal:")
        partes += [_linha_prazo(n, dados_acertos["resumo"][str(n)]) for n in acertos.PRAZOS]

    calculado = em_brasilia(de_iso(dados_acertos["calculado_em_utc"]))
    partes += ["", f"Preços da Kraken (fechamento diário), calculados em {calculado:%d/%m/%Y, %H:%M} "
                   f"(Brasília). {FINAL}"]
    return "\n".join(partes)


def relatorio(agora=None, pasta=PASTA_DADOS, enviar_fn=None):
    """Recalcula os acertos, monta o texto e manda (ou só mostra, se `enviar_fn` for None)."""
    agora = agora or datetime.now(timezone.utc).replace(microsecond=0)
    dados = acertos.obter(agora, pasta)
    texto = montar_texto(sinais.ler(pasta), dados, agora)
    if enviar_fn is None:
        print("[sem Telegram configurado] relatório que seria enviado:\n")
        print(texto)
    else:
        enviar_fn(texto)
        print("Relatório semanal enviado no Telegram.")
    return texto


def main():
    cred = telegram.credenciais()
    enviar_fn = (lambda texto: telegram.enviar(texto, *cred)) if cred else None
    try:
        relatorio(enviar_fn=enviar_fn)
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    except telegram.ErroTelegram as erro:
        print(f"Não foi possível falar com o Telegram: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
