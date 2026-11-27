"""Uma rodada completa do Radar Kraken: coleta, topos, gatilhos e avisos.

    python -m radar.rodar            # rodada normal (é o que o GitHub roda a cada 5 minutos)
    python -m radar.rodar --teste    # manda "Radar Kraken ligado" no Telegram e depois faz a rodada

Sem TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID configurados, só mostra na tela o que mandaria.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from radar import avisar, coletar, kraken, regras, telegram, topos

PUBLICAR_PRECOS_A_CADA = timedelta(minutes=30)
TEXTO_TESTE = ("Radar Kraken ligado. A partir de agora eu confiro os gatilhos de preço da Kraken "
               "a cada 5 minutos (o GitHub pode atrasar de 5 a 30 minutos) e aviso aqui quando algum "
               "disparar, sempre com o motivo, os números e a data. Comprar ou vender continua sendo "
               "decisão sua, no app. Não é recomendação de investimento.")


def _coletado_antes(pasta):
    """Horário da coleta que estava em dados/precos.json antes desta rodada (None se não houver)."""
    arquivo = pasta / "precos.json"
    if not arquivo.exists():
        return None
    try:
        return coletar.de_iso(json.loads(arquivo.read_text(encoding="utf-8"))["coletado_em_utc"])
    except (ValueError, KeyError):
        return None


def deve_publicar_precos(antes, agora):
    """Os preços vão para o GitHub no máximo a cada 30 minutos (para não encher de commits)."""
    return antes is None or agora - antes >= PUBLICAR_PRECOS_A_CADA


def _saida_github(nome, valor):
    """Passa um valor para os próximos passos do workflow do GitHub Actions."""
    caminho = os.environ.get("GITHUB_OUTPUT")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"{nome}={valor}\n")


def rodar(teste=False, agora=None, pasta=coletar.PASTA_DADOS):
    agora = agora or datetime.now(timezone.utc).replace(microsecond=0)
    cred = telegram.credenciais()
    enviar_fn = (lambda texto: telegram.enviar(texto, *cred)) if cred else None

    if teste:
        if not enviar_fn:
            print("Para a mensagem de teste, configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.", file=sys.stderr)
            return 1
        enviar_fn(TEXTO_TESTE)
        print("Mensagem de teste enviada: 'Radar Kraken ligado'.")

    antes = _coletado_antes(pasta)
    retrato = coletar.coletar(agora=agora, pasta=pasta)
    tops = topos.obter_topos(agora=agora, pasta=pasta)
    resultados = regras.avaliar(retrato, tops, regras.carregar_regras())
    enviados, estado_mudou = avisar.avisar(resultados, pasta, agora, enviar_fn)

    publicar = deve_publicar_precos(antes, agora)
    _saida_github("publicar_precos", "true" if publicar else "false")

    disparados = regras.disparados(resultados)
    print(f"Rodada de {coletar.iso(agora)}: {len(retrato['ativos'])} preços, "
          f"{len(disparados)} gatilho(s) disparado(s), {len(enviados)} aviso(s) "
          f"{'enviado(s)' if enviar_fn else 'que seriam enviados (sem Telegram)'}.")
    if disparados:
        print("Disparados agora: " + ", ".join(f"{r['ticker']} ({r['tipo']})" for r in disparados))
    print(f"Preços vão para o GitHub nesta rodada: {'sim' if publicar else 'não (última publicação há menos de 30 min)'}.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Rodada do Radar Kraken")
    p.add_argument("--teste", action="store_true", help="manda a mensagem 'Radar Kraken ligado'")
    args = p.parse_args(argv)
    try:
        return rodar(teste=args.teste)
    except kraken.ErroKraken as erro:
        print(f"Não foi possível falar com a Kraken: {erro}", file=sys.stderr)
        return 1
    except telegram.ErroTelegram as erro:
        print(f"Não foi possível falar com o Telegram: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
