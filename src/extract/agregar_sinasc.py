"""
Agrega nascidos vivos por município de residência e ano — população-alvo
para o cálculo de cobertura vacinal infantil.
"""
import pandas as pd
from pathlib import Path

ANOS = [2023, 2024, 2025]
DATA_RAW = Path("data/raw")

agregados = []

for ano in ANOS:
    caminho_csv = DATA_RAW / f"SINASC_{ano}.csv"
    if not caminho_csv.exists():
        print(f"Arquivo de {ano} não encontrado, pulando.")
        continue

    print(f"Processando {ano}...")
    leitor = pd.read_csv(
        caminho_csv, sep=";", encoding="utf-8",
        usecols=["CODMUNRES"], chunksize=200_000,
    )

    contagem_ano = pd.Series(dtype=int)
    for bloco in leitor:
        contagem_bloco = bloco["CODMUNRES"].value_counts()
        contagem_ano = contagem_ano.add(contagem_bloco, fill_value=0)

    df_ano = contagem_ano.reset_index()
    df_ano.columns = ["codigo_municipio_pni", "nascidos_vivos"]
    df_ano["codigo_municipio_pni"] = df_ano["codigo_municipio_pni"].astype(int).astype(str)
    df_ano["ano"] = ano
    agregados.append(df_ano)
    print(f"  {len(df_ano)} municípios, {df_ano['nascidos_vivos'].sum():.0f} nascimentos totais")

resultado = pd.concat(agregados, ignore_index=True)
caminho_saida = Path("data/processed/nascidos_vivos_2023_2025.csv")
resultado.to_csv(caminho_saida, index=False)
print(f"\nSalvo: {caminho_saida}")
print(resultado.head(10))