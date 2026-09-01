"""
Junta doses aplicadas (agregadas por município/mês) com população (IBGE),
calcula a cobertura vacinal anual por município/vacina, e monta a variável
alvo do modelo: o município ficou abaixo da meta de cobertura?
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import IMUNOBIOLOGICOS_PRIORITARIOS, METAS_COBERTURA, DATA_PROCESSED

import pandas as pd

CAMINHO_DOSES = Path("data/processed/doses_2023_2025.csv")
CAMINHO_POPULACAO = Path("data/raw/ibge_populacao_2023_2025.csv")
CAMINHO_SAIDA = DATA_PROCESSED / "features_cobertura_vacinal.csv"

def carregar_doses_filtradas() -> pd.DataFrame:
    """ Lê as doses, filtra pela dose-alvo de cada vacina priorizada e soma os meses 
    para obter o total anual por município/vacina.
    """
    doses = pd.read_csv(CAMINHO_DOSES)

    # Corrige o código de município: veio como float (ex.: 110001.0) na 
    # extração - precisa virar string de 6 digitos para casar com o IBGE
    doses["codigo_municipio_pni"] = doses["co_municipio_estabelecimento"].astype(int).astype(str)

    linhas_filtradas = []
    for nome_vacina, especificacao in IMUNOBIOLOGICOS_PRIORITARIOS.items():
        filtro = (
            (doses["sg_imunobiologico"] == especificacao["sigla"]) &
            (doses["ds_tipo_dose"] == especificacao["dose"])
        )
        subset = doses[filtro].copy()
        subset["vacina"] = nome_vacina
        linhas_filtradas.append(subset)

    doses_filtradas = pd.concat(linhas_filtradas, ignore_index=True)

    # Soma os 12 meses para virar total anual por município/vacina
    anual = (
        doses_filtradas
        .groupby(["codigo_municipio_pni", "ano", "vacina"])["doses_aplicadas"]
        .sum()
        .reset_index()
    )
    return anual

def carregar_populacao_alvo() -> pd.DataFrame:
    """
    População-alvo para cobertura vacinal infantil = nascidos vivos
    (SINASC), não população total do município — ver decisoes_tecnicas.md
    para o porquê dessa correção.
    """
    caminho = Path("data/processed/nascidos_vivos_2023_2025.csv")
    pop_alvo = pd.read_csv(caminho)
    pop_alvo["codigo_municipio_pni"] = pop_alvo["codigo_municipio_pni"].astype(str)
    return pop_alvo

def montar_features() -> pd.DataFrame:
    doses_anuais = carregar_doses_filtradas()
    populacao = carregar_populacao_alvo()   # ← troca aqui

    df = doses_anuais.merge(populacao, on=["codigo_municipio_pni", "ano"], how="left")

    sem_populacao = df["nascidos_vivos"].isna().sum()   # ← troca aqui
    if sem_populacao > 0:
        print(f"AVISO: {sem_populacao} linhas sem nascidos vivos correspondente (join falhou).")

    df["cobertura"] = df["doses_aplicadas"] / df["nascidos_vivos"]   # ← troca aqui
    df["meta"] = df["vacina"].map(METAS_COBERTURA)
    df["abaixo_meta"] = df["cobertura"] < df["meta"]

    return df

if __name__ == "__main__":
    features = montar_features()
    CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(CAMINHO_SAIDA, index=False)

    print(f"\nSalvo: {CAMINHO_SAIDA}")
    print(f"Total de linhas: {len(features)}")
    print(f"\nDistribuição de abaixo_meta por vacina:")
    print(features.groupby("vacina")["abaixo_meta"].mean())
    print(f"\nAmostra:")
    print(features.head(10))