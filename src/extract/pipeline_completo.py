"""
Pipeline completo de extração: baixa, filtra e agrega doses aplicadas do
PNI para os anos priorizados (2023-2025), mês a mês, apagando os arquivos
brutos (zip + csv extraído) logo após processar cada mês — senão os ~36
arquivos de até 7GB cada lotariam o disco.

Decisão de escopo (ver reports/decisoes_tecnicas.md): reduzimos de
2020-2025 para 2023-2025 por causa do prazo do concurso (10/09) — baixar
e processar 6 anos de dados granulares do Brasil inteiro não é viável
no tempo disponível.
"""
import sys
import zipfile
import requests
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import IMUNOBIOLOGICOS_PRIORITARIOS

S3_BASE = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv"
MESES = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}
ANOS = [2023, 2024, 2025]

COLUNAS_NECESSARIAS = [
    "co_municipio_estabelecimento",
    "sg_uf_estabelecimento",
    "sg_imunobiologico",
    "ds_tipo_dose",
]

SIGLAS_INTERESSE = {v["sigla"] for v in IMUNOBIOLOGICOS_PRIORITARIOS.values()}

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed/por_mes")
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def baixar_zip(ano: int, mes_nome: str) -> Path:
    url = f"{S3_BASE}/vacinacao_{mes_nome}_{ano}_csv.zip"
    caminho_zip = DATA_RAW / f"vacinacao_{mes_nome}_{ano}.zip"
    print(f"  Baixando: {url}")
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(caminho_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return caminho_zip


def processar_mes(ano: int, mes: int) -> None:
    mes_nome = MESES[mes]
    caminho_saida = DATA_PROCESSED / f"doses_{mes_nome}_{ano}.csv"

    # Pula se já processamos esse mês antes (permite retomar se cair a conexão)
    if caminho_saida.exists():
        print(f"[{ano}-{mes:02d}] Já processado, pulando.")
        return

    print(f"[{ano}-{mes:02d}] Iniciando...")

    try:
        caminho_zip = baixar_zip(ano, mes_nome)
    except requests.exceptions.HTTPError as e:
        print(f"  AVISO: não foi possível baixar {ano}-{mes:02d} ({e}). Pulando este mês.")
        return

    with zipfile.ZipFile(caminho_zip) as z:
        z.extractall(DATA_RAW)
        nome_csv = z.namelist()[0]
    caminho_csv = DATA_RAW / nome_csv

    agregados = []
    leitor = pd.read_csv(
        caminho_csv, sep=";", encoding="utf-8",
        usecols=COLUNAS_NECESSARIAS, chunksize=500_000,
    )
    for bloco in leitor:
        bloco_filtrado = bloco[bloco["sg_imunobiologico"].isin(SIGLAS_INTERESSE)]
        if len(bloco_filtrado) == 0:
            continue
        contagem = (
            bloco_filtrado.groupby(
                ["co_municipio_estabelecimento", "sg_uf_estabelecimento",
                 "sg_imunobiologico", "ds_tipo_dose"]
            ).size().reset_index(name="doses_aplicadas")
        )
        agregados.append(contagem)

    if agregados:
        resultado = (
            pd.concat(agregados)
            .groupby(["co_municipio_estabelecimento", "sg_uf_estabelecimento",
                       "sg_imunobiologico", "ds_tipo_dose"])["doses_aplicadas"]
            .sum().reset_index()
        )
        resultado["ano"] = ano
        resultado["mes"] = mes
        resultado.to_csv(caminho_saida, index=False)
        print(f"  Salvo: {caminho_saida} ({len(resultado)} linhas)")

    # Limpeza: apaga os arquivos brutos deste mês para não lotar o disco
    caminho_zip.unlink()
    caminho_csv.unlink()
    print(f"  Arquivos brutos de {ano}-{mes:02d} removidos.")


if __name__ == "__main__":
    for ano in ANOS:
        for mes in range(1, 13):
            processar_mes(ano, mes)

    print("\nConcluído. Consolidando todos os meses em um único arquivo...")
    todos = pd.concat(
        [pd.read_csv(f) for f in DATA_PROCESSED.glob("*.csv")],
        ignore_index=True,
    )
    caminho_final = Path("data/processed/doses_2023_2025.csv")
    todos.to_csv(caminho_final, index=False)
    print(f"Arquivo consolidado: {caminho_final} ({len(todos)} linhas)")