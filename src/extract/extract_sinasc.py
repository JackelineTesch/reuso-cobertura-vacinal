"""
Extração de nascidos vivos por município/ano (SINASC) — usado como
população-alvo real para calcular cobertura vacinal infantil (doses
aplicadas ÷ nascidos vivos), em vez de população total do município.

DECISÃO REGISTRADA (ver reports/decisoes_tecnicas.md): a primeira versão
do cálculo de cobertura usava população total como denominador, o que
gerou coberturas absurdamente baixas (~1%) — porque vacinas infantis são
aplicadas só em recém-nascidos, uma fração pequena da população total.
"""
import sys
import zipfile
import requests
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import DATA_RAW

S3_BASE = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINASC/csv"
ANOS = [2023, 2024, 2025]


def baixar_e_extrair_ano(ano: int) -> Path | None:
    url = f"{S3_BASE}/SINASC_{ano}_csv.zip"
    caminho_zip = DATA_RAW / f"sinasc_{ano}.zip"

    print(f"Baixando: {url}")
    try:
        with requests.get(url, stream=True, timeout=180) as r:
            r.raise_for_status()
            with open(caminho_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.HTTPError as e:
        print(f"  AVISO: não encontrado para {ano} ({e}). Pulando.")
        return None

    with zipfile.ZipFile(caminho_zip) as z:
        z.extractall(DATA_RAW)
        nome_csv = z.namelist()[0]

    return DATA_RAW / nome_csv


if __name__ == "__main__":
    for ano in ANOS:
        caminho = baixar_e_extrair_ano(ano)
        if caminho:
            print(f"Extraído: {caminho}")
            # Só inspeciona o cabeçalho por enquanto — não sabemos ainda
            # os nomes exatos das colunas desse dataset
            with open(caminho, encoding="utf-8") as f:
                print("Cabeçalho:", f.readline())