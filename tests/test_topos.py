import json
from datetime import datetime, timedelta, timezone

from radar import topos
from radar.ativos import ATIVOS
from tests.conftest import GRAVADO_EM, carregar

AGORA = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)


def _candle(dias_atras, maxima):
    t = int((AGORA - timedelta(days=dias_atras)).replace(hour=0).timestamp())
    return [t, "1", str(maxima), "1", "1", "1", "1", 1]


def test_maxima_de_12_meses_ignora_o_que_e_mais_antigo():
    candles = [_candle(500, 200), _candle(300, 150), _candle(10, 120)]
    t = topos.calcular_topo(candles, AGORA)
    assert t["max_12m_usd"] == 150 and t["max_12m_data"] == (AGORA - timedelta(days=300)).date().isoformat()
    assert t["max_historico_usd"] == 200
    assert t["dias_de_historico"] == 3


def test_sem_candles_nao_ha_topo():
    assert topos.calcular_topo([], AGORA) is None


def test_usa_a_maxima_diaria_dos_candles_gravados(kraken_gravada, tmp_path):
    resultado = topos.obter_topos(agora=GRAVADO_EM, pasta=tmp_path)
    esperado = max(float(c[2]) for c in carregar("ohlc1440_spyx.json")["result"]["SPYx/USD"]
                   if int(c[0]) >= (GRAVADO_EM - timedelta(days=365)).timestamp())
    assert resultado["ativos"]["spx"]["max_12m_usd"] == esperado
    assert set(resultado["ativos"]) == {a["id"] for a in ATIVOS}
    assert json.loads((tmp_path / "topos.json").read_text(encoding="utf-8"))["dia_utc"] == GRAVADO_EM.date().isoformat()


def test_recalcula_so_uma_vez_por_dia(kraken_gravada, tmp_path):
    topos.obter_topos(agora=GRAVADO_EM, pasta=tmp_path)
    assert len(kraken_gravada) == 15
    topos.obter_topos(agora=GRAVADO_EM + timedelta(minutes=5), pasta=tmp_path)
    assert len(kraken_gravada) == 15  # mesmo dia: usou o arquivo
    topos.obter_topos(agora=GRAVADO_EM + timedelta(days=1), pasta=tmp_path)
    assert len(kraken_gravada) == 30  # dia novo: recalculou
