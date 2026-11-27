"""Cada regra de config/gatilhos.yaml dispara e não dispara nos casos certos."""
import pytest

from radar import coletar, regras, topos
from radar.ativos import ATIVOS, CRIPTO, XSTOCK
from tests.conftest import GRAVADO_EM

COLETADO = "2026-11-27T13:48:00Z"  # 10:48 de Brasília
REGRAS = regras.carregar_regras()
TOPO_SPY = {"max_12m_usd": 781.78, "max_12m_data": "2026-10-29"}
TOPO_QQQ = {"max_12m_usd": 762.80, "max_12m_data": "2026-10-29"}


def regra(id_ativo, id_regra):
    return next(r for r in REGRAS[id_ativo] if r["id"] == id_regra)


def ativo(ticker, preco, var_pct=None, classe=XSTOCK):
    a = {"ticker": ticker, "preco_usd": preco, "var_pct": var_pct}
    if classe == CRIPTO:
        a |= {"var_ref_desc": "em 24 horas", "var_ref_em": "2026-11-26T13:00:00Z",
              "var_ref_usd": preco / (1 + var_pct / 100) if var_pct is not None else None}
    else:
        a |= {"var_ref_desc": "desde o fechamento de Nova York", "var_ref_em": "2026-11-25T21:00:00Z",
              "var_ref_usd": preco / (1 + var_pct / 100) if var_pct is not None else None}
    return a


def avaliar(id_ativo, id_regra, a, topo=None):
    return regras.avaliar_regra(regra(id_ativo, id_regra), a, topo, COLETADO)


def termina_certo(motivo):
    assert motivo.endswith("Confira as notícias antes de decidir. Não é recomendação de investimento.")
    assert "Preço da Kraken em 27/11/2026, 10:48 (Brasília)." in motivo
    assert "Gatilho: " in motivo


# ---------- o arquivo de regras ----------

def test_arquivo_tem_as_regras_do_painel():
    assert set(REGRAS) == {a["id"] for a in ATIVOS}
    for a in ATIVOS:
        var = regra(a["id"], "variacao")
        assert var["pct"] == (7 if a["classe"] == CRIPTO else 5)
    assert regra("nvda", "preco")["referencia_usd"] == 125.53 and regra("nvda", "preco")["pct"] == 3
    limites = {i: regra(i, "preco")["valor_usd"] for i in ("googl", "meta", "msft", "aapl", "amzn")}
    assert limites == {"googl": 270, "meta": 580, "msft": 475, "aapl": 320, "amzn": 245}
    assert regra("spx", "preco")["tipo"] == regra("ndx", "preco")["tipo"] == "pct_abaixo_topo"
    assert (regra("spx", "preco")["pct"], regra("ndx", "preco")["pct"]) == (10, 20)
    # sem regra de preço: só a variação
    for i in ("btc", "eth", "sol", "xrp", "bnb", "amd", "tsla"):
        assert [r["id"] for r in REGRAS[i]] == ["variacao"]


@pytest.mark.parametrize("conteudo, erro", [
    ("ativos:\n  doge:\n    - {id: preco, tipo: abaixo_de, valor_usd: 1, gatilho: x}\n", "não existem: doge"),
    ("ativos:\n  btc:\n    - {id: preco, tipo: acima_de, valor_usd: 1, gatilho: x}\n", "tipo de regra desconhecido"),
    ("ativos:\n  btc:\n    - {id: preco, tipo: abaixo_de, gatilho: x}\n", "precisa de: valor_usd"),
    ("ativos:\n  btc:\n    - {id: a, tipo: abaixo_de, valor_usd: 1, gatilho: x}\n"
     "    - {id: a, tipo: abaixo_de, valor_usd: 2, gatilho: y}\n", "mesmo id"),
])
def test_arquivo_errado_da_erro_claro(tmp_path, conteudo, erro):
    arquivo = tmp_path / "gatilhos.yaml"
    arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(regras.ErroRegras, match=erro):
        regras.carregar_regras(arquivo)


# ---------- abaixo de um valor (GOOGL, META, MSFT, AAPL, AMZN) ----------

@pytest.mark.parametrize("id_, ticker, limite", [
    ("googl", "GOOGLx", 270), ("meta", "METAx", 580), ("msft", "MSFTx", 475),
    ("aapl", "AAPLx", 320), ("amzn", "AMZNx", 245)])
def test_abaixo_de(id_, ticker, limite):
    assert avaliar(id_, "preco", ativo(ticker, limite - 0.01))["disparou"] is True
    assert avaliar(id_, "preco", ativo(ticker, limite))["disparou"] is False  # exatamente no limite: não
    nao = avaliar(id_, "preco", ativo(ticker, limite * 1.05))
    assert nao["disparou"] is False and nao["falta_pct"] > 0 and "motivo" not in nao


def test_mensagem_abaixo_de():
    r = avaliar("googl", "preco", ativo("GOOGLx", 268.40))
    assert r["motivo"].startswith("GOOGLx a US$ 268,40, abaixo de US$ 270,00 (0,6% abaixo do limite).")
    assert "Gatilho: abaixo de US$ 270 (mínima de 12 meses)." in r["motivo"]
    termina_certo(r["motivo"])


# ---------- até 3% acima da mínima (NVDA) ----------

def test_nvda_ate_3_pct_acima_da_minima():
    limite = 125.53 * 1.03  # US$ 129,2959
    assert avaliar("nvda", "preco", ativo("NVDAx", 129.29))["disparou"] is True
    assert avaliar("nvda", "preco", ativo("NVDAx", 129.30))["disparou"] is False
    assert avaliar("nvda", "preco", ativo("NVDAx", 154.28))["disparou"] is False
    assert avaliar("nvda", "preco", ativo("NVDAx", 120.00))["disparou"] is True  # abaixo da mínima também
    assert avaliar("nvda", "preco", ativo("NVDAx", 150))["limite_usd"] == round(limite, 4)


def test_mensagem_do_exemplo_do_claude_md():
    r = avaliar("nvda", "preco", ativo("NVDAx", 129.10))
    assert r["motivo"].startswith("NVDAx a US$ 129,10, 2,8% acima da mínima de 20/11/2026 (US$ 125,53).")
    assert "Gatilho: perto da mínima sem notícia ruim nova." in r["motivo"]
    termina_certo(r["motivo"])
    abaixo = avaliar("nvda", "preco", ativo("NVDAx", 120.00))
    assert "4,4% abaixo da mínima de 20/11/2026" in abaixo["motivo"]


# ---------- % abaixo da máxima de 12 meses (SPYx, QQQx) ----------

def test_spx_10_pct_abaixo_do_topo():
    # 10% abaixo de US$ 781,78 = US$ 703,602
    assert avaliar("spx", "preco", ativo("SPYx", 703.60), TOPO_SPY)["disparou"] is True
    assert avaliar("spx", "preco", ativo("SPYx", 703.61), TOPO_SPY)["disparou"] is False
    assert avaliar("spx", "preco", ativo("SPYx", 728.20), TOPO_SPY)["disparou"] is False


def test_ndx_20_pct_abaixo_do_topo():
    # 20% abaixo de US$ 762,80 = US$ 610,24
    assert avaliar("ndx", "preco", ativo("QQQx", 610.24), TOPO_QQQ)["disparou"] is True
    assert avaliar("ndx", "preco", ativo("QQQx", 610.25), TOPO_QQQ)["disparou"] is False


def test_mensagem_pct_abaixo_do_topo():
    r = avaliar("spx", "preco", ativo("SPYx", 700.00), TOPO_SPY)
    assert r["motivo"].startswith("SPYx a US$ 700,00, 10,5% abaixo da máxima de 12 meses (US$ 781,78 em 29/10/2026).")
    termina_certo(r["motivo"])


def test_sem_topo_nao_dispara():
    r = avaliar("spx", "preco", ativo("SPYx", 100.00), None)
    assert r["disparou"] is False and r["motivo_sem_dados"]


# ---------- variação: cripto 7% em 24h, ações 5% desde o fechamento de NY ----------

@pytest.mark.parametrize("v, dispara", [(7.0, True), (-7.0, True), (12.3, True), (-9.1, True),
                                        (6.99, False), (-6.99, False), (0, False)])
def test_cripto_7_pct_em_24h(v, dispara):
    assert avaliar("btc", "variacao", ativo("BTC", 61000, v, CRIPTO))["disparou"] is dispara


@pytest.mark.parametrize("v, dispara", [(5.0, True), (-5.0, True), (4.99, False), (-4.99, False)])
def test_acoes_5_pct_desde_o_fechamento(v, dispara):
    assert avaliar("tsla", "variacao", ativo("TSLAx", 390, v))["disparou"] is dispara
    assert avaliar("spx", "variacao", ativo("SPYx", 728, v))["disparou"] is dispara  # ETFs também


def test_mensagens_de_variacao():
    c = avaliar("btc", "variacao", ativo("BTC", 55000, -8.2, CRIPTO))["motivo"]
    assert c.startswith("BTC a US$ 55.000,00, queda de 8,2% em 24 horas (era US$ 59.912,85 em 26/11, 10:00).")
    termina_certo(c)
    a = avaliar("amd", "variacao", ativo("AMDx", 450, 6.1))["motivo"]
    assert a.startswith("AMDx a US$ 450,00, alta de 6,1% desde o fechamento de Nova York de 25/11 (US$ 424,13).")
    termina_certo(a)


def test_sem_referencia_de_variacao_nao_dispara():
    r = avaliar("btc", "variacao", ativo("BTC", 61000, None, CRIPTO))
    assert r["disparou"] is False and r["motivo_sem_dados"]


# ---------- tudo junto, com os preços reais gravados ----------

def test_avalia_todos_os_ativos_com_dados_gravados(kraken_gravada, tmp_path):
    retrato = coletar.coletar(agora=GRAVADO_EM, pasta=tmp_path)
    tops = topos.obter_topos(agora=GRAVADO_EM, pasta=tmp_path)
    resultados = regras.avaliar(retrato, tops, REGRAS)
    assert len(resultados) == 15 + 8  # uma variação por ativo + 8 regras de preço
    spx = next(r for r in resultados if r["id"] == "spx" and r["regra_id"] == "preco")
    assert spx["limite_usd"] == round(tops["ativos"]["spx"]["max_12m_usd"] * 0.9, 4)
    for r in regras.disparados(resultados):
        assert r["motivo"].endswith("Não é recomendação de investimento.")
