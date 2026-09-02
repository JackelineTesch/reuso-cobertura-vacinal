# Radar de Risco Vacinal — Priorização preditiva de municípios em queda de cobertura vacinal infantil

Projeto de reúso de dados abertos submetido ao **2º Concurso de Reúso de Dados Abertos da CGU** (Edital CGU nº 46/2026).

## O problema

O Brasil vem apresentando queda sustentada na cobertura vacinal infantil desde 2019, com forte
heterogeneidade entre municípios vizinhos e risco de reintrodução de doenças já eliminadas
(sarampo, poliomielite). Painéis oficiais existentes (ImunizaSUS, Painel RNDS) **descrevem** essa
queda, mas não **priorizam** onde agir. Este projeto fecha essa lacuna: gera um score de risco
por município, prevendo quais têm maior probabilidade de cair abaixo da meta de cobertura (95%)
no próximo ciclo, e um ranking de urgência que combina esse risco com a população impactada —
para orientar gestores sobre onde uma campanha extra teria o maior efeito por real investido.

**Entrega:** app interativo em Streamlit (não painel de BI) — decisão registrada em
`reports/decisoes_tecnicas.md`. Motivo principal: o modelo preditivo e a explicação
SHAP por município precisam rodar ao vivo, algo que ferramentas de BI tradicionais
não fazem sem contorno. Streamlit também mantém a entrega 100% em código Python,
reforçando o critério de replicabilidade do edital (mesmo repositório do pipeline).

## Como o projeto atende aos critérios de julgamento do edital (item 8.2)

| Critério | Peso | Como este projeto atende |
|---|---|---|
| Relevância e impacto | 2 | Score de risco antecipa queda *antes* que aconteça, não só relata depois |
| Benefício para sociedade/economia | 2 | Ranking de urgência direciona recurso público escasso (campanhas de vacinação) para onde tem maior efeito |
| Inovação e originalidade | 1 | Modelo preditivo com interpretabilidade (SHAP), não só dashboard descritivo — diferencia de painéis oficiais existentes |
| Apresentação e usabilidade | 1 | App Streamlit interativo com mapa de risco, ranking e explicação SHAP ao vivo por município |
| Replicabilidade e escalabilidade | 1 | Pipeline modular e código aberto no GitHub; método generalizável a outras doenças/imunobiológicos |

## Fontes de dados abertos (todas de sítio oficial do governo federal — item 6.3 do edital)

- **Doses aplicadas do PNI por município/ano** (base para calcular cobertura) — Portal de Dados Abertos do SUS / OpenDataSUS (CKAN, CSV), 2020-2025. *Trocamos do TabNet clássico para cá: o TabNet está com links quebrados e o DATASUS avisa que os dados de cobertura estão em revisão — ver `reports/decisoes_tecnicas.md`.*
- **Infraestrutura de saúde (nº de UBS por município)** — CNES/DATASUS
- **Indicadores socioeconômicos (renda, IDHM, % população rural)** — IBGE / Atlas do Desenvolvimento Humano
- **Malha geográfica dos municípios** — IBGE
- **População-alvo por município** — IBGE (usada como denominador para calcular cobertura a partir das doses aplicadas)

**Limitação conhecida:** os datasets do OpenDataSUS só cobrem 2020 em diante — não achamos ainda uma fonte aberta em CSV para 2015-2019. Isso desloca o início da nossa série histórica; vamos decidir juntas o corte de anos ao montar as features.

## Arquitetura

```
data/raw/          # dados brutos baixados (não versionados no git — ver .gitignore)
data/processed/     # dados tratados, prontos para features/modelagem (DuckDB)
src/extract/        # scripts de extração por fonte
src/features/        # engenharia de atributos (tendência, taxa de variação, per capita)
src/models/         # treino, validação temporal, inferência
src/app/             # app Streamlit (mapa de risco, ranking, explicação SHAP)
notebooks/           # exploração e validação de hipóteses
reports/             # documentação de metodologia para a submissão no edital
```

## Status

- [x] Estrutura do projeto
- [x] Extração: OpenDataSUS (doses PNI)
- [x] Extração: IBGE (população) + SINASC (nascidos vivos)
- [x] Cálculo de cobertura vacinal por município/ano/vacina
- [x] Extração: CNES (UBS + Postos de Saúde por município)
- [x] Indicador socioeconômico: PIB per capita municipal (substituindo IDHM)
- [x] Engenharia de atributos
- [x] Modelo preditivo (baseline + comparação)
- [x] Previsões de risco 2026 + índice de urgência
- [x] Interpretabilidade (SHAP)
- [x] Malha geográfica dos municípios (para o mapa no app Streamlit)
- [ ] App Streamlit
- [ ] Cadastro da iniciativa em dados.gov.br como caso de reúso