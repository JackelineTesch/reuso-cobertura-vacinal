"""
App Streamlit - Radar de Risco Vacinal.

Layout: filtros + score + explicacao SHAP na coluna esquerda (mais estreita),
mapa na coluna direita (mais larga) - evita rolagem vertical em telas normais.
O mapa centraliza e da zoom automatico no estado (UF) selecionado no filtro.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import streamlit as st
import pandas as pd
import json
import plotly.express as px

from src.models.explicar_shap import carregar_explainer, explicar_caso

# --- 1. Configuracao da pagina ---
st.set_page_config(
    page_title="Radar de Risco Vacinal",
    page_icon="💉",
    layout="wide",
)


# --- 2. Carregamento de dados, com cache ---

@st.cache_data
def carregar_previsoes() -> pd.DataFrame:
    df = pd.read_csv("data/processed/previsoes_risco_2026.csv")
    df["codigo_municipio_pni"] = df["codigo_municipio_pni"].astype(str)
    return df


@st.cache_data
def carregar_malha_geografica() -> dict:
    with open("data/processed/malha_municipios_brasil.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def carregar_nomes_municipios() -> dict:
    df = pd.read_csv("data/raw/ibge_populacao_2023_2025.csv")
    df["codigo_municipio_pni"] = df["codigo_municipio_pni"].astype(str)
    df_unico = df.drop_duplicates(subset="codigo_municipio_pni")
    return dict(zip(df_unico["codigo_municipio_pni"], df_unico["nome_municipio"]))


@st.cache_data
def montar_correspondencia_codigos(_malha: dict) -> dict:
    return {
        feature["properties"]["codarea"][:6]: feature["properties"]["codarea"]
        for feature in _malha["features"]
    }


@st.cache_data
def calcular_bbox_por_uf(_malha: dict) -> dict:
    """
    Calcula a caixa delimitadora (bounding box) de cada UF, a partir dos
    poligonos dos municipios - usado para centralizar e dar zoom no mapa
    quando o usuario troca de estado no filtro.
    """
    bboxes = {}
    for feature in _malha["features"]:
        codarea = feature["properties"]["codarea"]
        uf_codigo = codarea[:2]  # 2 primeiros digitos = codigo da UF no IBGE

        geometria = feature["geometry"]
        coords_lista = geometria["coordinates"]

        # Poligonos podem ser "Polygon" (lista simples) ou "MultiPolygon"
        # (lista de listas) - achatamos tudo em uma lista unica de pontos
        pontos = []
        if geometria["type"] == "Polygon":
            for anel in coords_lista:
                pontos.extend(anel)
        elif geometria["type"] == "MultiPolygon":
            for poligono in coords_lista:
                for anel in poligono:
                    pontos.extend(anel)

        for lon, lat in pontos:
            if uf_codigo not in bboxes:
                bboxes[uf_codigo] = {"min_lat": lat, "max_lat": lat, "min_lon": lon, "max_lon": lon}
            else:
                b = bboxes[uf_codigo]
                b["min_lat"] = min(b["min_lat"], lat)
                b["max_lat"] = max(b["max_lat"], lat)
                b["min_lon"] = min(b["min_lon"], lon)
                b["max_lon"] = max(b["max_lon"], lon)

    return bboxes


def calcular_centro_e_zoom(bbox: dict) -> tuple[dict, float]:
    """Deriva o centro e um nivel de zoom aproximado a partir de uma bbox."""
    centro = {
        "lat": (bbox["min_lat"] + bbox["max_lat"]) / 2,
        "lon": (bbox["min_lon"] + bbox["max_lon"]) / 2,
    }
    extensao = max(bbox["max_lat"] - bbox["min_lat"], bbox["max_lon"] - bbox["min_lon"])

    # Heuristica simples: quanto maior a extensao geografica do estado,
    # menor o zoom necessario para enxergar ele inteiro
    if extensao > 20:
        zoom = 3.5
    elif extensao > 10:
        zoom = 4.5
    elif extensao > 5:
        zoom = 5.5
    elif extensao > 2:
        zoom = 6.5
    else:
        zoom = 7.5

    return centro, zoom


# --- Corpo principal ---

st.title("💉 Radar de Risco Vacinal")
st.caption(
    "Score preditivo de risco de queda na cobertura vacinal infantil, por município e vacina "
    "— 2º Concurso de Reúso de Dados Abertos da CGU."
)

previsoes = carregar_previsoes()
malha = carregar_malha_geografica()
nomes_municipios = carregar_nomes_municipios()

# --- Estado inicial: caso de maior urgência nacional ---

if "select_municipio" not in st.session_state:
    caso_padrao = previsoes.nlargest(1, "indice_urgencia").iloc[0]
    uf_padrao = nomes_municipios.get(caso_padrao["codigo_municipio_pni"], "").split(" - ")[-1]
    st.session_state["select_uf"] = uf_padrao
    st.session_state["select_municipio"] = caso_padrao["codigo_municipio_pni"]
    st.session_state["select_vacina"] = caso_padrao["vacina"]


def selecionar_da_tabela(codigo: str, vacina: str):
    """Atualiza o estado do app quando uma linha da tabela é clicada —
    escreve DIRETO nas chaves dos widgets, não em um estado intermediário,
    porque o Streamlit ignora o parametro 'index' de um widget que ja tem
    'key' definida."""
    nome_completo = nomes_municipios.get(codigo, "")
    uf = nome_completo.split(" - ")[-1] if " - " in nome_completo else "??"
    st.session_state["select_uf"] = uf
    st.session_state["select_municipio"] = codigo
    st.session_state["select_vacina"] = vacina

col_urgencia, col_risco = st.columns(2)

with col_urgencia:
    st.markdown("**Por índice de urgência** *(risco × população impactada)*")
    top5_urgencia = previsoes.nlargest(5, "indice_urgencia")[
        ["codigo_municipio_pni", "vacina", "probabilidade_risco"]
    ].reset_index(drop=True)
    top5_urgencia["Município"] = top5_urgencia["codigo_municipio_pni"].map(nomes_municipios)
    top5_urgencia["Risco"] = top5_urgencia["probabilidade_risco"].apply(lambda x: f"{x:.0%}")

    evento_urgencia = st.dataframe(
        top5_urgencia[["Município", "vacina", "Risco"]].rename(columns={"vacina": "Vacina"}),
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tabela_urgencia",
    )
    if evento_urgencia.selection.rows:
        linha_idx = evento_urgencia.selection.rows[0]
        selecionar_da_tabela(
            top5_urgencia.loc[linha_idx, "codigo_municipio_pni"],
            top5_urgencia.loc[linha_idx, "vacina"],
        )

with col_risco:
    st.markdown("**Por risco absoluto** *(municípios mais graves, qualquer tamanho)*")
    top5_risco = previsoes.nlargest(5, "probabilidade_risco")[
        ["codigo_municipio_pni", "vacina", "probabilidade_risco"]
    ].reset_index(drop=True)
    top5_risco["Município"] = top5_risco["codigo_municipio_pni"].map(nomes_municipios)
    top5_risco["Risco"] = top5_risco["probabilidade_risco"].apply(lambda x: f"{x:.0%}")

    evento_risco = st.dataframe(
        top5_risco[["Município", "vacina", "Risco"]].rename(columns={"vacina": "Vacina"}),
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="tabela_risco",
    )
    if evento_risco.selection.rows:
        linha_idx = evento_risco.selection.rows[0]
        selecionar_da_tabela(
            top5_risco.loc[linha_idx, "codigo_municipio_pni"],
            top5_risco.loc[linha_idx, "vacina"],
        )

st.divider()

# --- 3. Widgets de busca (agora usando st.session_state como fonte da verdade) ---

codigos_disponiveis = previsoes["codigo_municipio_pni"].unique()

opcoes_municipio = []
for codigo in codigos_disponiveis:
    nome_completo = nomes_municipios.get(codigo, f"Município {codigo}")
    uf = nome_completo.split(" - ")[-1] if " - " in nome_completo else "??"
    opcoes_municipio.append((codigo, nome_completo, uf))

ufs_disponiveis = sorted(set(uf for _, _, uf in opcoes_municipio))

col_filtro1, col_filtro2, col_filtro3 = st.columns(3)

with col_filtro1:
    uf_selecionada = st.selectbox("Estado (UF)", options=ufs_disponiveis, key="select_uf")

municipios_da_uf = sorted(
    [(codigo, nome) for codigo, nome, uf in opcoes_municipio if uf == uf_selecionada],
    key=lambda x: x[1],
)
codigos_da_uf = [codigo for codigo, nome in municipios_da_uf]

# Se o município salvo no estado nao pertence a UF atual (ex: acabou de
# trocar a UF manualmente), usa o primeiro município da lista como fallback
if st.session_state.get("select_municipio") not in codigos_da_uf:
    st.session_state["select_municipio"] = codigos_da_uf[0] if codigos_da_uf else None

with col_filtro2:
    codigo_selecionado = st.selectbox(
        "Município",
        options=codigos_da_uf,
        format_func=lambda codigo: dict(municipios_da_uf).get(codigo, codigo),
        key="select_municipio",
    )

vacinas_do_municipio = sorted(previsoes[
    previsoes["codigo_municipio_pni"] == codigo_selecionado
]["vacina"].unique())

if st.session_state.get("select_vacina") not in vacinas_do_municipio:
    st.session_state["select_vacina"] = vacinas_do_municipio[0] if vacinas_do_municipio else None

with col_filtro3:
    vacina_selecionada = st.selectbox("Vacina", options=vacinas_do_municipio, key="select_vacina")

# --- 4. Layout principal: esquerda (score + explicacao) | direita (mapa) ---

col_esquerda, col_direita = st.columns([1, 2])

with col_esquerda:
    linha_selecionada = previsoes[
        (previsoes["codigo_municipio_pni"] == codigo_selecionado) &
        (previsoes["vacina"] == vacina_selecionada)
    ]

    if linha_selecionada.empty:
        st.warning("Sem previsão disponível para essa combinação de município e vacina.")
    else:
        linha = linha_selecionada.iloc[0]
        risco = linha["probabilidade_risco"]

        st.metric(
            "Risco previsto (2026)",
            f"{risco:.1%}",
            help=(
                "Probabilidade estimada pelo modelo de que este município ficará "
                "abaixo da meta de cobertura em 2026, baseada em padrões históricos "
                "de cobertura, infraestrutura e características socioeconômicas. "
                "O modelo tem taxa de acerto de ~82% (AUC-ROC) — use como indicativo "
                "para priorização, não como certeza absoluta."
            ),
        )
        valor_formatado = f"{linha['nascidos_vivos']:,.0f}".replace(",", ".")
        st.metric("Nascidos vivos (2025)", valor_formatado)

        st.subheader("Por que esse score?")

        @st.cache_resource
        def obter_explainer():
            return carregar_explainer()

        with st.spinner("Calculando explicação..."):
            modelo, explainer, colunas_features = obter_explainer()
            explicacao = explicar_caso(explainer, colunas_features, linha, top_n=5)

        for item in explicacao:
            emoji = "🔺" if item["direcao"] == "aumenta" else "🔻"
            st.write(f"{emoji} **{item['nome_exibicao']}**: {item['direcao']} o risco em {abs(item['valor']):.3f}")

with col_direita:
    st.subheader(f"Mapa de risco — {vacina_selecionada}")

    correspondencia = montar_correspondencia_codigos(malha)
    bboxes_uf = calcular_bbox_por_uf(malha)

    # Descobre o codigo de UF (2 digitos) a partir do municipio selecionado,
    # para buscar a bbox correta e centralizar o mapa nesse estado
    codigo_uf_selecionada = codigo_selecionado[:2]
    bbox_selecionada = bboxes_uf.get(codigo_uf_selecionada)

    if bbox_selecionada:
        centro, zoom = calcular_centro_e_zoom(bbox_selecionada)
    else:
        centro, zoom = {"lat": -14.2, "lon": -51.9}, 3.0

    df_mapa = previsoes[previsoes["vacina"] == vacina_selecionada].copy()
    df_mapa["codarea"] = df_mapa["codigo_municipio_pni"].map(correspondencia)
    df_mapa = df_mapa.dropna(subset=["codarea"])
    df_mapa["nome_municipio"] = df_mapa["codigo_municipio_pni"].map(nomes_municipios)

    fig = px.choropleth_map(
        df_mapa,
        geojson=malha,
        locations="codarea",
        featureidkey="properties.codarea",
        color="probabilidade_risco",
        color_continuous_scale=["#e0e0e0", "#f4a261", "#e63946", "#9d0208"],
        range_color=(0, 1),
        map_style="carto-darkmatter",
        zoom=zoom,
        center=centro,
        opacity=0.7,
        labels={"probabilidade_risco": "Risco previsto"},
        hover_name="nome_municipio",
        hover_data={"codarea": False},
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=550)

    # scrollZoom=True permite dar zoom com a roda do mouse direto no mapa
    # (sem isso, o Streamlit intercepta o scroll para rolar a pagina)
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    st.caption(
        "💡 Use a roda do mouse para dar zoom, ou arraste para navegar. "
        "O mapa centraliza automaticamente no estado selecionado no filtro acima."
    )