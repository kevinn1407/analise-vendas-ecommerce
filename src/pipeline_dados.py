"""
pipeline_dados.py
------------------
Pipeline UNICO (extracao + tratamento) feito todo em pandas.

Fluxo:
  1. Baixa produtos, clientes e carrinhos da DummyJSON (limit=0 -> traz tudo).
  2. Achata/explode os JSONs com pd.json_normalize.
  3. Limpa, valida, cria data do pedido e features.
  4. Salva o modelo estrela E uma tabela unica consolidada.

Saidas (em dados/tratados/):
  - dim_produtos.csv / dim_clientes.csv / dim_calendario.csv / fato_vendas.csv
  - vendas_completo.csv  -> tudo concatenado numa tabela so (1 linha por item)

Dependencias:  pip install requests pandas numpy
Rodar:         python pipeline_dados.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
BASE_URL = "https://dummyjson.com"
PASTA_OUT = Path("dados/tratados")
TIMEOUT = 30
SEED = 42
MESES_HISTORICO = 18

# alguns servidores limitam mais o User-Agent padrao do python-requests
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-data-pipeline)"}

DATA_FIM = pd.Timestamp.today().normalize()
DATA_INICIO = DATA_FIM - pd.DateOffset(months=MESES_HISTORICO)

MESES_PT = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
DIAS_PT = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sab", 6: "Dom"}


# ---------------------------------------------------------------------------
# 1) EXTRACAO  (requests so pra puxar; o resto e tudo pandas)
# ---------------------------------------------------------------------------
def baixar(endpoint, chave, tentativas=6):
    """Puxa todos os registros (limit=0).

    A DummyJSON limita requisicoes em sequencia (erro 429). Entao, se levar
    429 ou cair a conexao, ele espera e tenta de novo, respeitando o tempo
    pedido pela propria API no cabecalho 'Retry-After'."""
    url = f"{BASE_URL}/{endpoint}?limit=0"
    for n in range(1, tentativas + 1):
        print(f"  baixando {endpoint}... (tentativa {n})")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 429:
                espera = int(resp.headers.get("Retry-After", 2 ** n))
                print(f"    429 (limite atingido). Esperando {espera}s...")
                time.sleep(espera)
                continue
            resp.raise_for_status()
            return resp.json()[chave]
        except requests.RequestException as e:
            espera = 2 ** n
            print(f"    erro: {e}. Tentando de novo em {espera}s...")
            time.sleep(espera)
    raise RuntimeError(
        f"Nao consegui baixar '{endpoint}' apos {tentativas} tentativas")


# ---------------------------------------------------------------------------
# 2) ACHATAMENTO  (pd.json_normalize)
# ---------------------------------------------------------------------------
def achatar_produtos(produtos):
    df = pd.json_normalize(produtos)
    return df.rename(columns={
        "id": "produto_id", "title": "titulo", "category": "categoria",
        "brand": "marca", "price": "preco", "discountPercentage": "desconto_pct",
        "rating": "avaliacao", "stock": "estoque",
        "availabilityStatus": "status_estoque",
    })


def achatar_clientes(usuarios):
    df = pd.json_normalize(usuarios)
    return df.rename(columns={
        "id": "cliente_id", "firstName": "nome", "lastName": "sobrenome",
        "age": "idade", "gender": "genero",
        "address.city": "cidade", "address.state": "estado",
        "address.country": "pais", "company.name": "empresa",
        "company.department": "departamento", "company.title": "cargo",
    })


def achatar_itens(carrinhos):
    """Explode a lista de produtos de cada carrinho em 1 linha por item."""
    itens = pd.json_normalize(
        carrinhos,
        record_path="products",
        meta=["id", "userId"],
        meta_prefix="cart_",
    )
    return itens.rename(columns={
        "id": "produto_id", "quantity": "quantidade", "price": "preco_unit",
        "discountPercentage": "desconto_pct",
        "cart_id": "pedido_id", "cart_userId": "cliente_id",
    })


# ---------------------------------------------------------------------------
# 3) VALIDACAO de regras de negocio (so reporta)
# ---------------------------------------------------------------------------
def validar(itens, df_clientes, df_produtos):
    print("\n--- Validacao de regras de negocio ---")
    qtd_inv = int((itens["quantidade"] <= 0).sum())
    preco_inv = int((itens["preco_unit"] < 0).sum())
    cli_orfaos = int(itens.loc[
        ~itens["cliente_id"].isin(df_clientes["cliente_id"]), "cliente_id"
    ].nunique())
    prod_orfaos = int(itens.loc[
        ~itens["produto_id"].isin(df_produtos["produto_id"]), "produto_id"
    ].nunique())
    print(f"  Itens com quantidade <= 0 ........ {qtd_inv}")
    print(f"  Itens com preco < 0 .............. {preco_inv}")
    print(f"  Clientes inexistentes (FK orfa) .. {cli_orfaos}")
    print(f"  Produtos inexistentes (FK orfa) .. {prod_orfaos}")


# ---------------------------------------------------------------------------
# 4) DIMENSOES + features
# ---------------------------------------------------------------------------
def faixa_etaria(idade):
    if pd.isna(idade):
        return "Desconhecida"
    for limite, rotulo in [(25, "18-24"), (35, "25-34"), (45, "35-44"),
                           (55, "45-54")]:
        if idade < limite:
            return rotulo
    return "55+"


def faixa_preco(preco):
    if pd.isna(preco):
        return "Desconhecido"
    for limite, rotulo in [(10, "Ate R$10"), (50, "R$10-50"),
                           (200, "R$50-200"), (1000, "R$200-1000")]:
        if preco < limite:
            return rotulo
    return "Acima de R$1000"


def construir_dim_clientes(df):
    dim = df.copy()
    dim["idade"] = pd.to_numeric(dim["idade"], errors="coerce")
    dim["nome_completo"] = (
        dim["nome"].fillna("") + " " + dim["sobrenome"].fillna("")
    ).str.strip()
    dim["faixa_etaria"] = dim["idade"].apply(faixa_etaria)
    return dim[["cliente_id", "nome_completo", "idade", "faixa_etaria",
                "genero", "cidade", "estado", "pais", "empresa",
                "departamento", "cargo"]]


def construir_dim_produtos(df):
    dim = df.copy()
    dim["marca"] = dim.get("marca", pd.Series(dtype=object)).fillna("Sem marca")
    dim["preco"] = pd.to_numeric(dim["preco"], errors="coerce")
    dim["faixa_preco"] = dim["preco"].apply(faixa_preco)
    return dim[["produto_id", "titulo", "categoria", "marca", "preco",
                "faixa_preco", "avaliacao", "estoque", "status_estoque"]]


# ---------------------------------------------------------------------------
# 5) DATAS dos pedidos + calendario
# ---------------------------------------------------------------------------
def gerar_datas_pedido(itens):
    pedidos = itens["pedido_id"].drop_duplicates().sort_values()
    rng = np.random.default_rng(SEED)
    dias = (DATA_FIM - DATA_INICIO).days
    # triangular -> leve tendencia de crescimento (mais pedidos recentes)
    offsets = rng.triangular(0, dias, dias, size=len(pedidos)).astype(int)
    datas = DATA_INICIO + pd.to_timedelta(offsets, unit="D")
    return pd.DataFrame({"pedido_id": pedidos.values, "data_pedido": datas})


def construir_dim_calendario(datas):
    cal = pd.DataFrame({"data": pd.date_range(
        datas["data_pedido"].min().normalize(),
        datas["data_pedido"].max().normalize(), freq="D")})
    cal["ano"] = cal["data"].dt.year
    cal["mes"] = cal["data"].dt.month
    cal["nome_mes"] = cal["mes"].map(MESES_PT)
    cal["ano_mes"] = cal["data"].dt.strftime("%Y-%m")
    cal["trimestre"] = cal["data"].dt.quarter
    cal["dia_semana"] = cal["data"].dt.dayofweek
    cal["nome_dia"] = cal["dia_semana"].map(DIAS_PT)
    cal["fim_de_semana"] = cal["dia_semana"] >= 5
    return cal


# ---------------------------------------------------------------------------
# 6) FATO + features de valor
# ---------------------------------------------------------------------------
def construir_fato(itens, datas):
    fato = itens.merge(datas, on="pedido_id", how="left")
    fato["valor_bruto"] = (fato["preco_unit"] * fato["quantidade"]).round(2)
    fato["valor_desconto"] = (
        fato["valor_bruto"] * fato["desconto_pct"] / 100).round(2)
    fato["valor_liquido"] = (fato["valor_bruto"] - fato["valor_desconto"]).round(2)
    return fato[["pedido_id", "data_pedido", "cliente_id", "produto_id",
                 "quantidade", "preco_unit", "desconto_pct",
                 "valor_bruto", "valor_desconto", "valor_liquido"]]


# ---------------------------------------------------------------------------
# 7) CONSOLIDACAO -> tudo numa tabela so
# ---------------------------------------------------------------------------
def consolidar(fato, dim_produtos, dim_clientes, dim_calendario):
    wide = (fato
            .merge(dim_produtos, on="produto_id", how="left")
            .merge(dim_clientes, on="cliente_id", how="left")
            .merge(dim_calendario, left_on="data_pedido", right_on="data",
                   how="left")
            .drop(columns=["data"]))
    return wide


def salvar(df, nome):
    PASTA_OUT.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_OUT / f"{nome}.csv"
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"  salvo: {caminho}  ({len(df)} linhas)")


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------
def processar(produtos_raw, usuarios_raw, carrinhos_raw):
    """Recebe os JSONs crus e devolve as tabelas tratadas (testavel sem rede)."""
    df_produtos = achatar_produtos(produtos_raw)
    df_clientes = achatar_clientes(usuarios_raw)
    itens = achatar_itens(carrinhos_raw)

    validar(itens, df_clientes, df_produtos)

    dim_produtos = construir_dim_produtos(df_produtos)
    dim_clientes = construir_dim_clientes(df_clientes)
    datas = gerar_datas_pedido(itens)
    dim_calendario = construir_dim_calendario(datas)
    fato = construir_fato(itens, datas)
    wide = consolidar(fato, dim_produtos, dim_clientes, dim_calendario)
    return dim_produtos, dim_clientes, dim_calendario, fato, wide


def main():
    print("== PIPELINE UNICO (pandas) -- VERSAO 2 (com retry pra 429) ==")
    produtos_raw = baixar("products", "products")
    time.sleep(1)                      # pausa educada pra nao tomar 429
    usuarios_raw = baixar("users", "users")
    time.sleep(1)
    carrinhos_raw = baixar("carts", "carts")

    dim_produtos, dim_clientes, dim_calendario, fato, wide = processar(
        produtos_raw, usuarios_raw, carrinhos_raw)

    print("\n--- Salvando ---")
    salvar(dim_produtos, "dim_produtos")
    salvar(dim_clientes, "dim_clientes")
    salvar(dim_calendario, "dim_calendario")
    salvar(fato, "fato_vendas")
    salvar(wide, "vendas_completo")

    print(f"\nFaturamento liquido total: R$ {fato['valor_liquido'].sum():,.2f}")
    print(f"Periodo: {fato['data_pedido'].min().date()} "
          f"-> {fato['data_pedido'].max().date()}")
    print("\nPronto! Tudo em 'dados/tratados/'. Bora pro SQL. 🚀")


if __name__ == "__main__":
    main()
