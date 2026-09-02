"""
APP Stremlit - Radar de Risco Vacinal
"""

import streamlit as st
import pandas as pd
import json

# --- Configuração da página ---
# Primeira chamada Streamlit do arquivo

st.set_page_config(
    page_title="Radar de Risco Vacinal",
    page_icon="💉",
    layout="wide", # usa a largura inteira da tela, melhor para mapas/tabelas
)

# --- Carregamento de dados, com cache ---

@st.cache_data
def carregar_previsoes() -> pd.DataFrame:
    """ Cache de Dados: o Streamlit guarda o resultado e só recalcula se
    o arquivo de origem mudar (ou se limpar o cache manualmente)."""
    df = pd.read_csv("data/processed/previsoes_risco_2026.csv")
    df["codigo_municipio_pni"] = df["codigo_municipio_pni"].astype(str)
    return df

@st.cache_data
def carregar_malha_geografica() -> dict:
    with open("data/processed/malha_municipios_brasil.geojson", encoding="utf-8") as f:
        return json.load(f)

# --- Corpo principal do app ---

st.title("💉 Radar de Risco Vacinal")
st.markdown(
    "Score preditivo de risco de queda na cobertura vacinal infantil,"
    " por município e vacina - 2º Concurso de Reúso de Dados Abertos da CGU"
)

previsoes = carregar_previsoes()
malha = carregar_malha_geografica()

st.write(f"Dados carregados: {len(previsoes)} previsoes, {len(malha['features'])} municipios na malha.")