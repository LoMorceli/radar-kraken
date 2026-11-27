"""Envio de mensagens pelo Telegram Bot API (sendMessage).

O token e o chat_id vêm das variáveis de ambiente TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID:
no GitHub, dos segredos do repositório; no seu computador, de um arquivo .env
(que está no .gitignore e nunca vai para o GitHub).

O token é uma senha: ele nunca aparece em mensagens de erro nem na tela.
"""
import os
from pathlib import Path

import requests

ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


class ErroTelegram(Exception):
    pass


def carregar_env(caminho=None):
    """Lê linhas NOME=valor do .env para o ambiente, sem sobrescrever o que já existe."""
    caminho = caminho or ARQUIVO_ENV
    if not Path(caminho).exists():
        return
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


def credenciais():
    """(token, chat_id), ou None se não estiverem configurados."""
    carregar_env()
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    return (token, chat) if token and chat else None


def enviar(texto, token, chat_id, timeout=20):
    """Manda uma mensagem. Levanta ErroTelegram (sem o token no texto) se der errado."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": texto,
                                     "disable_web_page_preview": True}, timeout=timeout)
    except requests.RequestException as erro:
        # a mensagem do requests contém a URL, e a URL contém o token: não repassar
        raise ErroTelegram(f"falha de conexão com o Telegram ({type(erro).__name__})") from None
    try:
        dados = r.json()
    except ValueError:
        dados = {}
    if r.status_code != 200 or not dados.get("ok"):
        raise ErroTelegram(f"o Telegram recusou a mensagem (HTTP {r.status_code}: "
                           f"{dados.get('description', 'sem descrição')})")
    return dados
