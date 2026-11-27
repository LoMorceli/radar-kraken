# Teste das regras no passado (backtest)

Gerado em 27/11/2026 com os candles diários da Kraken (API pública). Cada regra do `config/gatilhos.yaml` foi aplicada aos preços de fechamento de cada dia.

## Como ler

- **Disparos**: quantas vezes a regra passou de "não disparada" para "disparada".
- **30 dias / 90 dias**: quanto o preço andou depois de cada disparo, em média, se você tivesse comprado no dia do disparo. Entre parênteses, quantos ficaram no positivo.
- **Comprar todo mês**: a mesma conta para quem compra o mesmo valor todo dia 1º, sem regra nenhuma. É a comparação que importa: **se a regra não for melhor que isso, ela não está ajudando.**
- Com menos de 3 disparos com resultado, não dá para concluir nada.

## Cuidado antes de tirar conclusões

- São poucos dados: cripto tem cerca de 2 anos na Kraken, e as xStocks existem desde agosto de 2025 (AMDx desde janeiro de 2026).
- Os limites de preço (ex.: GOOGLx abaixo de US$ 270) foram escolhidos agora, olhando os preços de agora. Testar esses números no passado é injusto com eles (para mais ou para menos).
- Variação aqui é de um fechamento diário para o seguinte; no radar de verdade, cripto usa 24 horas e ações usam o fechamento de Nova York.
- O que funcionou no passado pode não funcionar no futuro. Use este teste para **descartar regras ruins**, não para ter certeza das boas.

## Resultado por regra

| Ativo | Regra | Disparos | 30 dias depois | 90 dias depois | Comprar todo mês (30 / 90 dias) | Conclusão |
|---|---|---|---|---|---|---|
| BTC | variação de 7% em 1 dia (queda) | 2 | -0,15% (1 de 2 no positivo) | +5,06% (1 de 2 no positivo) | +0,12% / +0,16% | poucos disparos para concluir |
| BTC | variação de 7% em 1 dia (alta) | 4 | +8,86% (3 de 4 no positivo) | +3,91% (2 de 4 no positivo) | +0,12% / +0,16% | melhor que comprar todo mês (90 dias) |
| ETH | variação de 7% em 1 dia (queda) | 18 | -9,68% (4 de 15 no positivo) | +2,32% (7 de 15 no positivo) | +1,03% / +7,21% | não foi melhor que comprar todo mês (90 dias) |
| ETH | variação de 7% em 1 dia (alta) | 21 | +4,30% (11 de 21 no positivo) | +8,93% (10 de 21 no positivo) | +1,03% / +7,21% | melhor que comprar todo mês (90 dias) |
| SOL | variação de 7% em 1 dia (queda) | 20 | +0,56% (10 de 19 no positivo) | -6,28% (8 de 19 no positivo) | -0,23% / -1,86% | não foi melhor que comprar todo mês (90 dias) |
| SOL | variação de 7% em 1 dia (alta) | 22 | +2,92% (9 de 22 no positivo) | -5,39% (9 de 21 no positivo) | -0,23% / -1,86% | não foi melhor que comprar todo mês (90 dias) |
| XRP | variação de 7% em 1 dia (queda) | 15 | +1,45% (6 de 13 no positivo) | -7,42% (4 de 12 no positivo) | -0,70% / -4,43% | não foi melhor que comprar todo mês (90 dias) |
| XRP | variação de 7% em 1 dia (alta) | 22 | -3,06% (7 de 22 no positivo) | -10,32% (6 de 19 no positivo) | -0,70% / -4,43% | não foi melhor que comprar todo mês (90 dias) |
| BNB | variação de 7% em 1 dia (queda) | 6 | -4,34% (1 de 4 no positivo) | -16,19% (0 de 4 no positivo) | +2,79% / +7,42% | não foi melhor que comprar todo mês (90 dias) |
| BNB | variação de 7% em 1 dia (alta) | 5 | -8,75% (1 de 5 no positivo) | -12,26% (1 de 5 no positivo) | +2,79% / +7,42% | não foi melhor que comprar todo mês (90 dias) |
| NVDAx | até 3% acima de US$ 125,53 | 0 | — | — | +1,16% / +3,64% | poucos disparos para concluir |
| NVDAx | variação de 5% em 1 dia (queda) | 11 | +0,21% (2 de 6 no positivo) | +3,64% (5 de 6 no positivo) | +1,16% / +3,64% | não foi melhor que comprar todo mês (90 dias) |
| NVDAx | variação de 5% em 1 dia (alta) | 6 | -1,33% (1 de 5 no positivo) | +3,31% (3 de 5 no positivo) | +1,16% / +3,64% | não foi melhor que comprar todo mês (90 dias) |
| AMDx | variação de 5% em 1 dia (queda) | 13 | +1,23% (3 de 8 no positivo) | +25,73% (4 de 5 no positivo) | +10,69% / +58,31% | não foi melhor que comprar todo mês (90 dias) |
| AMDx | variação de 5% em 1 dia (alta) | 23 | +6,06% (10 de 21 no positivo) | +44,16% (12 de 17 no positivo) | +10,69% / +58,31% | não foi melhor que comprar todo mês (90 dias) |
| GOOGLx | preço abaixo de US$ 270,00 | 1 | +19,92% (1 de 1 no positivo) | +23,78% (1 de 1 no positivo) | +2,75% / +8,85% | poucos disparos para concluir |
| GOOGLx | variação de 5% em 1 dia (queda) | 1 | -7,24% (0 de 1 no positivo) | — | +2,75% / +8,85% | poucos disparos para concluir |
| GOOGLx | variação de 5% em 1 dia (alta) | 9 | +4,17% (5 de 9 no positivo) | +4,54% (4 de 9 no positivo) | +2,75% / +8,85% | não foi melhor que comprar todo mês (90 dias) |
| METAx | preço abaixo de US$ 580,00 | 12 | +10,52% (9 de 11 no positivo) | +12,80% (10 de 11 no positivo) | -0,33% / -1,96% | melhor que comprar todo mês (90 dias) |
| METAx | variação de 5% em 1 dia (queda) | 8 | +4,07% (4 de 7 no positivo) | +1,70% (3 de 6 no positivo) | -0,33% / -1,96% | melhor que comprar todo mês (90 dias) |
| METAx | variação de 5% em 1 dia (alta) | 21 | -2,45% (8 de 19 no positivo) | +0,90% (7 de 16 no positivo) | -0,33% / -1,96% | melhor que comprar todo mês (90 dias) |
| MSFTx | preço abaixo de US$ 475,00 | 6 | -3,42% (3 de 6 no positivo) | -9,61% (1 de 6 no positivo) | +0,49% / +0,11% | não foi melhor que comprar todo mês (90 dias) |
| MSFTx | variação de 5% em 1 dia (queda) | 5 | -0,88% (2 de 4 no positivo) | -1,10% (2 de 4 no positivo) | +0,49% / +0,11% | não foi melhor que comprar todo mês (90 dias) |
| MSFTx | variação de 5% em 1 dia (alta) | 7 | -2,22% (2 de 6 no positivo) | +6,83% (5 de 6 no positivo) | +0,49% / +0,11% | melhor que comprar todo mês (90 dias) |
| AAPLx | preço abaixo de US$ 320,00 | 2 | +3,63% (2 de 2 no positivo) | +10,54% (1 de 1 no positivo) | +2,95% / +7,61% | poucos disparos para concluir |
| AAPLx | variação de 5% em 1 dia (queda) | 3 | +6,04% (2 de 3 no positivo) | +15,44% (3 de 3 no positivo) | +2,95% / +7,61% | melhor que comprar todo mês (90 dias) |
| AAPLx | variação de 5% em 1 dia (alta) | 2 | -3,02% (0 de 1 no positivo) | -8,87% (0 de 1 no positivo) | +2,95% / +7,61% | poucos disparos para concluir |
| AMZNx | preço abaixo de US$ 245,00 | 14 | -0,18% (7 de 13 no positivo) | +2,47% (10 de 13 no positivo) | +1,09% / +2,16% | melhor que comprar todo mês (90 dias) |
| AMZNx | variação de 5% em 1 dia (queda) | 4 | +5,70% (2 de 3 no positivo) | +11,35% (2 de 3 no positivo) | +1,09% / +2,16% | melhor que comprar todo mês (90 dias) |
| AMZNx | variação de 5% em 1 dia (alta) | 12 | +1,34% (6 de 11 no positivo) | -0,92% (4 de 10 no positivo) | +1,09% / +2,16% | não foi melhor que comprar todo mês (90 dias) |
| TSLAx | variação de 5% em 1 dia (queda) | 13 | +2,59% (7 de 11 no positivo) | +0,35% (5 de 11 no positivo) | +2,63% / -1,42% | melhor que comprar todo mês (90 dias) |
| TSLAx | variação de 5% em 1 dia (alta) | 15 | -0,39% (7 de 13 no positivo) | +1,45% (5 de 10 no positivo) | +2,63% / -1,42% | melhor que comprar todo mês (90 dias) |
| SPYx | 10% abaixo da máxima de 12 meses | 2 | +13,19% (1 de 1 no positivo) | +16,44% (1 de 1 no positivo) | +1,24% / +3,86% | poucos disparos para concluir |
| SPYx | variação de 5% em 1 dia (queda) | 0 | — | — | +1,24% / +3,86% | poucos disparos para concluir |
| SPYx | variação de 5% em 1 dia (alta) | 0 | — | — | +1,24% / +3,86% | poucos disparos para concluir |
| QQQx | 20% abaixo da máxima de 12 meses | 1 | +17,85% (1 de 1 no positivo) | +27,59% (1 de 1 no positivo) | +1,37% / +4,82% | poucos disparos para concluir |
| QQQx | variação de 5% em 1 dia (queda) | 1 | — | — | +1,37% / +4,82% | poucos disparos para concluir |
| QQQx | variação de 5% em 1 dia (alta) | 0 | — | — | +1,37% / +4,82% | poucos disparos para concluir |

## Período de cada ativo

- BTC: 07/12/2024 a 27/11/2026.
- ETH: 07/12/2024 a 27/11/2026.
- SOL: 07/12/2024 a 27/11/2026.
- XRP: 07/12/2024 a 27/11/2026.
- BNB: 22/04/2025 a 27/11/2026.
- NVDAx: 12/08/2025 a 27/11/2026.
- AMDx: 16/01/2026 a 27/11/2026.
- GOOGLx: 14/08/2025 a 27/11/2026.
- METAx: 27/08/2025 a 27/11/2026.
- MSFTx: 27/08/2025 a 27/11/2026.
- AAPLx: 14/08/2025 a 27/11/2026.
- AMZNx: 02/09/2025 a 27/11/2026.
- TSLAx: 12/08/2025 a 27/11/2026.
- SPYx: 14/08/2025 a 27/11/2026.
- QQQx: 02/09/2025 a 27/11/2026.

Resultado passado não garante resultado futuro. Não é recomendação de investimento.
