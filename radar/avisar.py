"""Decide quais gatilhos viram mensagem no Telegram e guarda o estado em dados/estado.json.

Regras:
- só avisa quando um gatilho MUDA de estado: passa de "não disparado" para "disparado";
- depois de um aviso, o mesmo ativo e a mesma regra ficam 6 horas sem novo aviso;
- se faltar dado para conferir uma regra, o estado dela fica como estava (não inventa mudança);
- se o Telegram falhar, a regra volta a "não disparado" para tentar de novo na próxima execução.
"""
import json
import sys
from datetime import timedelta

from radar.coletar import de_iso, iso
from radar.telegram import ErroTelegram

PAUSA = timedelta(hours=6)


def chave(resultado):
    return f"{resultado['id']}:{resultado['regra_id']}"


def carregar_estado(pasta):
    arquivo = pasta / "estado.json"
    if not arquivo.exists():
        return {}
    return json.loads(arquivo.read_text(encoding="utf-8")).get("regras", {})


def salvar_estado(pasta, estado):
    texto = json.dumps({"regras": dict(sorted(estado.items()))}, indent=1, ensure_ascii=False)
    (pasta / "estado.json").write_text(texto + "\n", encoding="utf-8")


def decidir(resultados, estado, agora):
    """Devolve (resultados que devem virar aviso, novo estado). Não manda nada."""
    avisos, novo = [], dict(estado)
    for r in resultados:
        k = chave(r)
        antes = dict(estado.get(k, {}))
        if r.get("motivo_sem_dados"):
            continue  # sem dados: mantém o estado anterior
        depois = dict(antes)
        depois["disparado"] = bool(r["disparou"])
        if r["disparou"] and not antes.get("disparado"):
            depois["disparou_em_utc"] = iso(agora)
            ultimo = antes.get("ultimo_aviso_utc")
            if ultimo is None or agora - de_iso(ultimo) >= PAUSA:
                avisos.append(r)
        novo[k] = depois
    return avisos, novo


def avisar(resultados, pasta, agora, enviar_fn=None):
    """Manda os avisos e atualiza o estado. Com `enviar_fn=None` só mostra na tela o que
    seria enviado e não grava o estado (modo de teste, sem Telegram configurado).

    Devolve (lista de motivos enviados, True se o estado mudou)."""
    estado = carregar_estado(pasta)
    avisos, novo = decidir(resultados, estado, agora)
    if enviar_fn is None:
        for r in avisos:
            print(f"[sem Telegram configurado] mensagem que seria enviada:\n{r['motivo']}\n")
        return [r["motivo"] for r in avisos], False
    enviados = []
    for r in avisos:
        try:
            enviar_fn(r["motivo"])
        except ErroTelegram as erro:
            print(f"Aviso não enviado ({r['ticker']}): {erro}", file=sys.stderr)
            novo[chave(r)]["disparado"] = False  # tenta de novo na próxima execução
            continue
        novo[chave(r)]["ultimo_aviso_utc"] = iso(agora)
        enviados.append(r["motivo"])
    mudou = novo != estado
    if mudou:
        salvar_estado(pasta, novo)
    return enviados, mudou
