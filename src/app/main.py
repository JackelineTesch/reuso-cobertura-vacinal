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

# --- 3. Widgets de busca ---

st.divider()
st.subheader("Consultar um município")


@st.cache_data
def carregar_nomes_municipios() -> dict:
    """Usa o arquivo de população do IBGE, que já tem nome + código PNI
    juntos — evita o problema de converter 6↔7 dígitos manualmente."""
    df = pd.read_csv("data/raw/ibge_populacao_2023_2025.csv")
    df["codigo_municipio_pni"] = df["codigo_municipio_pni"].astype(str)
    # Remove duplicatas (o arquivo tem uma linha por ano, mas o nome é o mesmo)
    df_unico = df.drop_duplicates(subset="codigo_municipio_pni")
    return dict(zip(df_unico["codigo_municipio_pni"], df_unico["nome_municipio"]))


nomes_municipios = carregar_nomes_municipios()
codigos_disponiveis = previsoes["codigo_municipio_pni"].unique()

# Para fazer uma divisão de municípios por estado, extraímos o estado do próprio nome do município
# que extraímos, sem precisa de outra fonte de dados

opcoes_municipio = []
for codigo in codigos_disponiveis:
    nome_completo = nomes_municipios.get(codigo, f"Município {codigo}")
    uf = nome_completo.split(" - ")[-1] if " - " in nome_completo else "??"
    opcoes_municipio.append((codigo, nome_completo, uf))

ufs_disponiveis = sorted(set(uf for _, _, uf in opcoes_municipio))

col1, col2, col3 = st.columns(3)

with col1:
    uf_selecionada = st.selectbox("Estado (UF)", options=ufs_disponiveis)

municipios_da_uf = sorted(
    [(codigo, nome) for codigo, nome, uf in opcoes_municipio if uf == uf_selecionada],
    key=lambda x: x[1],
)

with col2:
    codigo_selecionado = st.selectbox(
        "Município",
        options=[codigo for codigo, nome in municipios_da_uf],
        format_func=lambda codigo: dict(municipios_da_uf).get(codigo, codigo),
    )


vacinas_do_municipio = previsoes[
    previsoes["codigo_municipio_pni"] == codigo_selecionado
]["vacina"].unique()

with col3:
    vacina_selecionada = st.selectbox("Vacina", options=sorted(vacinas_do_municipio))

st.write(f"Você selecionou: município `{codigo_selecionado}` ({nomes_municipios.get(codigo_selecionado, '?')}), vacina `{vacina_selecionada}`")