"""
Extração de PIB municipal via API SIDRA (só o PIB total, variável 37) —
o per capita é calculado depois, dividindo pela população que já temos
extraída (evita depender de outro código de variável não confirmado).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_RAW

import requests
import pandas as pd

URL = "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/last"


def get_pib_municipios() -> pd.DataFrame:
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    dados = resp.json()

    df = pd.DataFrame(dados[1:])
    df = df.rename(columns={
        "D1C": "codigo_municipio_ibge",
        "D1N": "nome_municipio",
        "V": "pib_mil_reais",
        "D3N": "ano",
    })[["codigo_municipio_ibge", "nome_municipio", "pib_mil_reais", "ano"]]

    df["pib_mil_reais"] = pd.to_numeric(df["pib_mil_reais"], errors="coerce")
    df["codigo_municipio_pni"] = df["codigo_municipio_ibge"].astype(str).str[:6]
    return df


if __name__ == "__main__":
    df = get_pib_municipios()
    print(f"Total de municípios: {len(df)}")
    print(f"Ano dos dados: {df['ano'].unique()}")
    print(df.head())

    caminho_saida = DATA_RAW / "pib_municipios.csv"
    df.to_csv(caminho_saida, index=False)
    print(f"\nSalvo: {caminho_saida}")