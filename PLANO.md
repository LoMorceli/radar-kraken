# Plano do projeto: Radar Kraken

Ordem pensada para você ter algo útil já na Etapa 3 (avisos de preço no celular) e só depois investir em histórico e testes.

---

## Etapa 0: Preparação (feita pelo Lorenzo, uns 15 minutos)
1. No GitHub, crie um repositório **público** chamado `radar-kraken`, com README.
2. No Telegram, fale com **@BotFather**, mande `/newbot` e guarde o **token** que ele devolve.
3. Mande qualquer mensagem para o seu bot novo. Depois abra `https://api.telegram.org/bot<TOKEN>/getUpdates` no navegador e anote o número em `"chat":{"id": ...}`. Esse é o seu **chat_id**.
4. No repositório: Settings › Secrets and variables › Actions › New repository secret. Crie `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.
5. Coloque `CLAUDE.md` e `PLANO.md` na raiz do repositório.

**Pronto quando:** os dois segredos aparecem na lista e os dois arquivos estão no repositório.

---

## Etapa 1: Coletor de preços da Kraken
- `radar/kraken.py`: busca o Ticker de todos os 15 ativos (cripto e xStocks, em chamadas separadas por classe) e devolve, para cada id, o último preço, a abertura do dia e a máxima e a mínima de 24h.
- `radar/coletar.py`: grava `dados/precos.json` (último retrato, com horário em UTC e em Brasília) e acrescenta uma linha por ativo em `dados/historico.csv`.
- Testes com respostas gravadas da API.

**Pronto quando:** `python -m radar.coletar` mostra os 15 preços na tela e cria os dois arquivos.

## Etapa 2: Gatilhos de preço em código
- `config/gatilhos.yaml` com uma regra por ativo, partindo dos gatilhos de preço que já estão no painel:
  - `nvda`: avisar se o preço ficar até 3% acima de US$ 125,53 (mínima de 20/11/2026);
  - `googl`: abaixo de US$ 270; `meta`: abaixo de US$ 580; `msft`: abaixo de US$ 475; `aapl`: abaixo de US$ 320; `amzn`: abaixo de US$ 245;
  - `spx` (SPYx): 10% ou mais abaixo da máxima de 12 meses; `ndx` (QQQx): 20% ou mais abaixo da máxima de 12 meses;
  - todas as criptos: variação de 7% ou mais em 24 horas, para cima ou para baixo;
  - todas as ações: variação de 5% ou mais no dia.
- `radar/topos.py`: calcula a máxima de 12 meses pelos candles diários (OHLC) e guarda em `dados/topos.json`, recalculado uma vez por dia.
- `radar/regras.py`: compara os preços com as regras e devolve os gatilhos disparados, cada um com o motivo em português e os números.
- Gatilhos que não são de preço (fluxo dos ETFs, decisões do Fed, notícias) **continuam com a tarefa agendada do Claude**. Não tente fazer isso aqui.

**Pronto quando:** os testes provam que cada regra dispara e não dispara nos casos certos.

## Etapa 3: Agendamento e avisos no Telegram
- `.github/workflows/radar.yml`: cron `*/5 * * * *` e também `workflow_dispatch` (para rodar na mão).
- `radar/avisar.py`: manda a mensagem pelo Telegram só quando um gatilho **muda de estado** (passa de não disparado para disparado). Pausa de 6 horas por ativo e por regra, para não repetir o mesmo aviso. O estado fica em `dados/estado.json`.
- Commit dos arquivos de `dados/` só quando algo mudou, para não encher o repositório de commits iguais.
- Mensagem de teste: um comando que manda "Radar Kraken ligado" para conferir o Telegram.

**Pronto quando:** você roda o workflow na mão, recebe a mensagem de teste no celular e vê as execuções automáticas a cada 5 a 15 minutos na aba Actions.

**Saiba que:** o GitHub não garante o horário exato. Execuções podem atrasar de 5 a 30 minutos quando os servidores estão cheios, e agendamentos pausam se o repositório ficar 60 dias sem atividade. Os commits de dados contam como atividade, mas confira a aba Actions de vez em quando.

## Etapa 4: Ligação com o painel do claude.ai
- `radar/painel.py`: gera `dados/painel.json` com os campos que o painel já usa (`id`, `preco_usd`, `data_preco`, `topo_usd`, `topo_tipo`, `topo_data`, `queda_do_topo_pct` positivo, `fonte_preco` = "Kraken (API pública)", `fonte_preco_url`).
- O endereço público fica `https://raw.githubusercontent.com/<seu-usuario>/radar-kraken/main/dados/painel.json`.
- **Depois desta etapa, volte ao Cowork**, mande esse endereço e peça para eu mudar a tarefa agendada: ela passa a ler os preços desse arquivo e só pesquisa notícias, fluxo de ETFs e juros na web. Também dá para espaçar a tarefa (por exemplo, a cada 6 horas), porque os preços já chegam pelo GitHub, e isso economiza uso do seu plano.

**Pronto quando:** o arquivo abre no navegador pelo endereço acima.

## Etapa 5: Histórico de sinais e taxa de acerto
- Cada aviso enviado vira uma linha em `dados/sinais.csv`: data, ativo, regra, preço no momento e motivo.
- `radar/acertos.py`: calcula quanto o preço andou 7, 30 e 90 dias depois de cada sinal e gera `dados/acertos.json`.
- Relatório semanal no Telegram (domingo à noite): quantos sinais saíram, quantos teriam dado lucro e de quanto.

**Pronto quando:** o relatório semanal chega com números, mesmo que no começo existam poucos sinais.

## Etapa 6: Teste das regras no passado (backtest)
- `radar/backtest.py`: aplica as regras do `gatilhos.yaml` aos candles diários da Kraken (até 720 dias) e mostra, por regra, quantas vezes ela teria disparado e o resultado 30 e 90 dias depois.
- Mostra também o resultado de simplesmente comprar todo mês o mesmo valor, para comparar. Se a regra não for melhor que isso, ela não está ajudando.
- Saída em `relatorios/backtest.md`, em português simples.

**Cuidado:** são poucos anos de dados e as xStocks têm pouco histórico. O que funcionou no passado pode não funcionar no futuro. Use o teste para descartar regras ruins, não para ter certeza das boas.

## Etapa 7 (opcional): O que os grandes investidores estão fazendo
- Rodar uma vez por dia, em outro workflow.
- Formulário 4 da SEC (diretores comprando ou vendendo ações da própria empresa) para as 8 empresas da lista, e Formulário 13F (carteiras de fundos com mais de US$ 100 milhões) de uma lista curta de fundos escolhidos por você.
- Usar a API gratuita da SEC (`data.sec.gov`), que exige um `User-Agent` com nome e e-mail de contato. Ponha o e-mail num segredo, não no código.
- Avisar no Telegram só compras relevantes de diretores (por exemplo, acima de US$ 1 milhão).

## Etapa 8 (opcional e paga): tempo real de verdade
- Só se, depois de usar as etapas anteriores, os 5 a 30 minutos de atraso realmente fizerem falta.
- Um servidor sempre ligado (cerca de US$ 5 por mês) ligado ao WebSocket da Kraken avisa em segundos.
- Para quem aporta todo mês e segura por meses, isso dificilmente compensa. Decida com base no histórico da Etapa 5.
