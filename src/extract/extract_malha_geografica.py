"""
Extração da malha geográfica (contornos dos municípios) via API do IBGE,
uma chamada por estado (27 no total) — cada chamada já traz todos os
municípios daquele estado de uma vez (parâmetro intrarregiao=municipio).

Usado para o mapa de risco no app Streamlit.
"""

import json
import requests
import time
from pathlib import Path

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", 
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO"
]

DATA_RAW = Path("data/raw/malhas")
CAMINHO_SAIDA = Path("data/processed/malha_municipios_brasil.geojson")

def baixar_malha_uf(uf: str) -> dict:
    url = f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}?formato=application/vnd.geo+json&intrarregiao=municipio"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    todas_features = []

    for uf in UFS:
        caminho_uf = DATA_RAW / f"malha_{uf}.geojson"

        if caminho_uf.exists():
            print(f"{uf}: ja baixado, reaproveitando.")
            with open(caminho_uf, encoding="utf-8") as f:
                dados_uf = json.load(f)
        else:
            print(f"{uf}: baixando...")
            dados_uf = baixar_malha_uf(uf)
            with open(caminho_uf, "w", encoding="utf-8") as f:
                json.dump(dados_uf, f)
            time.sleep(1) # pausa entre chamadas, para não sobrecarregar a API

        features_uf = dados_uf.get("features", [])
        print(f"   {len(features_uf)} municipios")
        todas_features.extend(features_uf)

    malha_completa = {
        "type": "FeatureCollection",
        "features": todas_features
    }    

    with open(CAMINHO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(malha_completa, f)

    print(f"Salvo: {CAMINHO_SAIDA}")
    print(f"Total de municípios: {len(todas_features)}")

