"""
Treina o modelo final (Random Forest, com todos os dados 2024+2025) e
gera as previsões de risco para 2026 — o "score de risco" que alimenta
o ranking de urgência e o app Streamlit.
"""

import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier

CAMINHO_DATASET_MODELO = Path("data/processed/dataset_modelo.csv")
CAMINHO_FEATURES = Path("data/processed/features_cobertura_vacinal.csv")
CAMINHO_SAIDA = Path("data/processed/previsoes_risco_2026.csv")

FEATURES = [
    "cobertura_ano_anterior", 
    "tendencia", 
    "num_ubs", 
    "num_postos_saude",
    "pib_per_capita",
    "meta"
]

def trenar_modelo_final():
    """
    Treina o modelo final (Random Forest) com todos os dados de 2024 e 2025.
    """
    # Carrega o dataset completo
    df = pd.read_csv(CAMINHO_DATASET_MODELO)
    df = pd.get_dummies(df, columns=["vacina"], prefix="vacina")
    colunas_vacina = [c for c in df.columns if c.startswith("vacina_")]
    colunas_features = FEATURES + colunas_vacina

    # Separa as features e o target
    X = df[colunas_features].fillna(0)  # Preenche valores ausentes com 0
    y = df["abaixo_meta_alvo"]
        
    # Cria e treina o modelo Random Forest
    modelo = RandomForestClassifier(
        n_estimators=200,
        max_depth=8, 
        random_state=42,
        class_weight="balanced"
    )
    modelo.fit(X, y)
    
    return modelo, colunas_features, colunas_vacina

def construir_dados_2026(colunas_vacina: list) -> pd.DataFrame:
    """
    Monta as linhas de previsão para 2026, usando 2025 como ano anterior
    e a tendência 2024→2025 — mesma lógica do build_model_dataset.py,
    mas sem alvo conhecido (é isso que vamos prever).
    """
    df_features = pd.read_csv(CAMINHO_FEATURES)

    linhas = []
    for (municipio, vacina), grupo in df_features.groupby(["codigo_municipio_pni", "vacina"]):
        grupo = grupo.sort_values("ano").set_index("ano")

        if 2025 not in grupo.index:
            continue  # Não há dados de 2025 para este município/vacina

        cobertura_2025 = grupo.loc[2025, "cobertura"]

        if 2024 in grupo.index:
            tendencia = cobertura_2025 - grupo.loc[2024, "cobertura"]
        else:
            tendencia = 0.0  # Sem dados de 2024, assume tendência neutra

        linhas.append({
            "codigo_municipio_pni": municipio,
            "vacina": vacina,
            "cobertura_ano_anterior": cobertura_2025,
            "tendencia": tendencia,
            "num_ubs": grupo.loc[2025, "num_ubs"],
            "num_postos_saude": grupo.loc[2025, "num_postos_saude"],
            "pib_per_capita": grupo.loc[2025, "pib_per_capita"],
            "meta": grupo.loc[2025, "meta"]
        })

    resultado = pd.DataFrame(linhas)

    # Mesmo one-hot encoding das vacinas, plicado aqui manualmente para garantir 
    # que as colunas batam com as do modelo treinado
    for col_vacina in colunas_vacina:
        nome_vacina = col_vacina.replace("vacina_", "")
        resultado[col_vacina] = (resultado["vacina"] == nome_vacina)
        
    return resultado

if __name__ == "__main__":
    print("Treinando modelo final com todos os dados disponíveis (2024+2025)...")
    modelo, colunas_features, colunas_vacina = trenar_modelo_final()

    print("MMontando os dados de previsão para 2026...")
    dados_2026 = construir_dados_2026(colunas_vacina)
    print(f"Total de linhas de previsão para 2026: {len(dados_2026)}")

    X_2026 = dados_2026[colunas_features].fillna(0)
    dados_2026["probabilidade_risco"] = modelo.predict_proba(X_2026)[:, 1]  # Probabilidade de estar abaixo da meta

    dados_2026 = dados_2026.sort_values("probabilidade_risco", ascending=False)
    dados_2026.to_csv(CAMINHO_SAIDA, index=False)

    print(f"\nSalvo: {CAMINHO_SAIDA}")
    print(f"\nDistribuição de risco por vacina (média):")
    print(dados_2026.groupby("vacina")["probabilidade_risco"].mean())
    print(f"\nTop 10 municípios com maior risco:")
    print(dados_2026[["codigo_municipio_pni", "vacina", "probabilidade_risco"]].head(10))