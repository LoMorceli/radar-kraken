# Radar Kraken: instruções para o Claude Code

## O que é este projeto
Programa que vigia preços na Kraken e avisa o Lorenzo no celular (Telegram) quando um gatilho de preço é atingido. Ele abastece o painel "Radar de Investimentos (Kraken)", um painel Claude Data que já existe no claude.ai. O painel continua sendo a tela. Este repositório só fornece dados mais rápidos e mais confiáveis.

Hoje o painel é atualizado por uma tarefa agendada do Claude (a cada 2 horas) que lê notícias na web. Os problemas que este projeto resolve:
- preços tirados de notícias, com datas diferentes (alguns com uma semana de atraso);
- gatilhos de preço julgados pelo Claude, em vez de conferidos por código;
- cada execução gasta uso do plano do Lorenzo, mesmo sem novidade;
- nenhum histórico para saber se os sinais acertam.

## Sobre o Lorenzo
- Iniciante: sabe o básico do Claude Code e de programação.
- Investe pela Kraken, com cadastro no Brasil. As xStocks (ações tokenizadas) só aparecem para ele na plataforma global da Kraken.
- Plano: aportes mensais, mantendo os ativos por alguns meses.
- Explique o que fez em português simples, sem jargão sem explicação. Toda mensagem do programa para ele (Telegram, relatórios) é em português do Brasil.

## Regras que não podem ser quebradas
1. **Nunca usar chaves de API da Kraken.** Só os endpoints públicos (`/0/public/...`), que não exigem conta. O programa nunca compra, vende ou move dinheiro. Comprar e vender é sempre decisão manual do Lorenzo, no app.
2. **Nunca colocar segredo no código ou no repositório.** O token do bot do Telegram e o chat_id ficam só em GitHub Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) e, localmente, em um `.env` listado no `.gitignore`.
3. **O repositório é público.** Nada de dado pessoal: sem valores investidos, saldo, nome completo ou e-mail. Só preços, gatilhos e sinais.
4. **Todo aviso diz o motivo com números e data**, por exemplo: "NVDAx a US$ 129,10, 3% acima da mínima de 20/11 (US$ 125,53). Gatilho: perto da mínima sem notícia ruim nova. Confira as notícias antes de decidir." E sempre termina com "Não é recomendação de investimento."
5. **Pergunte antes** de adicionar serviço pago, biblioteca pesada ou qualquer coisa que rode fora do GitHub Actions.

## Stack
- Python 3.12, só `requests` e `pyyaml` (e `pytest` para testes). Nada de pandas, a não ser que o backtest realmente precise; nesse caso, pergunte antes.
- GitHub Actions como agendador (cron a cada 5 minutos, repositório público, minutos ilimitados).
- Estado e histórico em arquivos JSON/CSV na pasta `dados/`.
- Avisos pelo Telegram Bot API (`sendMessage`).

## API da Kraken (já testada em 26/11/2026)
- Cripto: `GET https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD,SOLUSD,XRPUSD,BNBUSD`. As chaves da resposta vêm em outro formato (`XXBTZUSD`, `XETHZUSD`, `SOLUSD`, `XXRPZUSD`, `BNBUSD`). Mapeie pelo `altname` de `/0/public/AssetPairs`, não por string fixa.
- xStocks: precisa de `asset_class=tokenized_asset` e do nome com barra, por exemplo `GET /0/public/Ticker?pair=NVDAx/USD&asset_class=tokenized_asset`. Sem isso a API responde `EQuery:Unknown asset pair`.
- Pares de xStocks confirmados: `AAPLx/USD`, `AMDx/USD`, `AMZNx/USD`, `GOOGLx/USD`, `METAx/USD`, `MSFTx/USD`, `NVDAx/USD`, `QQQx/USD`, `SPYx/USD`, `TSLAx/USD`. Existem também versões `...SPV` e `TQQQx`. Ignore-as.
- Campo do último preço: `c[0]`. Abertura do dia (UTC): `o`. Máxima e mínima de 24h: `h[1]`, `l[1]`.
- `GET /0/public/OHLC?pair=...&interval=1440` devolve até 720 candles diários. Use para calcular máxima de 12 meses e para o backtest. xStocks existem desde meados de 2025, então o histórico delas é menor.
- xStocks negociam 24 horas, 5 dias por semana. No fim de semana o preço fica parado: não trate isso como erro.
- Limite de requisições por IP: agrupe pares numa mesma chamada e trate erro com nova tentativa curta, sem martelar a API.

## Ativos (ids iguais aos do painel)
`btc` XBTUSD · `eth` ETHUSD · `sol` SOLUSD · `xrp` XRPUSD · `bnb` BNBUSD · `nvda` NVDAx/USD · `amd` AMDx/USD · `googl` GOOGLx/USD · `meta` METAx/USD · `msft` MSFTx/USD · `aapl` AAPLx/USD · `amzn` AMZNx/USD · `tsla` TSLAx/USD · `spx` SPYx/USD · `ndx` QQQx/USD

Atenção: no painel, `spx` e `ndx` estão em pontos do índice. Aqui serão o preço dos ETFs SPYx e QQQx em dólares. Gatilhos desses dois devem ser em **percentual abaixo do topo**, nunca em pontos.

## Jeito de trabalhar
- Siga o `PLANO.md`, uma etapa por vez. No fim de cada etapa: testes passando, uma demonstração (rodar e mostrar a saída), commit com mensagem clara em português e um resumo curto para o Lorenzo do que mudou e do que ele precisa fazer.
- Escreva testes com respostas da API gravadas em arquivo (fixtures), para os testes não dependerem da internet.
- Se algo do plano estiver errado ou houver um jeito mais simples, diga antes de mudar.
