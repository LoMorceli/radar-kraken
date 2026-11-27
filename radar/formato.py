"""Números e datas no formato brasileiro, para a tela e para as mensagens."""


def num(valor, casas=2):
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def usd(valor):
    if valor is None:
        return "—"
    return "US$ " + num(valor, 4 if abs(valor) < 10 else 2)


def var(pct):
    """Variação com sinal: +1,20% / -3,46%."""
    return "—" if pct is None else ("+" if pct > 0 else "") + num(pct) + "%"


def pct(valor, casas=1):
    """Percentual sem sinal: 3,2%."""
    return "—" if valor is None else num(valor, casas) + "%"
