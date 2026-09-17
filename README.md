# DEGIA — Sistema Inteligente para Avaliação Técnico-Econômica de Projetos Fotovoltaicos

**Versão documentada:** MVP 0.7 — protótipo acadêmico em desenvolvimento.

O DEGIA realiza uma pré-análise de cenários fotovoltaicos em uma rede de teste IEEE 13-Bus. Integra cadastro de projetos e cenários, simulação elétrica com OpenDSS, previsão de tensão por modelo de aprendizado de máquina e avaliação de alternativas técnico-econômicas. **Não substitui estudos de conexão, medições de campo nem análises oficiais da distribuidora.**

> Este README descreve o comportamento observado no código e nos testes compartilhados. Os arquivos `docker-compose.yml`, `requirements.txt`, `schemas.py`, `models.py`, `alternativas.py` e `economico.py` não foram auditados integralmente nesta revisão; confirme detalhes de configuração e dependências nesses arquivos antes de distribuir o projeto.

## 1. Arquitetura e recursos

```text
Navegador (HTML, CSS e JavaScript; porta 5500)
          |
          | HTTP / JSON
          v
FastAPI (porta 8000)
  |-- PostgreSQL (Docker; porta 5433 no Mac)
  |-- IBGE / ANEEL (cadastro e listas de contingência)
  |-- Open-Meteo (irradiância meteorológica momentânea)
  |-- OpenDSS (rede IEEE 13-Bus)
  |-- Modelo ML (previsão de tensão)
  `-- Avaliação técnico-econômica de alternativas
```

O formulário de projeto permite selecionar UF e concessionária. O backend consulta fontes públicas e dispõe de listas locais de contingência quando elas estão indisponíveis. A tensão de referência precisa ser confirmada pelo usuário: UF e concessionária não determinam, sozinhas, a tensão real da instalação.

A irradiância obtida via Open-Meteo é uma **referência momentânea**, não um valor normativo ou uma série histórica de projeto. O nó de simulação pertence à rede elétrica modelada; não é inferido pela UF. O fator de potência é uma configuração do projeto/inversor.

## 2. Estrutura principal

```text
degia_v07/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── simulador.py
│   │   ├── previsao_ml.py
│   │   ├── alternativas.py
│   │   ├── economico.py
│   │   └── opendss/.../13Bus/IEEE13Nodeckt.dss
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── docker-compose.yml
```

A árvore acima apresenta os caminhos principais conhecidos; outros arquivos e diretórios podem existir na cópia local.

## 3. Requisitos e configuração local

Ambiente utilizado no desenvolvimento: macOS, Python com ambiente virtual, Docker com PostgreSQL e navegador. O backend utiliza `opendssdirect`, FastAPI e SQLAlchemy. Para a lista completa e versões exatas dos pacotes, consulte `backend/requirements.txt`.

Na pasta raiz do projeto:

```bash
cd ~/Downloads/degia_v07
docker compose up -d
docker ps
```

No ambiente local utilizado nos testes, o PostgreSQL está acessível em `localhost:5433` (porta interna do contêiner: `5432`), banco `degia`, usuário `degia_user`. **Não publique credenciais reais no repositório.** Configure a variável `DATABASE_URL` conforme o `docker-compose.yml` e o mecanismo de configuração do backend; caso exista um `.env.example`, use-o como modelo. Um exemplo de formato é:

```env
DATABASE_URL=postgresql+psycopg2://USUARIO:SENHA@localhost:5433/degia
```

Para preservar o banco existente, **não execute `docker compose down -v`**: a opção `-v` remove volumes associados à composição. O `main.py` contém migrações incrementais com `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para campos do MVP; `create_all` não substitui um sistema completo de migrações de esquema.

## 4. Executar o backend

Abra um Terminal:

```bash
cd ~/Downloads/degia_v07/backend
source .venv/bin/activate
uvicorn app.main:app --log-level debug
```

Se o ambiente virtual ainda não existir:

```bash
cd ~/Downloads/degia_v07/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --log-level debug
```

API: <http://127.0.0.1:8000> · Documentação interativa: <http://127.0.0.1:8000/docs> · Saúde: <http://127.0.0.1:8000/api/health>.

Se aparecer `address already in use`, a porta 8000 já está ocupada. Verifique o processo com `lsof -nP -iTCP:8000 -sTCP:LISTEN`; encerre apenas a instância antiga identificada, sem iniciar dois backends na mesma porta.

**Atenção ao OpenDSS no macOS:** as rotas que executam a simulação diretamente estão definidas como `async def` no código atual. Evite executar duas simulações simultaneamente: o módulo usa um estado global do OpenDSS e chama `ClearAll()` antes de carregar a rede.

## 5. Executar o frontend

Em **outro Terminal**:

```bash
cd ~/Downloads/degia_v07/frontend
python3 -m http.server 5500
```

Abra <http://127.0.0.1:5500>. Confirme que o Terminal está na pasta `degia_v07/frontend`, e não em uma versão anterior `degia_sistema/frontend`. Mantenha backend, frontend e PostgreSQL em execução durante o uso.

## 6. Fluxo de uso

1. **Projeto:** cadastre nome, UF, concessionária, potência FV instalada, carga local e tensão de referência confirmada. Os dados técnicos de rede/nó e fator de potência podem ser configurados ou herdados conforme a interface e o modelo do projeto.
2. **Cenário:** informe nome, geração FV, carga e irradiância (automática ou manual, conforme a tela). O código usa o nó de referência e o fator de potência do projeto. Não há campo de hora no fluxo atual.
3. **Simulação:** o backend carrega a IEEE 13-Bus, adiciona a carga ao nó escolhido, resolve o caso sem FV, adiciona o sistema FV e resolve novamente. Registra a tensão máxima das fases **do nó analisado**.
4. **Resultados:** o cenário salvo inclui tensão OpenDSS, previsão ML, diferença entre ambas e classificação de risco. O dashboard resume os cenários e apresenta avaliação de alternativas quando disponível.

### Regra de classificação atualmente implementada

A classificação é **interna ao DEGIA**, calculada com `tensao_fv_max_pu` retornada pelo OpenDSS para o nó analisado:

| Tensão máxima no nó | Classificação |
|---|---|
| Até 1,0500 pu (inclusive) | BAIXO |
| Acima de 1,0500 até 1,0591 pu (inclusive) | ATENÇÃO |
| Acima de 1,0591 pu | ALTO |

**Importante:** o limite de 1,0591 pu está fixado no código e ainda precisa de justificativa técnica documentada. Não deve ser apresentado como limite regulatório ou critério de aprovação da concessionária. A tensão em volts exibida pelo sistema é calculada multiplicando o valor em pu pela tensão de referência cadastrada; isso não substitui a verificação da base elétrica e da ligação fase-neutro/fase-fase.

### Limitações conhecidas da classificação

- O simulador mede a tensão máxima **no barramento selecionado**, não em todos os barramentos da rede. Uma sobretensão em outro nó pode não aparecer na classificação atual.
- A rede IEEE 13-Bus tem controles automáticos. Nos testes realizados, o regulador `reg2` passou do tap 8 para o 7 entre irradiâncias de 701 e 702 W/m² (FV 3.000 kW; carga 1.475 kW), e a tensão máxima no nó 675 caiu de aproximadamente 1,058230 para 1,052083 pu. Portanto, aumentar geração/irradiância não garante crescimento monotônico da tensão.
- Os testes compartilhados **não produziram um cenário ALTO**. Isso não comprova, isoladamente, erro do OpenDSS ou impossibilidade física; exige validação dos parâmetros, controles, medições da rede inteira e critério de risco.
- Uma falha de convergência no cadastro atualmente gera HTTP 500 e **não salva um cenário `NÃO CLASSIFICADO`**. O dashboard já contabiliza classificações ausentes/desconhecidas, mas isso não significa que a interface consiga cadastrá-las.
- Previsão ML e erro percentual devem ser avaliados em dados independentes. Erro médio no conjunto de treinamento não é uma medida de acurácia independente.

## 7. Endpoints relevantes

| Método e rota | Uso |
|---|---|
| `GET /api/health` | Verificação da API |
| `GET /api/ufs` | UFs, com contingência local |
| `GET /api/concessionarias?uf=SP` | Agentes/concessionárias por UF |
| `GET /api/tensoes-referencia?uf=SP&concessionaria=...` | Sugestões de tensão a confirmar |
| `GET /api/redes` | Redes disponíveis |
| `GET /api/redes/IEEE13/nos` | Nós da IEEE 13-Bus |
| `GET /api/localidades/referencia?uf=SP` | Irradiância momentânea de referência |
| `GET /api/projetos` | Projetos |
| `POST /api/projetos` | Cadastro de projeto |
| `GET /api/projetos/{id}/cenarios` | Cenários do projeto |
| `POST /api/projetos/{id}/cenarios` | Criação e simulação de cenário |
| `POST /api/projetos/{id}/cenarios/gerar-automaticamente` | Geração de lote de cenários |
| `GET /api/projetos/{id}/dashboard` | Resumo do projeto |
| `GET /api/projetos/{id}/dataset.csv` | Exportação de cenários com resultado |
| `POST /api/avaliar-alternativas` | Avaliação técnico-econômica |
| `POST /api/simular` | Simulação diagnóstica, sem cadastro |
| `POST /api/prever-tensao` | Previsão por ML |
| `POST /api/comparar-opendss-ml` | Comparação dos resultados |

**Correção em relação ao README antigo:** o endpoint de localidade no `main.py` recebe apenas `uf`; não envie `municipio` como parâmetro obrigatório. OpenDSS e ML **já estão integrados**, não são etapas futuras.

## 8. Diagnóstico seguro de simulação

O endpoint abaixo executa uma simulação **sem gravar no PostgreSQL**. O contrato atual de `/api/simular` não aceita `carga_kw`, portanto este exemplo usa carga zero e **não reproduz** um cenário com carga cadastrada:

```bash
curl -s -X POST http://127.0.0.1:8000/api/simular \
  -H 'Content-Type: application/json' \
  -d '{"no_rede":"675","potencia_fv_kw":3000,"irradiancia_w_m2":700,"fator_potencia":1.0}'
```

Para reproduzir exatamente um cenário com carga, use uma rotina de diagnóstico que chame `simular_cenario(..., carga_kw=...)` em um processo isolado, sem simulações concorrentes. Não altere taps ou parâmetros do circuito apenas para forçar uma classificação ALTO.

## 9. Próximas correções técnicas

- Validar a classificação usando a maior tensão de **toda a rede**, se esse for o indicador definido para o projeto, preservando também o valor do nó de conexão.
- Revisar e justificar tecnicamente os limiares de risco; separar critérios internos dos limites aplicáveis da distribuidora.
- Tratar entrada inválida e não convergência com respostas adequadas e, se for requisito, permitir registrar o estado `NÃO CLASSIFICADO` com motivo e sem tensão inventada.
- Verificar limites físicos de carga, FV e irradiância e registrar os estados dos controles/taps em diagnósticos reproduzíveis.
- Documentar a origem e as faixas do dataset, a divisão treino/teste e a avaliação independente do ML.

## 10. Fontes de dados e escopo

- **IBGE — API de Localidades:** lista de UFs.
- **ANEEL — Dados Abertos/PDD:** agentes associados à UF, com lista local de contingência.
- **Open-Meteo:** irradiância de onda curta atual para uma localidade representativa da UF; não é irradiância exata do endereço.
- **IEEE 13-Bus / OpenDSS:** circuito de teste utilizado na simulação elétrica.

Este repositório é um **protótipo acadêmico de apoio à pré-análise**. Os resultados e custos estimados dependem das hipóteses do modelo e não constituem laudo técnico, aprovação de acesso ou recomendação automática de investimento.
