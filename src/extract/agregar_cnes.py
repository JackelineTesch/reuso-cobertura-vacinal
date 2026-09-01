"""
Agrega o CNES: conta UBS (TP_UNIDADE == "2") por município, usando
leitura em streaming (ijson) para não carregar os 642MB na memória.
"""

import ijson
import pandas as pd
from pathlib import Path
from collections import Counter

CAMINHO_CNES = Path("data/raw/cnes_estabelecimentos.json")
CAMINHO_SAIDA = Path("data/processed/infraestrutura_saude_por_municipio.csv")

CODIGO_UBS = "2"  # Centro de Saúde/ Unidade Básica de Saúde
CODIGO_POSTO = "1"  # Posto de Saúde

contagem_ubs = Counter()
contagem_posto = Counter()

with open(CAMINHO_CNES, "rb") as f:
    items = ijson.items(f, "item", use_float=True)

    for i, item in enumerate(items, start=1):
        tipo = item.get("TP_UNIDADE")
        codigo_ibge = item.get("CO_IBGE")
        if not codigo_ibge:
            continue  # Ignora registros sem código IBGE

        if tipo == CODIGO_UBS:
            contagem_ubs[codigo_ibge] += 1
        elif tipo == CODIGO_POSTO:
            contagem_posto[codigo_ibge] += 1

        if i % 100_000 == 0:
            print(f"  {i:,} registros processados...")

# Junta os dois contadores em um DataFrame, mantendo separado + total
todos_municipios = set(contagem_ubs.keys()).union(contagem_posto.keys())
linhas = []
for codigo_municipio_pni in todos_municipios:
    num_ubs = contagem_ubs.get(codigo_municipio_pni, 0)
    num_postos = contagem_posto.get(codigo_municipio_pni, 0)
    linhas.append({
        "codigo_municipio_pni": codigo_municipio_pni,
        "num_ubs": num_ubs,
        "num_postos_saude": num_postos,
        "num_infraestrutura_basica": num_ubs + num_postos,
    })

resultado = pd.DataFrame(linhas)
resultado.to_csv(CAMINHO_SAIDA, index=False)

print(f"\n Salvo: {CAMINHO_SAIDA}")
print(f"  Total de municípios: {len(resultado):,}")
print(f"  Total de UBS: {resultado['num_ubs'].sum():,}")
print(f"  Total de Postos de Saúde: {resultado['num_postos_saude'].sum():,}")
print(resultado.sort_values("num_infraestrutura_basica", ascending=False).head())