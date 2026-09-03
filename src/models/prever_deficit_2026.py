"""
Usa o modelo de regressao (cobertura numerica) para calcular o deficit de
crianças ate a meta de cobertura, em 2026 - resposta direta a pergunta
"quantas crianças ficarao sem vacina".
"""
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor

CAMINHO_DATASET_MODELO = Path("data/processed/dataset_modelo.csv")
CAMINHO_FEATURES = Path("data/processed/features_cobertura_vacinal.csv")
CAMINHO_NASCIDOS = Path("data/processed/nascidos_vivos_2023_2025.csv")
CAMINHO_SAIDA = Path("data/processed/deficit_2026.csv")

FEATURES = [
    "cobertura_ano_anterior", "tendencia", "num_ubs",
    "num_postos_saude", "pib_per_capita", "meta",
]


def treinar_modelo_regressao_final():
    """Treina com todos os dados disponiveis (2024+2025), igual fizemos
    para o modelo de classificacao final."""
    df = pd.read_csv(CAMINHO_DATASET_MODELO)
    df["cobertura_alvo"] = df["cobertura_alvo"].clip(upper=1.0)
    df = pd.get_dummies(df, columns=["vacina"], prefix="vacina")
    colunas_vacina = [c for c in df.columns if c.startswith("vacina_")]
    colunas_features = FEATURES + colunas_vacina

    X = df[colunas_features].fillna(0)
    y = df["cobertura_alvo"]

    modelo = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    modelo.fit(X, y)

    joblib.dump(modelo, "data/processed/modelo_regressao_final.joblib")
    joblib.dump(colunas_features, "data/processed/colunas_features_regressao.joblib")

    return modelo, colunas_features, colunas_vacina


def construir_dados_2026(colunas_vacina: list) -> pd.DataFrame:
    """Mesma logica do prever_risco_2026.py - reaproveitada aqui."""
    df_features = pd.read_csv(CAMINHO_FEATURES)

    linhas = []
    for (municipio, vacina), grupo in df_features.groupby(["codigo_municipio_pni", "vacina"]):
        grupo = grupo.sort_values("ano").set_index("ano")
        if 2025 not in grupo.index:
            continue

        cobertura_2025 = grupo.loc[2025, "cobertura"]
        if 2024 in grupo.index:
            tendencia = cobertura_2025 - grupo.loc[2024, "cobertura"]
        else:
            tendencia = 0.0

        linhas.append({
            "codigo_municipio_pni": municipio,
            "vacina": vacina,
            "cobertura_ano_anterior": cobertura_2025,
            "tendencia": tendencia,
            "num_ubs": grupo.loc[2025, "num_ubs"],
            "num_postos_saude": grupo.loc[2025, "num_postos_saude"],
            "pib_per_capita": grupo.loc[2025, "pib_per_capita"],
            "meta": grupo.loc[2025, "meta"],
        })

    resultado = pd.DataFrame(linhas)
    for col_vacina in colunas_vacina:
        nome_vacina = col_vacina.replace("vacina_", "")
        resultado[col_vacina] = (resultado["vacina"] == nome_vacina)

    return resultado


if __name__ == "__main__":
    print("Treinando modelo de regressao final...")
    modelo, colunas_features, colunas_vacina = treinar_modelo_regressao_final()

    print("Montando dados de previsao para 2026...")
    dados_2026 = construir_dados_2026(colunas_vacina)

    X_2026 = dados_2026[colunas_features].fillna(0)
    dados_2026["cobertura_prevista_2026"] = modelo.predict(X_2026).clip(0, 1)

    # Deficit = o quanto falta para bater a meta (zero se ja tiver batido)
    dados_2026["deficit_cobertura"] = (
        dados_2026["meta"] - dados_2026["cobertura_prevista_2026"]
    ).clip(lower=0)

    # Junta nascidos vivos de 2025 (populacao-base mais recente)
    nascidos = pd.read_csv(CAMINHO_NASCIDOS)
    nascidos["codigo_municipio_pni"] = nascidos["codigo_municipio_pni"].astype(str)
    nascidos_2025 = nascidos[nascidos["ano"] == 2025][["codigo_municipio_pni", "nascidos_vivos"]]

    dados_2026["codigo_municipio_pni"] = dados_2026["codigo_municipio_pni"].astype(str)
    dados_2026 = dados_2026.merge(nascidos_2025, on="codigo_municipio_pni", how="left")

    # Numero estimado de criancas que ficarao sem a vacina (deficit x populacao-base)
    dados_2026["criancas_sem_vacina_estimado"] = (
        dados_2026["deficit_cobertura"] * dados_2026["nascidos_vivos"].fillna(0)
    ).round().astype(int)

    dados_2026 = dados_2026.sort_values("criancas_sem_vacina_estimado", ascending=False)
    dados_2026.to_csv(CAMINHO_SAIDA, index=False)

    print(f"\nSalvo: {CAMINHO_SAIDA}")
    print(f"\nTop 10 município×vacina por número de crianças sem vacina (estimado):")
    print(
        dados_2026[["codigo_municipio_pni", "vacina", "cobertura_prevista_2026",
                     "meta", "criancas_sem_vacina_estimado"]].head(10)
    )