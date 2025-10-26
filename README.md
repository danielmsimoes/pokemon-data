# Pokemon Data — ETL, Análises e Dashboard

Projeto de dados com foco em:
- Cliente de API com autenticação JWT
- Pipeline ETL (Extração, Transformação e Carga) em CSV
- Dashboard interativo em Streamlit para explorar resultados

Principais decisões
- Persistência em CSV no diretório `data/` com separador `;` e encoding `utf-8-sig` (compatível com Excel PT-BR)
- Tratamento de Rate Limit (HTTP 429) com backoff e pequenos intervalos entre páginas
- Endpoints parametrizados via `.env`
- Visualizações em português com foco em clareza e leitura rápida

## Estrutura

```
pokemon-data/
├─ src/
│  ├─ api/
│  │  ├─ client.py          # Cliente JWT (login, GET, paginação, backoff)
│  │  └─ __init__.py
│  ├─ etl/
│  │  ├─ pipeline.py        # ETL: extrai, transforma e salva CSVs
│  │  └─ __init__.py
│  ├─ analysis/
│  │  └─ metrics.py         # Utilitários de análise (win rate, tipos, etc.)
│  └─ config.py             # Carrega variáveis do .env e garante pasta data/
├─ data/                    # Saída dos CSVs (no .gitignore por padrão)
├─ streamlit_app.py         # Dashboard interativo
├─ run_client.py            # Script de teste rápido do cliente da API
├─ requirements.txt
├─ .gitignore
└─ .env                     # VARIÁVEIS LOCAIS (não versionar)
```

## Variáveis de ambiente (.env)

Você tem um arquivo de exemplo `.env.example`. Copie e ajuste conforme sua API:
Retire o `.example` deixe somente `.env`

Depois, edite `.env` preenchendo as credenciais e URLs:

```
API_BASE_URL=http://host:8000
API_LOGIN_ENDPOINT=/login
 API_USERNAME=seu_usuario
 API_PASSWORD=sua_senha

# Endpoints de dados
HEALTH_ENDPOINT=/health
POKEMON_ENDPOINT=/pokemon
POKEMON_ATTRIBUTES_ENDPOINT=/pokemon/{pokemon_id}
 COMBATS_ENDPOINT=/combats

# Persistência
DATA_DIR=data


Observações:
- O arquivo `.env` está no `.gitignore` e não deve ser versionado.
- O `.env.example` existe apenas para documentar as variáveis necessárias e facilitar a configuração local.
```

## Setup rápido

1) Ambiente virtual e dependências
```
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

2) Configure o `.env` (ver seção acima) e deixe `.env` fora do Git.

## Executar o ETL

Roda extração e salva CSVs em `data/` (paginação padrão de 50 itens por página):
```
python -m src.etl.pipeline
```

Gera arquivos:
- `data/pokemons.csv` (colunas: id;name)
- `data/combats.csv` (first_pokemon;second_pokemon;winner — nomes já mapeados)
- `data/pokemon_attributes.csv` (atributos completos por Pokémon; necessário para análises por tipo/atributos)


## Executar o dashboard

```
streamlit run streamlit_app.py
```

Páginas disponíveis
- Visão Geral
  - Amostras de Pokémons (id fixo à esquerda) e Combates
  - Botões de download CSV
  - Vencedor do combate destacado (verde e negrito)
- Nº de Participações em Combates
  - Filtro “Mais/Menos participações” e “Quantidade exibida”
- Taxa de Vitória
  - Ordena por taxa de vitória ou por derrotas (comutador “Mostrar quem mais perdeu”)
  - Tabela traduzida com “Taxa de Vitória (%)” formatada
- Informações por Tipo
  - Gráfico consolidado com os 18 tipos oficiais (sem combinações), barras horizontais, rótulo com % e cores temáticas por tipo
  - Seletor de tipo (EN) + métrica (wins/losses/overall) com top da categoria
- Análises Interativas de Atributos
  - Top 10 por atributo (inclui coluna overall na tabela quando aplicável)
  - Top 10 por geração e atributo

