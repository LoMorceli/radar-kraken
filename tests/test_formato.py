from radar.formato import pct, usd, var


def test_formato_brasileiro_dos_numeros():
    assert usd(61586.0) == "US$ 61.586,00"
    assert usd(0.97931) == "US$ 0,9793"
    assert usd(None) == "—"
    assert var(1.2) == "+1,20%"
    assert var(-3.456) == "-3,46%"
    assert var(None) == "—"
    assert pct(2.844) == "2,8%"
