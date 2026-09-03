"""
Treina um modelo de REGRESSAO (nao classificacao) para prever o valor
numerico exato de cobertura vacinal - permite calcular quantas crianças
ficarao sem vacina, nao so se o municipio fica abaixo/acima da meta.

Validacao temporal: treina 2024, testa 2025 - mesmo padrao do modelo
de classificacao, para medir o erro real antes de usar em producao.
"""
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

CAMINHO_DATASET = Path("data/processed/dataset_modelo.csv")

FEATURES = [
    "cobertura_ano_anterior", "tendencia", "num_ubs",
    "num_postos_saude", "pib_per_capita", "meta",
]


def carregar_treino_teste():
    df = pd.read_csv(CAMINHO_DATASET)

    # Limita a cobertura-alvo em 100% antes de treinar: valores acima disso
    # sao distorcao metodologica conhecida (ano-calendario vs coorte de
    # nascimento - ver decisoes_tecnicas.md), e nao agregam sinal util para
    # calcular o deficit ate a meta (108% e 144% significam a mesma coisa
    # na pratica: "meta batida, sem deficit")
    df["cobertura_alvo"] = df["cobertura_alvo"].clip(upper=1.0)

    df = pd.get_dummies(df, columns=["vacina"], prefix="vacina")
    colunas_vacina = [c for c in df.columns if c.startswith("vacina_")]
    colunas_features = FEATURES + colunas_vacina

    treino = df[df["ano_alvo"] == 2024]
    teste = df[df["ano_alvo"] == 2025]

    X_treino = treino[colunas_features].fillna(0)
    y_treino = treino["cobertura_alvo"]
    X_teste = teste[colunas_features].fillna(0)
    y_teste = teste["cobertura_alvo"]

    return X_treino, y_treino, X_teste, y_teste, colunas_features


if __name__ == "__main__":
    X_treino, y_treino, X_teste, y_teste, colunas_features = carregar_treino_teste()
    print(f"Treino: {len(X_treino)} linhas (2024) | Teste: {len(X_teste)} linhas (2025)")

    modelo = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    modelo.fit(X_treino, y_treino)

    y_pred = modelo.predict(X_teste)
    y_pred = y_pred.clip(0, 1)  # garante previsão dentro de faixa plausível

    mae = mean_absolute_error(y_teste, y_pred)
    r2 = r2_score(y_teste, y_pred)

    print(f"\nErro absoluto médio (MAE): {mae:.3f}")
    print(f"  -> em termos práticos: a previsão de cobertura erra, em média, {mae:.1%} para mais ou para menos")
    print(f"R² (variância explicada): {r2:.3f}")