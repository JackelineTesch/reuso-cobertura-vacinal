"""
Explica as previsões do modelo com SHAP — para cada município/vacina,
mostra quais fatores mais pesaram na previsão de risco (não é uma
"caixa-preta": um gestor consegue ver o "porquê" de cada score).
"""
import joblib
import pandas as pd
import shap
from pathlib import Path

CAMINHO_MODELO = "data/processed/modelo_final.joblib"
CAMINHO_COLUNAS = "data/processed/colunas_features.joblib"
CAMINHO_PREVISOES = "data/processed/previsoes_risco_2026.csv"

# Nomes amigáveis para exibir no lugar dos nomes técnicos das colunas
NOMES_AMIGAVEIS = {
    "cobertura_ano_anterior": "Cobertura no ano anterior",
    "tendencia": "Tendência de queda/alta recente",
    "num_ubs": "Número de UBS",
    "num_postos_saude": "Número de Postos de Saúde",
    "pib_per_capita": "PIB per capita",
    "meta": "Meta de cobertura da vacina",
}


def explicar_top_municipios(n=5):
    modelo = joblib.load(CAMINHO_MODELO)
    colunas_features = joblib.load(CAMINHO_COLUNAS)
    previsoes = pd.read_csv(CAMINHO_PREVISOES)

    # Pega os N casos de maior índice de urgência (já ordenado ao salvar)
    top_casos = previsoes.head(n).reset_index(drop=True)
    X_top = top_casos[colunas_features].fillna(0)

    explainer = shap.TreeExplainer(modelo)
    valores_shap = explainer.shap_values(X_top)

    # Para classificação binária, valores_shap tem 2 conjuntos (classe 0 e
    # classe 1) — queremos a classe 1 ("abaixo da meta" = risco)
    if isinstance(valores_shap, list):
        valores_shap_risco = valores_shap[1]
    else:
        valores_shap_risco = valores_shap[:, :, 1]

    for i in range(n):
        municipio = top_casos.loc[i, "codigo_municipio_pni"]
        vacina = top_casos.loc[i, "vacina"]
        risco = top_casos.loc[i, "probabilidade_risco"]

        print(f"\n{'=' * 60}")
        print(f"Município {municipio} — {vacina} — Risco previsto: {risco:.1%}")
        print("=" * 60)

        contribuicoes = pd.Series(valores_shap_risco[i], index=colunas_features)
        contribuicoes = contribuicoes[contribuicoes.abs() > 0.001]  # ignora ruído irrelevante
        contribuicoes = contribuicoes.sort_values(key=abs, ascending=False)

        for feature, valor in contribuicoes.head(5).items():
            nome_exibicao = NOMES_AMIGAVEIS.get(feature, feature)
            direcao = "aumenta" if valor > 0 else "reduz"
            print(f"  {nome_exibicao}: {direcao} o risco em {abs(valor):.3f}")


if __name__ == "__main__":
    explicar_top_municipios(n=5)