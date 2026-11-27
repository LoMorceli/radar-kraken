from datetime import timedelta

import pytest

from radar import regras, rodar, telegram
from tests.conftest import GRAVADO_EM


@pytest.fixture
def telegram_falso(monkeypatch):
    mandadas = []
    monkeypatch.setattr(telegram, "credenciais", lambda: ("TOKEN", "CHAT"))
    monkeypatch.setattr(telegram, "enviar", lambda texto, token, chat: mandadas.append(texto))
    return mandadas


def test_publica_precos_no_maximo_a_cada_30_minutos():
    assert rodar.deve_publicar_precos(None, GRAVADO_EM) is True
    assert rodar.deve_publicar_precos(GRAVADO_EM, GRAVADO_EM + timedelta(minutes=10)) is False
    assert rodar.deve_publicar_precos(GRAVADO_EM, GRAVADO_EM + timedelta(minutes=30)) is True


def test_mensagem_de_teste(kraken_gravada, telegram_falso, tmp_path, monkeypatch):
    saida = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(saida))
    assert rodar.rodar(teste=True, agora=GRAVADO_EM, pasta=tmp_path) == 0
    assert telegram_falso[0] == rodar.TEXTO_TESTE
    assert telegram_falso[0].startswith("Radar Kraken ligado.")
    assert telegram_falso[0].endswith("Não é recomendação de investimento.")
    assert "publicar_precos=true" in saida.read_text(encoding="utf-8")


def test_teste_sem_telegram_configurado_falha(kraken_gravada, monkeypatch, tmp_path):
    monkeypatch.setattr(telegram, "credenciais", lambda: None)
    assert rodar.rodar(teste=True, agora=GRAVADO_EM, pasta=tmp_path) == 1


def test_gatilho_disparado_vira_um_aviso_so(kraken_gravada, telegram_falso, tmp_path, monkeypatch):
    # só uma regra de mentira, que dispara com qualquer preço da GOOGLx (as respostas gravadas
    # usam os candles de um ativo só, então as variações dos outros não servem aqui)
    falsas = {i: [] for i in regras.carregar_regras()}
    falsas["googl"] = [{"id": "preco", "tipo": "abaixo_de", "valor_usd": 100000,
                        "gatilho": "teste"}]
    monkeypatch.setattr(regras, "carregar_regras", lambda: falsas)
    rodar.rodar(agora=GRAVADO_EM, pasta=tmp_path)
    assert len(telegram_falso) == 1 and telegram_falso[0].startswith("GOOGLx a US$ ")
    rodar.rodar(agora=GRAVADO_EM + timedelta(minutes=5), pasta=tmp_path)
    assert len(telegram_falso) == 1  # continua disparado: não repete
