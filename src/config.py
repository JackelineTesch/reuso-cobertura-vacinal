"""Configurações centrais do projeto"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA_RAW = RAIZ / "data" / "raw"
DATA_PROCESSED = RAIZ / "data" / "processed"
DUCKDB_PATH = DATA_PROCESSED / "cobertura_vacinal.duckdb"

# Metas de cobertura por imunobiológico (parâmetros oficiais do PNI).
# Não é um número único: BCG tem meta diferente das demais vacinas do
# calendário básico.
# Fonte: Ministério da Saúde — "O PNI estabelece que a cobertura vacinal
# adequada é de 80% para meningo e HPV; 90% para rotavírus, influenza e
# BCG, e 95% para as demais vacinas."
# https://www.gov.br/saude/pt-br/assuntos/noticias/2021/dezembro/ministerio-da-saude-e-fiocruz-tracam-estrategias-para-aumentar-coberturas-vacinais-no-pais
METAS_COBERTURA = {
    "Tríplice viral (D1)": 0.95,
    "Poliomielite (3ª dose)": 0.95,
    "BCG": 0.90,
    "Hepatite B": 0.95,
}

# Imunobiológicos do calendário básico infantil priorizados na primeira versão
# (tríplice viral e poliomielite: maior risco epidemiológico de reintrodução
# de doença se a cobertura cair; BCG e hepatite B: adicionadas para ampliar
# a cobertura de análise, mesmo com risco de queda historicamente menor)
IMUNOBIOLOGICOS_PRIORITARIOS = [
    "Tríplice viral (D1)",
    "Poliomielite (3ª dose)",
    "BCG",
    "Hepatite B",
]

# Janela de anos para a validação temporal walk-forward do modelo
# (ajustado depois de descobrir que o OpenDataSUS só cobre 2020+)
ANO_INICIO_TREINO = 2020
ANO_MINIMO_TESTE = 2023
