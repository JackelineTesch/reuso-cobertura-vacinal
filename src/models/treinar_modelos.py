"""
Treina e compara 3 modelos para prever se um município ficará abaixo da
meta de cobertura vacinal: Random Forest, XGBoost, e regressão logística
regularizada.

VALIDAÇÃO TEMPORAL (walk-forward): treina com dados de 2024, testa com
2025 — nunca o contrário, para não vazar informação do futuro.

MÉTRICA PRIORITÁRIA: recall da classe "abaixo da meta" — um falso
negativo (dizer que está OK quando não está) é mais caro que um falso
positivo (alertar à toa), porque significa não intervir onde era preciso.
"""

import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb

CAMINHO_DATASET = Path("data/processed/dataset_modelo.csv")

FEATURES = [
    "cobertura_ano_anterior",
    "tendencia",
    "num_ubs",
    "num_postos_saude",
    "pib_per_capita",
    "meta"
]

def carregar_treino_teste():
    df = pd.read_csv(CAMINHO_DATASET)

    # One-hot encoding da variável categórica "vacina" - cada vacina vira uma coluna binária,
    # já que o modelo não consegue lidar com variáveis categóricas diretamente.
    df = pd.get_dummies(df, columns=["vacina"], prefix="vacina")
    colunas_vacina = [c for c in df.columns if c.startswith("vacina_")]

    # Treino: ano_alvo = 2024, Teste: ano_alvo = 2025
    df_treino = df[df["ano_alvo"] == 2024]
    df_teste = df[df["ano_alvo"] == 2025]

    colunas_features = FEATURES + colunas_vacina

    X_treino = df_treino[colunas_features].fillna(0)
    y_treino = df_treino["abaixo_meta_alvo"]

    X_teste = df_teste[colunas_features].fillna(0)
    y_teste = df_teste["abaixo_meta_alvo"]

    return X_treino, y_treino, X_teste, y_teste, colunas_features 

def avaliar(nome, y_teste, y_pred, y_proba):
    print(f"\n{'=' * 50}")
    print(f"{nome}")
    print("=" * 50)
    print(classification_report(y_teste, y_pred, target_names=["Acima da meta", "Abaixo da meta"]))
    auc = roc_auc_score(y_teste, y_proba)
    print(f"AUC-ROC: {roc_auc_score(y_teste, y_proba):.3f}")

if __name__ == "__main__":
    X_treino, y_treino, X_teste, y_teste, colunas_features = carregar_treino_teste()
    print(f"Treino:{len(X_treino)} linhas (2024) | Teste:{len(X_teste)} linhas (2025)")
    print(f"Features usadas: {colunas_features}")


    # Modelo 1: Regressão logística regularizada (L2)
    # Precisa de dados normalizados (mesma escala), então usamos StandardScaler
    scaler = StandardScaler()
    X_treino_norm = scaler.fit_transform(X_treino)
    X_teste_norm = scaler.transform(X_teste)

    modelo_logistico = LogisticRegression(penalty="l2", C=1.0, max_iter=1000, random_state=42)
    modelo_logistico.fit(X_treino_norm, y_treino)
    y_pred = modelo_logistico.predict(X_teste_norm)
    y_proba = modelo_logistico.predict_proba(X_teste_norm)[:, 1]
    avaliar("Regressão Logística Regularizada (L2)", y_teste, y_pred, y_proba)

    # Modelo 2: Randon Forest
    modelo_rf = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=42, class_weight="balanced"
        )
    modelo_rf.fit(X_treino, y_treino)
    y_pred = modelo_rf.predict(X_teste)
    y_proba = modelo_rf.predict_proba(X_teste)[:, 1]
    avaliar("Random Forest", y_teste, y_pred, y_proba)

    # Modelo 3: XGBoost
    modelo_xgb = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42, eval_metric="logloss"
    )
    modelo_xgb.fit(X_treino, y_treino)
    y_pred = modelo_xgb.predict(X_teste)
    y_proba = modelo_xgb.predict_proba(X_teste)[:, 1]
    avaliar("XGBoost", y_teste, y_pred, y_proba)