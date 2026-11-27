import pytest
import requests

from radar import telegram

TOKEN = "123456:SEGREDO-NAO-PODE-APARECER"


class Resposta:
    def __init__(self, status, dados):
        self.status_code, self._dados = status, dados

    def json(self):
        return self._dados


def test_manda_a_mensagem(monkeypatch):
    pedidos = []

    def post(url, json, timeout):
        pedidos.append((url, json))
        return Resposta(200, {"ok": True, "result": {"message_id": 1}})

    monkeypatch.setattr(telegram.requests, "post", post)
    telegram.enviar("Olá", TOKEN, "999")
    url, corpo = pedidos[0]
    assert url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert corpo["chat_id"] == "999" and corpo["text"] == "Olá"


def test_erro_de_conexao_nao_mostra_o_token(monkeypatch):
    def post(url, json, timeout):
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}")

    monkeypatch.setattr(telegram.requests, "post", post)
    with pytest.raises(telegram.ErroTelegram) as erro:
        telegram.enviar("Olá", TOKEN, "999")
    assert TOKEN not in str(erro.value) and "SEGREDO" not in str(erro.value)


def test_token_errado_da_erro_claro(monkeypatch):
    monkeypatch.setattr(telegram.requests, "post",
                        lambda url, json, timeout: Resposta(401, {"ok": False, "description": "Unauthorized"}))
    with pytest.raises(telegram.ErroTelegram, match="HTTP 401: Unauthorized") as erro:
        telegram.enviar("Olá", TOKEN, "999")
    assert TOKEN not in str(erro.value)


def test_le_o_env_sem_sobrescrever(monkeypatch, tmp_path):
    arquivo = tmp_path / ".env"
    arquivo.write_text("# comentário\nTELEGRAM_BOT_TOKEN=abc\nTELEGRAM_CHAT_ID=\"42\"\n", encoding="utf-8")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "já-existia")
    monkeypatch.setattr(telegram, "ARQUIVO_ENV", arquivo)
    assert telegram.credenciais() == ("abc", "já-existia")


def test_sem_credenciais(monkeypatch, tmp_path):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(telegram, "ARQUIVO_ENV", tmp_path / "nao-existe")
    assert telegram.credenciais() is None
