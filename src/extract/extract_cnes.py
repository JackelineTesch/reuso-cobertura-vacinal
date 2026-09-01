"""
Extração de CNES (Cadastro Nacional de Estabelecimentos de Saúde) - usado 
para contar número de UBS/estabelecimentos de saúde por município
"""

import sys
import zipfile  
import json
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_RAW

URL = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/cnes_estabelecimentos_json.zip"

def baixar_e_extrair() -> Path:
    caminho_zip = DATA_RAW / "cnes_estabelecimentos.zip"
    print(f"Baixando: {URL}")
    with requests.get(URL, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(caminho_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    with zipfile.ZipFile(caminho_zip) as z:
        z.extractall(DATA_RAW)
        nome_arquivo = z.namelist()[0]

    return DATA_RAW / nome_arquivo

if __name__ == "__main__":
    caminho = baixar_e_extrair()
    print(f"Arquivo extraído em: {caminho}")
    print(f"Tamanho {caminho.stat().st_size / 1_000_000:.2f} MB")

    with open(caminho, encoding="utf-8") as f:
        trecho = f.read(1000)
    print("\nPrimeiros 1000 caracteres do arquivo extraído:")
    print(trecho)

    