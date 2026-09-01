"""
Reestrutura a tabela de features (uma linha por munic'ípio/ano/vacina)
em formato de aprendizado supervisionado: cada linha vira uma predição de "ano Y" 
usando dados disponíveis até o "ano Y - 1" - sem vazar informação do futuro (reg
de ouro de séies temporais). 
"""

import pandas as pd
from pathlib import Path

CAMINHO_FEATURES = Path("data/processed/features_cobertura_vacinal.csv")
CAMINHO_SAIDA = Path("data/processed/dataset_modelo.csv")

def construir_dataset_modelo() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_FEATURES)

    linhas_modelo = []

    for (municipio, vacina), grupo in df.groupby(["codigo_municipio_pni", "vacina"]):
        grupo = grupo.sort_values("ano").set_index("ano")

        for ano_alvo in [2024, 2025]:
            ano_anterior = ano_alvo - 1
            ano_2_anos_antes = ano_alvo - 2

            if ano_anterior not in grupo.index:
                continue  # Não temos dados do ano anterior, não dá para prever

            cobertura_anterior = grupo.loc[ano_anterior, "cobertura"]

            # Tendência só existe se tivermos 2 anos de histórico antes do alvo
            if ano_2_anos_antes in grupo.index:
                cobertura_2_anos_antes = grupo.loc[ano_2_anos_antes, "cobertura"]
                tendencia = cobertura_anterior - cobertura_2_anos_antes
            else:
                tendencia = 0.0  # Não temos histórico suficiente

            
            linhas_modelo.append({
                "codigo_municipio_pni": municipio,
                "vacina": vacina,
                "ano_alvo": ano_alvo,
                "cobertura_ano_anterior": cobertura_anterior,
                "tendencia": tendencia,
                "num_ubs": grupo.loc[ano_anterior, "num_ubs"],
                "num_postos_saude": grupo.loc[ano_anterior, "num_postos_saude"],
                "pib_per_capita": grupo.loc[ano_anterior, "pib_per_capita"],
                "meta": grupo.loc[ano_anterior, "meta"],
                # Alvo: o município ficou abaixo da meta NO ANO QUE QUEREMOS PREVER
                "abaixo_meta_alvo": grupo.loc[ano_alvo, "abaixo_meta"] if ano_alvo in grupo.index else None,
            })

    resultado = pd.DataFrame(linhas_modelo)
    resultado = resultado.dropna(subset=["abaixo_meta_alvo"])  # Remove linhas sem alvo definido
    resultado["abaixo_meta_alvo"] = resultado["abaixo_meta_alvo"].astype(bool)  # Converte para 0/1
    return resultado

if __name__ == "__main__":
    dataset = construir_dataset_modelo()
    print(f"\nTipo da coluna abaixo_meta_alvo: {dataset['abaixo_meta_alvo'].dtype}")
    print(f"Valores únicos: {dataset['abaixo_meta_alvo'].unique()}")
    print(f"Contagem de cada valor:")
    print(dataset['abaixo_meta_alvo'].value_counts(dropna=False))
    dataset.to_csv(CAMINHO_SAIDA, index=False)

    print(f"\nSalvo: {CAMINHO_SAIDA}")
    print(f"Total de linhas: {len(dataset)}")
    print(f"\nDistribuição por ano_alvo:")
    print(dataset["ano_alvo"].value_counts())
    print(f"\nDistribuição do alvo (abaixo_meta) por ano:")
    print(dataset.groupby("ano_alvo")["abaixo_meta_alvo"].mean())
    print(f"\nAmostra final:")
    print(dataset.head())