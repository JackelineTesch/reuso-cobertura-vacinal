# Decisões técnicas do projeto

Registro do "porquê" por trás das escolhas de arquitetura — útil tanto para
a submissão do concurso (mostra maturidade técnica) quanto como prática de
documentação de engenharia real.

## 1. Fonte de dados: TabNet → OpenDataSUS (API CKAN) → download direto (S3)

**Tentativa 1 — TabNet:** abandonada. Links quebrados, e o DATASUS avisa
que os dados de cobertura estão "em fase de revisão".

**Tentativa 2 — API CKAN** (`opendatasus.saude.gov.br`, depois
`ckan-dadosabertos.saude.gov.br`): abandonada. Endpoints instáveis,
respostas em HTML em vez de JSON, alguns domínios bloqueados por robots.txt
até para ferramentas automatizadas.

**Solução final:** navegação manual no portal (`dadosabertos.saude.gov.br`)
revelou que os arquivos reais ficam num bucket S3 público, com padrão de
URL prev|| previsível por mês/ano: https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/PNI/csv/vacinacao_{mes}_{ano}_csv.zip

Elimina qualquer dependência de API — é download direto.

**Trade-off aceito:** sem API de filtro, baixamos o arquivo mensal
completo (todas as vacinas, Brasil inteiro) e filtramos localmente.

## 2. Formato do arquivo: JSON → CSV

JSON repete o nome de cada campo em cada um dos milhões de registros
(uma dose aplicada = um registro). CSV escreve o cabeçalho uma vez só —
mesmo dado, arquivo bem menor e mais rápido de processar.

## 3. Entrega: Power BI/Looker Studio → Streamlit

O diferencial do projeto (modelo preditivo + explicação SHAP por
município) precisa rodar ao vivo — BI tradicional não faz isso
nativamente. Streamlit também mantém a entrega 100% em Python, no mesmo
repositório do pipeline (reforça replicabilidade, peso 1 no edital).

## 4. Redução de escopo temporal: 2020-2025 → 2023-2025

**Motivo:** prazo do concurso (10/09). Cada mês de dados brutos tem ~1-7GB;
processar 6 anos (72 meses) era inviável no tempo disponível junto com o
resto do pipeline (features, modelo, app). Optamos por 3 anos como
equilíbrio entre robustez do modelo e viabilidade de prazo.

## 5. Processamento: DuckDB → pandas com leitura em blocos (chunks)

**Motivo:** o DuckDB foi bloqueado pelo Controle Inteligente de Aplicativos
do Windows (recurso de segurança que bloqueia binários compilados sem
assinatura reconhecida — não é específico do projeto, afeta qualquer
biblioteca Python com componente `.pyd`/`.dll`). Em vez de desativar uma
proteção de segurança do sistema, resolvemos com `pandas.read_csv(...,
chunksize=500_000)`, processando o CSV em blocos e descartando cada bloco
da memória depois de agregado — mesmo resultado, sem depender de binários
externos.

## 6. Encoding: latin1 → UTF-8

Primeira tentativa de leitura usou `encoding="latin1"` (padrão comum em
dados de governo brasileiro), mas gerou caracteres corrompidos
(mojibake — ex.: "Única" virou "Ãšnica"). O arquivo real do PNI é UTF-8.
Corrigido após inspeção direta do CSV gerado.

## 7. Cruzamento de município: código IBGE (7 dígitos) vs. PNI/DATASUS (6 dígitos)

O IBGE usa código de 7 dígitos (o último é dígito verificador); o
PNI/DATASUS historicamente grava só os 6 primeiros. Sem tratar isso, o
`join` entre doses aplicadas e população falharia silenciosamente (zero
correspondências, sem erro). Solução: truncar o código do IBGE para 6
dígitos (`codigo_municipio_pni = codigo_ibge[:6]`) em ambas as fontes
antes de cruzar.

## 8. Imunobiológicos: nomes descritivos → códigos reais do PNI

Os 4 imunobiológicos priorizados foram mapeados para os códigos reais
encontrados na coluna `sg_imunobiologico` do dataset (descoberta empírica,
listando valores únicos):
- Tríplice viral → `SCR` (Sarampo, Caxumba, Rubéola), 1ª Dose
- Poliomielite → `VIP` (vacina inativada, padrão atual do calendário), 3ª Dose
- BCG → `BCG`, dose única
- Hepatite B → `HB`, dose ao nascer

## 9. Meta de cobertura: 95% único → meta por vacina

A meta de 95% (PNI/OMS) não é uniforme: BCG tem meta de 90%, não 95%
(confirmado em fonte oficial do Ministério da Saúde). Corrigido de uma
constante única (`META_COBERTURA = 0.95`) para um dicionário por vacina
(`METAS_COBERTURA`), evitando viés no cálculo de risco para BCG.

## 10. População 2023: tabela SIDRA 6579 → Censo 2022 (tabela 4714) como aproximação

A tabela de estimativas populacionais anuais do IBGE (6579) não tem dado
para 2022/2023 — série pausada durante a transição do Censo 2022.
Usamos o próprio Censo 2022 (tabela 4714) como aproximação para 2023,
assumindo que a população não muda significativamente de um ano para o
outro na maioria dos municípios. Marcado explicitamente no dado
(`fonte = "censo_2022_aproximacao"`) para transparência.

## 11. Denominador de cobertura: população total → nascidos vivos (SINASC)

Primeira tentativa usou população total do município como denominador,
gerando coberturas irreais (~1%). Corrigido para usar nascidos vivos
(SINASC, mesmo padrão de download do PNI: bucket S3 público, dataset
anual). Limitação aceita: nascidos vivos são contados por município de
**residência** da mãe, enquanto as doses aplicadas foram agregadas por
município do **estabelecimento** de saúde — pode distorcer municípios
pequenos onde famílias se deslocam para vacinar em cidades maiores.
Não foi reprocessado por causa do custo de tempo (~150GB já processados);
declarado como limitação conhecida na submissão.

## 12. Cobertura pode ultrapassar 100%

Para vacinas com esquema de múltiplas doses ao longo da infância (ex.:
Poliomielite 3ª dose), usar nascidos vivos de um único ano-calendário como
denominador pode gerar cobertura >100% — porque crianças vacinadas num
ano podem ter nascido no ano anterior. Limitação metodológica conhecida
(mesmo problema enfrentado por estudos acadêmicos que usam ano-calendário
em vez de coorte de nascimento), não é erro de cálculo.

## 13. Denominador por ano-calendário vs. coorte de nascimento

O cálculo usa nascidos vivos do mesmo ano-calendário como denominador
para todas as vacinas, incluindo as aplicadas aos 12 meses (ex.: tríplice
viral) — reproduzindo a metodologia clássica do PNI. A literatura (ex.:
BVS/MS, "Denominadores para o cálculo de coberturas vacinais") documenta
que essa abordagem gera distorções conhecidas: crianças nascidas no fim
do ano são majoritariamente vacinadas no ano seguinte, inflando a
cobertura calculada (explica coberturas >100% observadas nos dados).
A correção ideal exigiria rastrear cada dose até a coorte de nascimento
real da criança (cruzamento individual PNI×SINASC por paciente), fora do
escopo deste projeto por restrição de prazo. Declarado como limitação
metodológica conhecida, consistente com a convenção oficial do PNI.