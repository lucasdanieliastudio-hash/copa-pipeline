# Spec — Etapa 1: Ingestão (raw)

## Contexto

Pipeline de dados em Python sobre o banco de dados das Copas do Mundo masculinas
(1930–2022) e femininas (1991–2019), de Joshua C. Fjelstul (CC-BY-SA 4.0).
Esta spec é a fonte da verdade da etapa 1: o código é consequência dela.

## Stack

- Python 3.13, dependências com uv
- pandas para ler os arquivos
- DuckDB como banco, arquivo `copa.duckdb` na raiz do projeto
- Sem orquestrador: script executável pela linha de comando

## Decisões fechadas antes do código

| # | Decisão | Escolha | Motivo |
|---|---|---|---|
| 1 | Quais tabelas | As 27 da fonte | Espelho completo: se uma pergunta nova surgir, o dado já está no banco e a raw continua sendo a cópia fiel da origem. |
| 2 | Nome das tabelas | Traduzido para português; colunas mantêm o nome original | O nome da tabela vai ser escrito de memória em todo JOIN, e em português ele é mais legível. Coluna não é traduzida porque isso já seria transformação. |
| 3 | Formato no repositório | `.csv.gz` com o mesmo nome do arquivo de origem | 12 MB viram 1,9 MB e o pandas/DuckDB leem gzip direto. Compactar não altera o conteúdo (conferido byte a byte com `cmp`). |
| 4 | Tipos | Tudo texto (`dtype=str`) | Conversão de tipo é decisão da refined. Na raw, data continua texto. |
| 5 | Nulos | Só célula vazia vira nulo (`keep_default_na=False`, `na_values=[""]`) | O padrão do pandas transforma textos como `NA`, `None` e `null` em nulo. Num dataset com códigos de país e nomes de pessoas, isso apagaria valores reais sem avisar. |
| 6 | Proibido nesta etapa | Converter tipo, descartar linha, renomear coluna, deduplicar | Qualquer correção aqui torna a raw diferente da fonte e esconde o problema da etapa que deveria tratá-lo. |
| 7 | Reexecução | `CREATE OR REPLACE TABLE`; rodar duas vezes dá o mesmo resultado | Qualquer etapa precisa poder ser rodada de novo do zero sem quebrar. |

## Mapa arquivo → tabela

| Arquivo em `raw/` | Tabela | Linhas esperadas |
|---|---|---:|
| `award_winners.csv.gz` | `raw.premiados` | 200 |
| `awards.csv.gz` | `raw.premios` | 8 |
| `bookings.csv.gz` | `raw.cartoes` | 3.178 |
| `confederations.csv.gz` | `raw.confederacoes` | 6 |
| `goals.csv.gz` | `raw.gols` | 3.637 |
| `group_standings.csv.gz` | `raw.classificacao_grupos` | 626 |
| `groups.csv.gz` | `raw.grupos` | 159 |
| `host_countries.csv.gz` | `raw.paises_sede` | 31 |
| `manager_appearances.csv.gz` | `raw.tecnicos_partidas` | 2.538 |
| `manager_appointments.csv.gz` | `raw.tecnicos_torneios` | 637 |
| `managers.csv.gz` | `raw.tecnicos` | 475 |
| `matches.csv.gz` | `raw.partidas` | 1.248 |
| `penalty_kicks.csv.gz` | `raw.cobrancas_penaltis` | 396 |
| `player_appearances.csv.gz` | `raw.jogadores_partidas` | 27.432 |
| `players.csv.gz` | `raw.jogadores` | 10.401 |
| `qualified_teams.csv.gz` | `raw.selecoes_classificadas` | 625 |
| `referee_appearances.csv.gz` | `raw.arbitros_partidas` | 1.248 |
| `referee_appointments.csv.gz` | `raw.arbitros_torneios` | 668 |
| `referees.csv.gz` | `raw.arbitros` | 493 |
| `squads.csv.gz` | `raw.elencos` | 13.843 |
| `stadiums.csv.gz` | `raw.estadios` | 240 |
| `substitutions.csv.gz` | `raw.substituicoes` | 10.222 |
| `team_appearances.csv.gz` | `raw.selecoes_partidas` | 2.496 |
| `teams.csv.gz` | `raw.selecoes` | 88 |
| `tournament_stages.csv.gz` | `raw.fases_torneio` | 155 |
| `tournament_standings.csv.gz` | `raw.classificacao_final` | 120 |
| `tournaments.csv.gz` | `raw.torneios` | 30 |

As contagens esperadas foram tiradas lendo cada CSV com o módulo `csv` do Python
(e conferidas com a contagem de quebras de linha, que deu igual em todos).

## Artefatos

1. `pipeline/db.py` — conexão compartilhada pelas etapas:
   - `PASTA_RAW`, `CAMINHO_BANCO`: resolvidos a partir da localização do próprio arquivo, nunca do diretório corrente.
   - `conectar(caminho=CAMINHO_BANCO)`: abre o banco, criando se faltar.
   - `criar_schema(con, nome)`: `CREATE SCHEMA IF NOT EXISTS`.
   - `gravar(con, df, schema, tabela)`: grava e devolve a contagem **lida do banco**.
   - Nome de schema e de tabela só aceita letras minúsculas, números e `_` (evita SQL injection por nome).
2. `pipeline/ingestao.py` — executável com `uv run python -m pipeline.ingestao`:
   - Confere que `raw/` tem exatamente os 27 arquivos do mapa (nem falta, nem sobra).
   - Para cada arquivo: lê, grava em `raw.<tabela>`, compara a contagem do arquivo com a do banco e para com erro se divergir.
   - Imprime uma linha por tabela: `✓ raw.partidas          1.248 linhas` (milhar com ponto), e o total no fim.
   - Saída em UTF-8 mesmo no terminal do Windows.

## Critérios de aceite

- As 27 contagens na tela batem com a tabela acima.
- Rodar a ingestão duas vezes seguidas dá o mesmo resultado, sem erro.
- Um arquivo a mais ou a menos em `raw/` faz a ingestão parar com mensagem clara, antes de gravar qualquer coisa.
