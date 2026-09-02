"""Testa se a API de malhas do IBGE traz os municipios individuais dentro
de uma unica chamada por estado, ou se precisariamos de uma chamada por
municipio (o que seria inviavel: 5.570 requisicoes)."""
import requests

url = "https://servicodados.ibge.gov.br/api/v3/malhas/estados/SE?formato=application/vnd.geo+json&intrarregiao=municipio"

resp = requests.get(url, timeout=30)
print("Status code:", resp.status_code)

if resp.status_code == 200:
    dados = resp.json()
    features = dados.get("features", [])
    print(f"Numero de features (poligonos) retornados: {len(features)}")
    if features:
        print("Exemplo de propriedades do primeiro poligono:")
        print(features[0].get("properties"))
else:
    print("Erro:", resp.text[:500])