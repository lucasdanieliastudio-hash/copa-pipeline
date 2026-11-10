# Pipeline das Copas do Mundo

Pipeline de dados em Python, SQL e DuckDB sobre todas as Copas do Mundo da FIFA:
22 masculinas (1930–2022) e 8 femininas (1991–2019). O dado vai do arquivo de
origem até indicadores que respondem perguntas sobre seleções, gols e pênaltis,
passando por três camadas separadas: `raw`, `refined` e `marts`.

> Desafio final da Trilha de Engenharia de Dados JR (Instituto NTA).
> **Status:** etapa 1 de 5 concluída (ingestão).

## Fonte do dado e licença

- **Fonte:** The Fjelstul World Cup Database — <https://github.com/jfjelstul/worldcup>
  (pasta `data-csv/`, versão do commit `35a8667`, de 11/06/2026).
- **Autor:** Joshua C. Fjelstul, Ph.D. — © 2023 Joshua C. Fjelstul, Ph.D.
- **Licença:** [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode).
  Permite uso público, inclusive em repositório aberto, com atribuição. Por isso
  os dados derivados deste repositório (tabelas das camadas `refined` e `marts`)
  também ficam sob CC-BY-SA 4.0.
- **Modificações feitas na cópia:** os 27 CSVs foram compactados com gzip (conteúdo
  idêntico, conferido byte a byte) e, no banco, as tabelas recebem nomes em
  português. Nenhum valor foi alterado na camada `raw`.

## Perguntas que o projeto responde

1. **Ranking de aproveitamento:** quais seleções têm mais vitórias e melhor aproveitamento na história das Copas?
2. **Fator casa:** o país-sede vai mais longe quando joga em casa do que nas Copas que disputa fora?
3. **Força das confederações:** Europa, América do Sul e o resto do mundo — quem ganha mais jogos e títulos?
4. **Minuto dos gols:** em que momento do jogo os gols saem, incluindo acréscimos e prorrogação?
5. **Artilheiros:** quem mais marcou, quantos gols foram de pênalti e quantos foram contra?
6. **Disputas de pênaltis:** quem mais vence nos pênaltis e qual a taxa de conversão das cobranças?

Copas masculinas e femininas entram no projeto, sempre separadas nos indicadores:
a campanha do Brasil masculino e a do Brasil feminino nunca são somadas. Como as
duas usam o mesmo `team_id`, a separação vem do torneio (masculino ou feminino),
não da seleção.

## Camadas

| Camada | Onde | O que é | Etapa |
|---|---|---|---|
| `raw` | schema `raw` no `copa.duckdb` | Espelho fiel dos 27 CSVs: tudo texto, nenhuma linha removida, colunas com o nome original | 1 ✅ |
| `refined` | schema `refined` | Dado tipado, padronizado e conferido, ainda no grão original | 2 |
| `marts` | schema `marts`, um `.sql` por indicador em `sql/marts/` | Tabelas agregadas, uma por pergunta | 3 |

## O que é uma linha de cada tabela (camada raw)

As 27 tabelas e suas contagens estão em [`specs/ingestao.md`](specs/ingestao.md).
As que as perguntas usam:

| Tabela | Uma linha é | Linhas |
|---|---|---:|
| `raw.torneios` | uma Copa | 30 |
| `raw.partidas` | um jogo | 1.248 |
| `raw.selecoes_partidas` | uma seleção em um jogo (cada jogo aparece duas vezes, uma por lado) | 2.496 |
| `raw.selecoes` | um país/federação. A seleção masculina e a feminina do mesmo país são **a mesma linha** (ex.: Brasil = `T-09`, com `mens_team` e `womens_team` iguais a 1); 33 das 88 seleções são assim | 88 |
| `raw.confederacoes` | uma confederação continental | 6 |
| `raw.paises_sede` | um país-sede em uma Copa (2002 teve dois: Coreia do Sul e Japão) | 31 |
| `raw.selecoes_classificadas` | uma seleção em uma Copa, com a fase que alcançou | 625 |
| `raw.gols` | um gol | 3.637 |
| `raw.jogadores` | um jogador ou jogadora | 10.401 |
| `raw.cobrancas_penaltis` | uma cobrança em disputa de pênaltis | 396 |

Conferência de consistência: `raw.selecoes_partidas` tem exatamente o dobro de
linhas de `raw.partidas` (2 × 1.248 = 2.496), como esperado.

## Como rodar do zero

Pré-requisito: [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado.

```bash
git clone https://github.com/lucasdanieliastudio-hash/copa-pipeline.git
cd copa-pipeline
uv sync                                  # cria o ambiente com as versões do uv.lock
uv run python -m pipeline.ingestao       # etapa 1: CSV -> schema raw
```

A ingestão imprime uma linha por tabela e termina com
`27 tabelas, 81.200 linhas no total.` Se algum número não bater com a tabela de
[`specs/ingestao.md`](specs/ingestao.md), a ingestão está errada: não siga para a
próxima etapa.

## Decisões sobre o dado

Cada decisão da etapa 1, com o motivo, está na tabela de
[`specs/ingestao.md`](specs/ingestao.md#decisões-fechadas-antes-do-código).
Resumo: todas as 27 tabelas entram; tabelas em português e colunas no original;
tudo como texto; só célula vazia vira nulo.

## A IA neste projeto

A IA foi usada em todas as etapas, e cada saída foi conferida.
Onde ela errou ou assumiu algo que não foi pedido:

| Etapa | O que a IA fez | Como foi descoberto |
|---|---|---|
| Escolha do escopo | Afirmou que o dataset tinha 31 Copas (22 masculinas + 9 femininas). | Contando as linhas de `raw.torneios`: são 30 (22 + 8). |
| 1 · Ingestão | Escreveu a gravação no estilo das versões antigas do DuckDB, sem ler o resultado de cada comando. Na versão 2.0 instalada, a primeira execução quebrou com `connection has an unfinished result`. | Rodando a ingestão. A correção (`executar()` em `pipeline/db.py`) consome sempre o resultado. |
| 1 · README | Escreveu que a seleção masculina e a feminina do mesmo país eram linhas diferentes em `raw.selecoes`. São a mesma linha, e isso mudaria todo ranking que agrupasse só por `team_id`. | Consultando `raw.selecoes`: o Brasil é uma linha só (`T-09`), e 33 das 88 seleções têm `mens_team = 1` e `womens_team = 1`. |
