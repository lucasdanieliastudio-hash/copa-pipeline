"""Conexão com o banco DuckDB, compartilhada por todas as etapas do pipeline.

Regras (specs/ingestao.md, seção Artefatos):
- Caminhos saem da localização deste arquivo, não do diretório corrente.
  Motivo: rodar o script de outra pasta não pode criar um segundo banco vazio
  em outro lugar.
- gravar() devolve a contagem lida do banco, não len(df).
  Motivo: a conferência tem que olhar o que foi gravado de fato.
- Nomes de schema e tabela são validados.
  Motivo: eles entram na SQL por formatação de texto; validar impede que um
  nome errado (ou malicioso) vire outro comando.
"""

import re
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "raw"
CAMINHO_BANCO = RAIZ / "copa.duckdb"

_NOME_VALIDO = re.compile(r"^[a-z][a-z0-9_]*$")


def validar_nome(nome: str) -> str:
    """Aceita só letras minúsculas, números e '_', começando por letra."""
    if not _NOME_VALIDO.match(nome):
        raise ValueError(f"Nome inválido para schema/tabela: {nome!r}")
    return nome


def conectar(caminho: Path = CAMINHO_BANCO) -> duckdb.DuckDBPyConnection:
    """Abre o banco do projeto, criando o arquivo se ele ainda não existir."""
    return duckdb.connect(str(caminho))


def executar(con: duckdb.DuckDBPyConnection, sql: str) -> list[tuple]:
    """Executa a SQL e consome o resultado.

    No DuckDB 2.x um execute() cujo resultado não foi lido bloqueia a conexão
    ("connection has an unfinished result"). Consumir sempre evita isso.
    """
    return con.execute(sql).fetchall()


def criar_schema(con: duckdb.DuckDBPyConnection, nome: str) -> None:
    executar(con, f"CREATE SCHEMA IF NOT EXISTS {validar_nome(nome)}")


def gravar(
    con: duckdb.DuckDBPyConnection, df: pd.DataFrame, schema: str, tabela: str
) -> int:
    """Grava o DataFrame em schema.tabela (substituindo) e devolve a contagem do banco."""
    destino = f"{validar_nome(schema)}.{validar_nome(tabela)}"
    con.register("_entrada", df)
    try:
        executar(con, f"CREATE OR REPLACE TABLE {destino} AS SELECT * FROM _entrada")
    finally:
        con.unregister("_entrada")
    return executar(con, f"SELECT COUNT(*) FROM {destino}")[0][0]
