"""
Funções reutilizáveis de explicação SHAP — usadas tanto para testes em
lote (linha de comando) quanto pelo app Streamlit (explicação sob
demanda, para o município que o usuário escolher).
"""
import joblib
import pandas as pd
import shap
from pathlib import Path

CAMINHO_MODELO = "data/processed/modelo_final.joblib"
CAMINHO_COLUNAS = "data/processed/colunas_features.joblib"
CAMINHO_PREVISOES = "data/processed/previsoes_risco_2026.csv"

NOMES_AMIGAVEIS = {
    "cobertura_ano_anterior": "Cobertura no ano anterior",
    "tendencia": "Tendência de queda/alta recente",
    "num_ubs": "Número de UBS",
    "num_postos_saude": "Número de Postos de Saúde",
    "pib_per_capita": "PIB per capita",
    "meta": "Meta de cobertura da vacina",
}


def carregar_explainer():
    """
    Carrega o modelo e monta o SHAP TreeExplainer — operação relativamente
    cara (percorre as 200 árvores do modelo), então deve ser chamada UMA
    VEZ só, não a cada explicação individual. No app Streamlit, isso vai
    entrar num cache (@st.cache_resource), carregado uma vez por sessão.
    """
    modelo = joblib.load(CAMINHO_MODELO)
    colunas_features = joblib.load(CAMINHO_COLUNAS)
    explainer = shap.TreeExplainer(modelo)
    return modelo, explainer, colunas_features


def explicar_caso(explainer, colunas_features, linha_dados: pd.Series, top_n: int = 5) -> list[dict]:
    """
    Explica UM caso específico (uma linha de features já pronta).
    Barato o suficiente para rodar a cada interação do usuário no app.
    Retorna uma lista de dicts, pronta para renderizar (não faz print).
    """
    X = linha_dados[colunas_features].to_frame().T.fillna(0)
    valores_shap = explainer.shap_values(X)

    if isinstance(valores_shap, list):
        valores_risco = valores_shap[1][0]
    else:
        valores_risco = valores_shap[0, :, 1]

    contribuicoes = pd.Series(valores_risco, index=colunas_features)
    contribuicoes = contribuicoes[contribuicoes.abs() > 0.001]
    contribuicoes = contribuicoes.sort_values(key=abs, ascending=False)

    resultado = []
    for feature, valor in contribuicoes.head(top_n).items():
        resultado.append({
            "feature": feature,
            "nome_exibicao": NOMES_AMIGAVEIS.get(feature, feature),
            "valor": float(valor),
            "direcao": "aumenta" if valor > 0 else "reduz",
        })
    return resultado


def buscar_e_explicar(codigo_municipio_pni: str, vacina: str, top_n: int = 5) -> dict:
    """
    Função de mais alto nível: dado um código de município e uma vacina,
    busca a previsão já calculada e retorna a explicação — é essa que o
    app Streamlit vai chamar diretamente, passando o que o usuário digitou.
    """
    modelo, explainer, colunas_features = carregar_explainer()
    previsoes = pd.read_csv(CAMINHO_PREVISOES)
    previsoes["codigo_municipio_pni"] = previsoes["codigo_municipio_pni"].astype(str)

    linha = previsoes[
        (previsoes["codigo_municipio_pni"] == str(codigo_municipio_pni)) &
        (previsoes["vacina"] == vacina)
    ]
    if linha.empty:
        return {"erro": f"Sem previsão para município {codigo_municipio_pni} / {vacina}"}

    linha = linha.iloc[0]
    explicacao = explicar_caso(explainer, colunas_features, linha, top_n=top_n)

    return {
        "codigo_municipio_pni": codigo_municipio_pni,
        "vacina": vacina,
        "risco_previsto": float(linha["probabilidade_risco"]),
        "explicacao": explicacao,
    }


if __name__ == "__main__":
    # Modo de teste em lote — reaproveita as funções acima, mas roda
    # para os top 5 casos de maior urgência, imprimindo no terminal
    previsoes = pd.read_csv(CAMINHO_PREVISOES)
    top_casos = previsoes.head(5)

    for _, caso in top_casos.iterrows():
        resultado = buscar_e_explicar(caso["codigo_municipio_pni"], caso["vacina"])
        print(f"\n{'=' * 60}")
        print(f"Município {resultado['codigo_municipio_pni']} — {resultado['vacina']} — Risco previsto: {resultado['risco_previsto']:.1%}")
        print("=" * 60)
        for item in resultado["explicacao"]:
            print(f"  {item['nome_exibicao']}: {item['direcao']} o risco em {abs(item['valor']):.3f}")