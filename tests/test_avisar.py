import json
from datetime import datetime, timedelta, timezone

from radar import avisar
from radar.telegram import ErroTelegram

T0 = datetime(2026, 11, 27, 14, 0, tzinfo=timezone.utc)


def res(disparou, id_="googl", regra_id="preco", sem_dados=False):
    r = {"id": id_, "ticker": id_.upper() + "x", "regra_id": regra_id, "tipo": "abaixo_de",
         "disparou": disparou, "motivo": f"{id_} disparou. Não é recomendação de investimento."}
    if sem_dados:
        r["motivo_sem_dados"] = "sem dados"
    return r


def test_avisa_quando_passa_a_disparar():
    avisos, estado = avisar.decidir([res(True)], {}, T0)
    assert len(avisos) == 1
    assert estado["googl:preco"]["disparado"] is True


def test_nao_repete_enquanto_continua_disparado():
    _, estado = avisar.decidir([res(True)], {}, T0)
    estado["googl:preco"]["ultimo_aviso_utc"] = "2026-11-27T14:00:00Z"
    avisos, _ = avisar.decidir([res(True)], estado, T0 + timedelta(minutes=5))
    assert avisos == []


def test_nao_avisa_quem_nao_disparou():
    avisos, estado = avisar.decidir([res(False)], {}, T0)
    assert avisos == [] and estado["googl:preco"]["disparado"] is False


def test_pausa_de_6_horas_por_ativo_e_regra():
    estado = {"googl:preco": {"disparado": True, "ultimo_aviso_utc": "2026-11-27T14:00:00Z"}}
    _, estado = avisar.decidir([res(False)], estado, T0 + timedelta(hours=1))  # saiu do gatilho
    # voltou a disparar 2 horas depois do aviso: dentro da pausa, sem mensagem
    avisos, estado = avisar.decidir([res(True)], estado, T0 + timedelta(hours=2))
    assert avisos == [] and estado["googl:preco"]["disparado"] is True
    # saiu e voltou depois de 6 horas: avisa de novo
    _, estado = avisar.decidir([res(False)], estado, T0 + timedelta(hours=5))
    avisos, _ = avisar.decidir([res(True)], estado, T0 + timedelta(hours=6))
    assert len(avisos) == 1


def test_pausa_e_separada_por_regra():
    estado = {"googl:preco": {"disparado": False, "ultimo_aviso_utc": "2026-11-27T14:00:00Z"}}
    avisos, _ = avisar.decidir([res(True, regra_id="variacao")], estado, T0 + timedelta(minutes=5))
    assert len(avisos) == 1  # a pausa da regra de preço não segura a regra de variação


def test_sem_dados_mantem_o_estado():
    estado = {"googl:preco": {"disparado": True}}
    avisos, novo = avisar.decidir([res(False, sem_dados=True)], estado, T0)
    assert avisos == [] and novo == estado


def test_avisar_manda_e_grava_o_estado(tmp_path):
    mandadas = []
    enviados, mudou = avisar.avisar([res(True), res(False, id_="meta")], tmp_path, T0, mandadas.append)
    assert mandadas == enviados == [res(True)["motivo"]] and mudou
    salvo = json.loads((tmp_path / "estado.json").read_text(encoding="utf-8"))["regras"]
    assert salvo["googl:preco"] == {"disparado": True, "disparou_em_utc": "2026-11-27T14:00:00Z",
                                    "ultimo_aviso_utc": "2026-11-27T14:00:00Z"}
    # rodada seguinte igual: nada enviado e o arquivo não muda (não gera commit)
    antes = (tmp_path / "estado.json").read_text(encoding="utf-8")
    enviados, mudou = avisar.avisar([res(True), res(False, id_="meta")], tmp_path,
                                    T0 + timedelta(minutes=5), mandadas.append)
    assert enviados == [] and mudou is False
    assert (tmp_path / "estado.json").read_text(encoding="utf-8") == antes


def test_se_o_telegram_falha_tenta_de_novo_na_proxima(tmp_path):
    def falha(texto):
        raise ErroTelegram("fora do ar")

    enviados, _ = avisar.avisar([res(True)], tmp_path, T0, falha)
    assert enviados == []
    mandadas = []
    enviados, _ = avisar.avisar([res(True)], tmp_path, T0 + timedelta(minutes=5), mandadas.append)
    assert len(mandadas) == 1


def test_sem_telegram_so_mostra_e_nao_grava(tmp_path, capsys):
    enviados, mudou = avisar.avisar([res(True)], tmp_path, T0, None)
    assert len(enviados) == 1 and mudou is False
    assert not (tmp_path / "estado.json").exists()
    assert "mensagem que seria enviada" in capsys.readouterr().out
