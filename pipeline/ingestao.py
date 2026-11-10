"""Etapa 1 — Ingestão: copia os 27 CSVs de raw/ para o schema raw do DuckDB.

Spec completa em specs/ingestao.md. Resumo das regras e do porquê:
- Nada é transformado: tudo é lido como texto, nenhuma linha sai, nenhuma
  coluna muda de nome. A raw é o espelho da fonte; corrigir aqui esconde o
  problema da etapa que deveria tratá-lo.
- Só célula vazia vira nulo. O padrão do pandas também apaga textos como
  "NA", "None" e "null", que podem ser valores reais.
- A pasta raw/ precisa ter exatamente os arquivos do mapa. Arquivo faltando ou
  sobrando é sinal de que algo mudou na origem, e é melhor parar antes de gravar.
- A contagem do arquivo é comparada com a do banco, tabela por tabela.

Uso:
    uv run python -m pipeline.ingestao
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.db import PASTA_RAW, conectar, criar_schema, gravar

SCHEMA = "raw"

# arquivo de origem -> tabela no banco (decisão 2 da spec: tabela em português)
MAPA_TABELAS: dict[str, str] = {
    "award_winners.csv.gz": "premiados",
    "awards.csv.gz": "premios",
    "bookings.csv.gz": "cartoes",
    "confederations.csv.gz": "confederacoes",
    "goals.csv.gz": "gols",
    "group_standings.csv.gz": "classificacao_grupos",
    "groups.csv.gz": "grupos",
    "host_countries.csv.gz": "paises_sede",
    "manager_appearances.csv.gz": "tecnicos_partidas",
    "manager_appointments.csv.gz": "tecnicos_torneios",
    "managers.csv.gz": "tecnicos",
    "matches.csv.gz": "partidas",
    "penalty_kicks.csv.gz": "cobrancas_penaltis",
    "player_appearances.csv.gz": "jogadores_partidas",
    "players.csv.gz": "jogadores",
    "qualified_teams.csv.gz": "selecoes_classificadas",
    "referee_appearances.csv.gz": "arbitros_partidas",
    "referee_appointments.csv.gz": "arbitros_torneios",
    "referees.csv.gz": "arbitros",
    "squads.csv.gz": "elencos",
    "stadiums.csv.gz": "estadios",
    "substitutions.csv.gz": "substituicoes",
    "team_appearances.csv.gz": "selecoes_partidas",
    "teams.csv.gz": "selecoes",
    "tournament_stages.csv.gz": "fases_torneio",
    "tournament_standings.csv.gz": "classificacao_final",
    "tournaments.csv.gz": "torneios",
}


class IngestaoError(Exception):
    """Falha que impede a ingestão de continuar com segurança."""


def verificar_pasta(pasta: Path, mapa: dict[str, str] = MAPA_TABELAS) -> None:
    """Para se a pasta não tiver exatamente os arquivos esperados."""
    if not pasta.is_dir():
        raise IngestaoError(f"Pasta não encontrada: {pasta}")
    encontrados = {p.name for p in pasta.glob("*.csv.gz")}
    esperados = set(mapa)
    faltando = sorted(esperados - encontrados)
    sobrando = sorted(encontrados - esperados)
    if faltando or sobrando:
        partes = []
        if faltando:
            partes.append(f"faltando: {', '.join(faltando)}")
        if sobrando:
            partes.append(f"não esperados: {', '.join(sobrando)}")
        raise IngestaoError(
            "Arquivos de raw/ não batem com o mapa (" + "; ".join(partes) + ")"
        )


def ler_csv(caminho: Path) -> pd.DataFrame:
    """Lê o CSV como texto puro; só célula vazia vira nulo (decisões 4 e 5)."""
    return pd.read_csv(caminho, dtype=str, keep_default_na=False, na_values=[""])


def ingerir(
    con: duckdb.DuckDBPyConnection,
    pasta: Path = PASTA_RAW,
    mapa: dict[str, str] = MAPA_TABELAS,
) -> dict[str, int]:
    """Grava cada arquivo em raw.<tabela> e devolve {tabela: linhas no banco}."""
    verificar_pasta(pasta, mapa)
    criar_schema(con, SCHEMA)
    contagens: dict[str, int] = {}
    for arquivo, tabela in mapa.items():
        df = ler_csv(pasta / arquivo)
        no_banco = gravar(con, df, SCHEMA, tabela)
        if no_banco != len(df):
            raise IngestaoError(
                f"{arquivo}: {len(df)} linhas no arquivo, {no_banco} no banco"
            )
        contagens[tabela] = no_banco
    return contagens


def formatar_milhar(numero: int) -> str:
    """1248 -> '1.248' (padrão brasileiro)."""
    return f"{numero:,}".replace(",", ".")


def main() -> None:
    # Terminal do Windows não usa UTF-8 por padrão; sem isso o "✓" quebra.
    sys.stdout.reconfigure(encoding="utf-8")
    con = conectar()
    try:
        contagens = ingerir(con)
    except IngestaoError as erro:
        print(f"✗ {erro}")
        sys.exit(1)
    finally:
        con.close()
    largura = max(len(t) for t in contagens) + len(SCHEMA) + 1
    for tabela, linhas in contagens.items():
        nome = f"{SCHEMA}.{tabela}"
        print(f"✓ {nome:<{largura}} {formatar_milhar(linhas):>7} linhas")
    total = sum(contagens.values())
    print(f"\n{len(contagens)} tabelas, {formatar_milhar(total)} linhas no total.")


if __name__ == "__main__":
    main()
