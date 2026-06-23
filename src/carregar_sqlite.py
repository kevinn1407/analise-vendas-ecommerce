"""
carregar_sqlite.py
-------------------
ETAPA 3 (parte 1): carrega o star schema (CSVs tratados) num banco SQLite,
pra rodar as consultas de sql/consultas.sql.

Nao precisa instalar banco nenhum -> o SQLite ja vem junto com o Python.

Dependencias: pip install pandas
Rodar:        python carregar_sqlite.py

Depois, rode as consultas de um destes jeitos:
  - abra 'vendas.db' no DB Browser for SQLite (interface grafica), ou
  - no terminal:  sqlite3 vendas.db < sql/consultas.sql
"""

import sqlite3
from pathlib import Path

import pandas as pd

PASTA_CSV = Path("dados/tratados")
BANCO = Path("vendas.db")
TABELAS = ["dim_produtos", "dim_clientes", "dim_calendario", "fato_vendas"]


def main():
    if not PASTA_CSV.exists():
        raise SystemExit(
            "Pasta 'dados/tratados/' nao encontrada. "
            "Rode antes o pipeline_dados.py para gerar o star schema."
        )

    con = sqlite3.connect(BANCO)
    print(f"== Carregando star schema em {BANCO} ==")
    for tabela in TABELAS:
        df = pd.read_csv(PASTA_CSV / f"{tabela}.csv")
        df.to_sql(tabela, con, if_exists="replace", index=False)
        print(f"  carregada: {tabela}  ({len(df)} linhas)")
    con.commit()
    con.close()

    print(f"\nPronto! Banco criado em: {BANCO.resolve()}")
    print("Rode as consultas com:  sqlite3 vendas.db < sql/consultas.sql")


if __name__ == "__main__":
    main()
