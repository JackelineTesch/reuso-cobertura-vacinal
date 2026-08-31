"""
Extração de dados populacionais por município via API SIDRA (IBGE).

DECISÃO REGISTRADA (ver reports/decisoes_tecnicas.md): a tabela 6579
(estimativas populacionais anuais) não tem dado para 2023 — o IBGE
pausou essa série durante a transição do Censo 2022. Para 2023, usamos
o próprio Censo 2022 (tabela 4714) como aproximação, assumindo que a
população não muda significativamente de um ano para o outro na maioria
dos municípios. Para 2024 e 2025, a tabela 6579 volta a ter estimativas
normais.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_RAW

import requests
import pandas as pd

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"


def _parse_resposta_sidra(dados: list, ano_referencia: int) -> pd.DataFrame:
    """Converte a resposta bruta da API SIDRA (lista de dicts) em DataFrame."""
    if len(dados) <= 1:
        raise ValueError(f"Sem dados retornados pela API para o ano {ano_referencia}.")

    df = pd.DataFrame(dados[1:])
    df = df.rename(columns={
        "D1C": "codigo_municipio_ibge",
        "D1N": "nome_municipio",
        "V": "populacao",
    })[["codigo_municipio_ibge", "nome_municipio", "populacao"]]
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
    df["ano"] = ano_referencia
    df["codigo_municipio_pni"] = df["codigo_municipio_ibge"].astype(str).str[:6]
    return df


def get_populacao_estimativa(ano: str) -> pd.DataFrame:
    """Tabela 6579 — estimativas populacionais anuais (não cobre 2022-2023)."""
    url = f"{SIDRA_BASE}/t/6579/n6/all/v/9324/p/{ano}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return _parse_resposta_sidra(resp.json(), ano_referencia=int(ano))


def get_populacao_censo_2022() -> pd.DataFrame:
    """Tabela 4714 — Censo Demográfico 2022, usado como aproximação p/ 2023."""
    url = f"{SIDRA_BASE}/t/4714/n6/all/v/93/p/2022"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = _parse_resposta_sidra(resp.json(), ano_referencia=2022)
    df["ano"] = 2023  # marca como aproximação para 2023
    df["fonte"] = "censo_2022_aproximacao"
    return df


if __name__ == "__main__":
    resultados = []

    print("Buscando população de 2023 (via Censo 2022, aproximação)...")
    pop_2023 = get_populacao_censo_2022()
    resultados.append(pop_2023)
    print(f"  {len(pop_2023)} municípios")

    for ano in ["2024", "2025"]:
        print(f"Buscando população de {ano}...")
        pop = get_populacao_estimativa(ano=ano)
        pop["fonte"] = "estimativa_anual"
        resultados.append(pop)
        print(f"  {len(pop)} municípios")

    todos = pd.concat(resultados, ignore_index=True)
    caminho_saida = DATA_RAW / "ibge_populacao_2023_2025.csv"
    todos.to_csv(caminho_saida, index=False)
    print(f"\nSalvo: {caminho_saida} ({len(todos)} linhas no total)")
    print(todos.head())