"""
Reduz o tamanho da malha geografica removendo pontos redundantes de cada
poligono (mantendo 1 a cada N pontos) -- ataca a causa real do peso, que
e a quantidade de pontos por contorno, nao a precisao decimal.
"""
import json
from pathlib import Path

CAMINHO_ENTRADA = Path("data/processed/malha_municipios_brasil.geojson")
CAMINHO_SAIDA = Path("data/processed/malha_municipios_brasil_simplificada.geojson")

CASAS_DECIMAIS = 4
MANTER_1_A_CADA = 4  # mantem 25% dos pontos de cada contorno


def simplificar_anel(anel: list) -> list:
    """Mantem 1 a cada N pontos, sempre preservando o primeiro e o
    ultimo (para o poligono continuar fechado corretamente)."""
    if len(anel) <= 4:
        return anel  # poligonos muito pequenos, nao vale simplificar

    pontos_reduzidos = anel[::MANTER_1_A_CADA]
    if pontos_reduzidos[-1] != anel[-1]:
        pontos_reduzidos.append(anel[-1])  # garante que fecha certo

    return [[round(c, CASAS_DECIMAIS) for c in ponto] for ponto in pontos_reduzidos]


def simplificar_geometria(geometria: dict) -> dict:
    if geometria["type"] == "Polygon":
        geometria["coordinates"] = [simplificar_anel(anel) for anel in geometria["coordinates"]]
    elif geometria["type"] == "MultiPolygon":
        geometria["coordinates"] = [
            [simplificar_anel(anel) for anel in poligono]
            for poligono in geometria["coordinates"]
        ]
    return geometria


with open(CAMINHO_ENTRADA, encoding="utf-8") as f:
    malha = json.load(f)

for feature in malha["features"]:
    feature["geometry"] = simplificar_geometria(feature["geometry"])

with open(CAMINHO_SAIDA, "w", encoding="utf-8") as f:
    json.dump(malha, f, separators=(",", ":"))

tamanho_original = CAMINHO_ENTRADA.stat().st_size / 1_000_000
tamanho_novo = CAMINHO_SAIDA.stat().st_size / 1_000_000
print(f"Original: {tamanho_original:.1f} MB")
print(f"Simplificado: {tamanho_novo:.1f} MB")
print(f"Reducao: {(1 - tamanho_novo/tamanho_original)*100:.0f}%")