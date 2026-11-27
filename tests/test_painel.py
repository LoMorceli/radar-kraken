import json

from radar import coletar, painel, regras, rodar, topos
from radar.ativos import ATIVOS
from tests.conftest import GRAVADO_EM

CAMPOS_DO_PAINEL = {"id", "preco_usd", "data_preco", "topo_usd", "topo_tipo", "topo_data",
                    "queda_do_topo_pct", "fonte_preco", "fonte_preco_url"}


def _gerar(tmp_path):
    retrato = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    tops = topos.obter_topos(agora=GRAVADO_EM, pasta=tmp_path)
    res = regras.avaliar(retrato, tops, regras.carregar_regras())
    return painel.gravar(retrato, tops, res, tmp_path), tops


def test_tem_os_campos_que_o_painel_usa(kraken_gravada, tmp_path):
    dados, _ = _gerar(tmp_path)
    assert [l["id"] for l in dados["ativos"]] == [a["id"] for a in ATIVOS]
    for linha in dados["ativos"]:
        assert CAMPOS_DO_PAINEL <= set(linha)
        assert linha["fonte_preco"] == "Kraken (API pública)"
        assert linha["queda_do_topo_pct"] >= 0  # sempre positivo, como no painel
    salvo = json.loads((tmp_path / "painel.json").read_text(encoding="utf-8"))
    assert salvo == dados


def test_topo_de_cripto_e_recorde_e_de_acao_e_12_meses(kraken_gravada, tmp_path):
    dados, tops = _gerar(tmp_path)
    linhas = {l["id"]: l for l in dados["ativos"]}
    assert linhas["btc"]["topo_tipo"] == "recorde histórico"
    assert linhas["btc"]["topo_usd"] == tops["ativos"]["btc"]["max_historico_usd"]
    assert linhas["spx"]["topo_tipo"] == "máxima de 12 meses"
    assert linhas["spx"]["topo_usd"] == tops["ativos"]["spx"]["max_12m_usd"]
    spx = linhas["spx"]
    assert spx["queda_do_topo_pct"] == round((1 - spx["preco_usd"] / spx["topo_usd"]) * 100, 1)


def test_data_do_preco_e_a_de_brasilia(kraken_gravada, tmp_path):
    dados, _ = _gerar(tmp_path)
    assert dados["ativos"][0]["data_preco"] == dados["atualizado_em_brasilia"][:10]


def test_endereco_da_fonte_de_cada_ativo():
    assert painel.url_fonte({"par": "XBTUSD", "classe": "cripto"}) == \
        "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
    assert painel.url_fonte({"par": "NVDAx/USD", "classe": "xstock"}) == \
        "https://api.kraken.com/0/public/Ticker?pair=NVDAx%2FUSD&asset_class=tokenized_asset"


def test_gatilhos_vao_junto(kraken_gravada, tmp_path):
    dados, _ = _gerar(tmp_path)
    nvda = next(l for l in dados["ativos"] if l["id"] == "nvda")
    assert {g["regra"] for g in nvda["gatilhos"]} == {"preco", "variacao"}
    assert all("disparou" in g for g in nvda["gatilhos"])


def test_rodada_grava_o_painel(kraken_gravada, tmp_path, monkeypatch):
    from radar import telegram
    monkeypatch.setattr(telegram, "credenciais", lambda: None)
    rodar.rodar(agora=GRAVADO_EM, pasta=tmp_path)
    assert (tmp_path / "painel.json").exists()


def test_nada_pessoal_no_arquivo(kraken_gravada, tmp_path):
    texto = json.dumps(_gerar(tmp_path)[0], ensure_ascii=False).lower()
    for proibido in ("lorenzo", "@", "carteira", "saldo", "quantidade", "r$"):
        assert proibido not in texto
