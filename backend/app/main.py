import csv
import io
import json

from app.economico import aplicar_analise_economica
from app.alternativas import avaliar_alternativas
from app.previsao_ml import prever_tensao_ml
from app.simulador import simular_cenario
from pydantic import BaseModel
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Cenario, Projeto
from .schemas import (
    CenarioCreate,
    CenarioResponse,
    DashboardResumo,
    GeracaoCenariosRequest,
    LocalidadeReferencia,
    ProjetoCreate,
    ProjetoResponse,
)

class AlternativasRequest(BaseModel):
    no_rede: str = "675"
    potencia_fv_kw: float
    irradiancia_w_m2: float
    carga_kw: float
    fator_potencia: float = 1.0

class PrevisaoMLRequest(BaseModel):
    potencia_fv_kw: float
    irradiancia_w_m2: float
    carga_kw: float

class ComparacaoRequest(BaseModel):
    potencia_fv_kw: float
    irradiancia_w_m2: float
    carga_kw: float
    no_rede: str = "675"
    fator_potencia: float = 1.0

class SimulacaoRequest(BaseModel):
    no_rede: str
    potencia_fv_kw: float
    irradiancia_w_m2: float
    fator_potencia: float = 1.0

# create_all cria tabelas novas, mas não altera tabelas antigas.
# As instruções abaixo permitem reaproveitar o banco do MVP 0.2 sem apagar o volume.
def executar_migracoes_mvp():
    comandos = [
        "ALTER TABLE projeto ADD COLUMN IF NOT EXISTS uf VARCHAR(2)",
        "ALTER TABLE projeto ADD COLUMN IF NOT EXISTS municipio VARCHAR(120)",
        "ALTER TABLE projeto ADD COLUMN IF NOT EXISTS fator_potencia DOUBLE PRECISION DEFAULT 1.0",
        "ALTER TABLE projeto ADD COLUMN IF NOT EXISTS rede_simulada VARCHAR(50) DEFAULT 'IEEE13'",
        "ALTER TABLE projeto ADD COLUMN IF NOT EXISTS no_rede_referencia VARCHAR(80) DEFAULT '675'",
        "ALTER TABLE cenario ADD COLUMN IF NOT EXISTS no_rede VARCHAR(80)",
        "ALTER TABLE cenario ADD COLUMN IF NOT EXISTS fator_potencia DOUBLE PRECISION",
    ]
    with engine.begin() as conn:
        for comando in comandos:
            conn.execute(text(comando))


Base.metadata.create_all(bind=engine)
executar_migracoes_mvp()

app = FastAPI(
    title="DEGIA API",
    description="API do Sistema Inteligente para Avaliação Técnico-Econômica de Projetos Fotovoltaicos",
    version="0.7.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Fallback local usado apenas se as APIs públicas estiverem indisponíveis.
UFS_FALLBACK = [
    {"sigla": "AC", "nome": "Acre"}, {"sigla": "AL", "nome": "Alagoas"},
    {"sigla": "AP", "nome": "Amapá"}, {"sigla": "AM", "nome": "Amazonas"},
    {"sigla": "BA", "nome": "Bahia"}, {"sigla": "CE", "nome": "Ceará"},
    {"sigla": "DF", "nome": "Distrito Federal"}, {"sigla": "ES", "nome": "Espírito Santo"},
    {"sigla": "GO", "nome": "Goiás"}, {"sigla": "MA", "nome": "Maranhão"},
    {"sigla": "MT", "nome": "Mato Grosso"}, {"sigla": "MS", "nome": "Mato Grosso do Sul"},
    {"sigla": "MG", "nome": "Minas Gerais"}, {"sigla": "PA", "nome": "Pará"},
    {"sigla": "PB", "nome": "Paraíba"}, {"sigla": "PR", "nome": "Paraná"},
    {"sigla": "PE", "nome": "Pernambuco"}, {"sigla": "PI", "nome": "Piauí"},
    {"sigla": "RJ", "nome": "Rio de Janeiro"}, {"sigla": "RN", "nome": "Rio Grande do Norte"},
    {"sigla": "RS", "nome": "Rio Grande do Sul"}, {"sigla": "RO", "nome": "Rondônia"},
    {"sigla": "RR", "nome": "Roraima"}, {"sigla": "SC", "nome": "Santa Catarina"},
    {"sigla": "SP", "nome": "São Paulo"}, {"sigla": "SE", "nome": "Sergipe"},
    {"sigla": "TO", "nome": "Tocantins"},
]

CONCESSIONARIAS_FALLBACK = {
    "AC": ["Energisa Acre"], "AL": ["Equatorial Alagoas"], "AP": ["CEA Equatorial"],
    "AM": ["Amazonas Energia"], "BA": ["Neoenergia Coelba"], "CE": ["Enel Ceará"],
    "DF": ["Neoenergia Brasília"], "ES": ["EDP Espírito Santo"], "GO": ["Equatorial Goiás"],
    "MA": ["Equatorial Maranhão"], "MT": ["Energisa Mato Grosso"],
    "MS": ["Energisa Mato Grosso do Sul"], "MG": ["Cemig Distribuição", "Energisa Minas Rio"],
    "PA": ["Equatorial Pará"], "PB": ["Energisa Paraíba"], "PR": ["Copel Distribuição"],
    "PE": ["Neoenergia Pernambuco"], "PI": ["Equatorial Piauí"],
    "RJ": ["Light", "Enel Distribuição Rio"], "RN": ["Neoenergia Cosern"],
    "RS": ["CEEE Equatorial", "RGE Sul"], "RO": ["Energisa Rondônia"],
    "RR": ["Roraima Energia"], "SC": ["Celesc Distribuição"],
    "SP": ["Enel São Paulo", "CPFL Paulista", "CPFL Piratininga", "EDP São Paulo", "Energisa Sul-Sudeste"],
    "SE": ["Energisa Sergipe"], "TO": ["Energisa Tocantins"],
}

IBGE_ESTADOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"
ANEEL_DATASTORE_URL = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
# Recurso público PDD/ANEEL. Possui SigAgente e SigUF e é usado para descobrir agentes por UF.
ANEEL_PDD_RESOURCE_ID = "30b8fbb7-4d7a-49d1-8985-97e9bb7d65e0"

# Referência meteorológica do MVP quando o projeto informa apenas a UF.
# Usamos a capital como ponto representativo da UF, deixando explícito que
# isso não equivale à irradiância exata do endereço do projeto.
CAPITAIS_UF = {
    "AC":"Rio Branco","AL":"Maceió","AP":"Macapá","AM":"Manaus","BA":"Salvador","CE":"Fortaleza",
    "DF":"Brasília","ES":"Vitória","GO":"Goiânia","MA":"São Luís","MT":"Cuiabá","MS":"Campo Grande",
    "MG":"Belo Horizonte","PA":"Belém","PB":"João Pessoa","PR":"Curitiba","PE":"Recife","PI":"Teresina",
    "RJ":"Rio de Janeiro","RN":"Natal","RS":"Porto Alegre","RO":"Porto Velho","RR":"Boa Vista",
    "SC":"Florianópolis","SP":"São Paulo","SE":"Aracaju","TO":"Palmas"
}


REDES = {
    "IEEE13": {
        "nome": "IEEE 13-Bus",
        "nos": ["sourcebus", "650", "632", "633", "634", "645", "646", "671", "675", "680", "684", "611", "652", "692"],
        "no_padrao": "675",
    }
}


def obter_projeto_ou_404(projeto_id: int, db: Session) -> Projeto:
    projeto = db.query(Projeto).filter(Projeto.id == projeto_id).first()
    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return projeto


def requisitar_json(url: str, timeout: int = 8):
    req = Request(url, headers={"User-Agent": "DEGIA-MVP/0.3"})
    with urlopen(req, timeout=timeout) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def buscar_irradiancia_atual(municipio: str, uf: str):
    """Busca geocodificação e radiação solar atual via Open-Meteo.

    O valor retornado é meteorológico e momentâneo. Ele NÃO é limite regulatório,
    nem substitui uma base solar de projeto. Serve para automatizar o MVP enquanto
    a estratégia definitiva de irradiância do dataset é definida.
    """
    try:
        geo_params = urlencode({
            "name": municipio,
            "count": 10,
            "language": "pt",
            "format": "json",
            "countryCode": "BR",
        })
        geo = requisitar_json(f"https://geocoding-api.open-meteo.com/v1/search?{geo_params}")
        resultados = geo.get("results") or []
        if not resultados:
            return None, None, None

        nome_uf = next((item["nome"] for item in UFS_FALLBACK if item["sigla"] == uf.upper()), None)
        escolhido = None
        if nome_uf:
            for item in resultados:
                admin1 = (item.get("admin1") or "").casefold()
                if item.get("country_code") == "BR" and admin1 == nome_uf.casefold():
                    escolhido = item
                    break
        if escolhido is None:
            escolhido = next((item for item in resultados if item.get("country_code") == "BR"), resultados[0])

        latitude = escolhido.get("latitude")
        longitude = escolhido.get("longitude")
        if latitude is None or longitude is None:
            return None, None, None

        meteo_params = urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "current": "shortwave_radiation",
            "timezone": "auto",
        })
        meteo = requisitar_json(f"https://api.open-meteo.com/v1/forecast?{meteo_params}")
        irradiancia = (meteo.get("current") or {}).get("shortwave_radiation")
        return latitude, longitude, irradiancia
    except Exception:
        return None, None, None


@app.get("/")
def inicio():
    return {
        "sistema": "DEGIA",
        "status": "online",
        "mensagem": "Back-end funcionando.",
        "versao": "0.7.0",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "api": "DEGIA"}


@app.get("/api/ufs")
def listar_ufs():
    """Carrega UFs pela API pública do IBGE, com fallback local."""
    try:
        dados = requisitar_json(IBGE_ESTADOS_URL, timeout=6)
        ufs = [
            {"id": item.get("id"), "sigla": item.get("sigla"), "nome": item.get("nome")}
            for item in dados
            if item.get("sigla") and item.get("nome")
        ]
        if ufs:
            return {
                "ufs": ufs,
                "fonte": "IBGE - API de Localidades",
                "fallback": False,
            }
    except Exception:
        pass

    return {
        "ufs": UFS_FALLBACK,
        "fonte": "Fallback local DEGIA (API IBGE indisponível)",
        "fallback": True,
    }


def buscar_concessionarias_aneel(sigla: str):
    filtros = json.dumps({"SigUF": sigla})
    params = urlencode({
        "resource_id": ANEEL_PDD_RESOURCE_ID,
        "limit": 5000,
        "filters": filtros,
    })
    dados = requisitar_json(f"{ANEEL_DATASTORE_URL}?{params}", timeout=10)
    if not dados.get("success"):
        return []
    registros = (dados.get("result") or {}).get("records") or []
    nomes = sorted({
        str(item.get("SigAgente") or "").strip()
        for item in registros
        if str(item.get("SigAgente") or "").strip()
    })
    return nomes


@app.get("/api/concessionarias")
def listar_concessionarias(uf: str = Query(min_length=2, max_length=2)):
    sigla = uf.strip().upper()
    if sigla not in {item["sigla"] for item in UFS_FALLBACK}:
        raise HTTPException(status_code=400, detail="UF inválida.")

    try:
        lista = buscar_concessionarias_aneel(sigla)
        if lista:
            return {
                "uf": sigla,
                "concessionarias": lista,
                "fonte": "ANEEL - Dados Abertos (PDD)",
                "fallback": False,
                "observacao": "Agentes encontrados em dados públicos da ANEEL para a UF selecionada.",
            }
    except Exception:
        pass

    lista = CONCESSIONARIAS_FALLBACK.get(sigla, [])
    return {
        "uf": sigla,
        "concessionarias": lista,
        "fonte": "Fallback local DEGIA (ANEEL indisponível)",
        "fallback": True,
        "observacao": "Lista de contingência usada apenas quando a consulta pública da ANEEL não responde.",
    }


@app.get("/api/tensoes-referencia")
def listar_tensoes_referencia(
    uf: str = Query(min_length=2, max_length=2),
    concessionaria: str = Query(min_length=1, max_length=160),
):
    """Sugere tensões usuais, mas exige confirmação do projeto.

    UF + distribuidora não determinam de forma única a tensão de atendimento de uma
    instalação. O valor final depende do padrão/local da conexão. Por isso o DEGIA
    sugere opções e não grava uma tensão 'oficial' automaticamente.
    """
    sigla = uf.strip().upper()
    if sigla not in {item["sigla"] for item in UFS_FALLBACK}:
        raise HTTPException(status_code=400, detail="UF inválida.")

    return {
        "uf": sigla,
        "concessionaria": concessionaria,
        "opcoes_v": [127, 220, 380],
        "sugerida_v": 220,
        "requer_confirmacao": True,
        "fonte": "Sugestão técnica do DEGIA",
        "observacao": (
            "A tensão não pode ser determinada com segurança apenas pela UF e pela distribuidora. "
            "Confirme a tensão real da instalação e se o valor é fase-neutro ou fase-fase."
        ),
    }


@app.get("/api/redes")
def listar_redes():
    return [
        {"codigo": codigo, "nome": dados["nome"], "no_padrao": dados["no_padrao"]}
        for codigo, dados in REDES.items()
    ]


@app.get("/api/redes/{rede_codigo}/nos")
def listar_nos_rede(rede_codigo: str):
    rede = REDES.get(rede_codigo.upper())
    if not rede:
        raise HTTPException(status_code=404, detail="Rede simulada não encontrada.")
    return {
        "rede": rede_codigo.upper(),
        "nome": rede["nome"],
        "nos": rede["nos"],
        "no_padrao": rede["no_padrao"],
        "observacao": "Os nós pertencem ao modelo elétrico simulado; não são inferidos pela UF do projeto.",
    }


@app.get("/api/localidades/referencia", response_model=LocalidadeReferencia)
def referencia_localidade(
    uf: str = Query(min_length=2, max_length=2),
):
    sigla = uf.upper()
    municipio = CAPITAIS_UF.get(sigla)
    if not municipio:
        raise HTTPException(status_code=400, detail="UF inválida.")
    latitude, longitude, irradiancia = buscar_irradiancia_atual(municipio, sigla)
    if irradiancia is None:
        return {
            "uf": sigla,
            "municipio": municipio,
            "latitude": latitude,
            "longitude": longitude,
            "irradiancia_w_m2": None,
            "fonte_irradiancia": "indisponível",
            "observacao": "Não foi possível consultar a irradiância agora. O cenário pode ser salvo sem esse valor e atualizado depois.",
        }

    return {
        "uf": sigla,
        "municipio": municipio,
        "latitude": latitude,
        "longitude": longitude,
        "irradiancia_w_m2": irradiancia,
        "fonte_irradiancia": "Open-Meteo - shortwave_radiation atual",
        "observacao": f"Referência meteorológica momentânea usando {municipio} como ponto representativo de {sigla}; não é irradiância exata do endereço nem valor normativo/de projeto.",
    }


@app.post("/api/projetos", response_model=ProjetoResponse, status_code=201)
def criar_projeto(dados: ProjetoCreate, db: Session = Depends(get_db)):
    projeto = Projeto(**dados.model_dump())
    db.add(projeto)
    db.commit()
    db.refresh(projeto)
    return projeto


@app.get("/api/projetos", response_model=list[ProjetoResponse])
def listar_projetos(db: Session = Depends(get_db)):
    return db.query(Projeto).order_by(Projeto.id.desc()).all()


@app.get("/api/projetos/{projeto_id}", response_model=ProjetoResponse)
def buscar_projeto(projeto_id: int, db: Session = Depends(get_db)):
    return obter_projeto_ou_404(projeto_id, db)

def executar_simulacao_cenario(
    projeto,
    geracao_fv_kw,
    irradiancia_w_m2,
    carga_kw
):
    no_rede = projeto.no_rede_referencia or "675"
    fator_potencia = projeto.fator_potencia or 1.0

    resultado_opendss = simular_cenario(
        no_rede=no_rede,
        potencia_fv_kw=geracao_fv_kw,
        irradiancia_w_m2=irradiancia_w_m2,
        carga_kw=carga_kw,
        fator_potencia=fator_potencia
    )

    tensao_inicial_pu = resultado_opendss["tensao_base_max_pu"]
    tensao_resultado_pu = resultado_opendss["tensao_fv_max_pu"]

    tensao_resultado_v = (
        tensao_resultado_pu
        * projeto.tensao_referencia_v
    )

    if tensao_resultado_pu <= 1.05:
        classificacao_risco = "BAIXO"
    elif tensao_resultado_pu <= 1.0591:
        classificacao_risco = "ATENÇÃO"
    else:
        classificacao_risco = "ALTO"


    resultado_ml = prever_tensao_ml(
                potencia_fv_kw=geracao_fv_kw,
                irradiancia_w_m2=irradiancia_w_m2,
                carga_kw=carga_kw
            )

    tensao_prevista_ml_pu = resultado_ml["tensao_prevista_pu"]

    erro_absoluto_ml_pu = abs(
        tensao_resultado_pu - tensao_prevista_ml_pu
    )

    erro_percentual_ml = (
        erro_absoluto_ml_pu / tensao_resultado_pu
    ) * 100


    return {
        "no_rede": no_rede,
        "fator_potencia": fator_potencia,
        "tensao_inicial_pu": tensao_inicial_pu,
        "tensao_resultado_pu": tensao_resultado_pu,
        "tensao_resultado_v": tensao_resultado_v,

        "tensao_prevista_ml_pu": tensao_prevista_ml_pu,
        "erro_absoluto_ml_pu": erro_absoluto_ml_pu,
        "erro_percentual_ml": erro_percentual_ml,

        "classificacao_risco": classificacao_risco,
        "origem_resultado": "OPENDSS",
    }

@app.post(
    "/api/projetos/{projeto_id}/cenarios",
    response_model=CenarioResponse,
    status_code=201
)
async def criar_cenario(
    projeto_id: int,
    dados: CenarioCreate,
    db: Session = Depends(get_db)
):
    projeto = obter_projeto_ou_404(projeto_id, db)

    if dados.irradiancia_w_m2 is None:
        raise HTTPException(
            status_code=400,
            detail="Informe a irradiância do cenário para executar a simulação OpenDSS."
        )

    # Se a geração do cenário não for informada,
    # utiliza a potência FV cadastrada no projeto.
    potencia_fv_kw = (
        dados.geracao_fv_kw
        if dados.geracao_fv_kw is not None
        else projeto.potencia_fv_kwp
    )

    # Se a carga do cenário não for informada,
    # utiliza a carga cadastrada no projeto.
    carga_cenario_kw = (
        dados.carga_kw
        if dados.carga_kw is not None
        else projeto.carga_local_kw
    )

    # Executa a simulação elétrica centralizada.
    try:
        resultado = executar_simulacao_cenario(
            projeto=projeto,
            geracao_fv_kw=potencia_fv_kw,
            irradiancia_w_m2=dados.irradiancia_w_m2,
            carga_kw=carga_cenario_kw
        )

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=f"Erro durante a simulação OpenDSS: {str(erro)}"
        )

    payload = dados.model_dump()

    # Entradas efetivamente usadas na simulação.
    payload["carga_kw"] = carga_cenario_kw
    payload["geracao_fv_kw"] = potencia_fv_kw
    payload["no_rede"] = resultado["no_rede"]
    payload["fator_potencia"] = resultado["fator_potencia"]

    # Resultados calculados automaticamente.
    payload["tensao_inicial_pu"] = resultado["tensao_inicial_pu"]
    payload["tensao_resultado_pu"] = resultado["tensao_resultado_pu"]
    payload["tensao_resultado_v"] = resultado["tensao_resultado_v"]
    payload["tensao_prevista_ml_pu"] = resultado["tensao_prevista_ml_pu"]
    payload["erro_absoluto_ml_pu"] = resultado["erro_absoluto_ml_pu"]
    payload["erro_percentual_ml"] = resultado["erro_percentual_ml"]
    payload["origem_resultado"] = resultado["origem_resultado"]
    payload["classificacao_risco"] = resultado["classificacao_risco"]

    try:
        cenario = Cenario(
            projeto_id=projeto_id,
            **payload
        )

        db.add(cenario)
        db.commit()
        db.refresh(cenario)

        return cenario

    except Exception as erro:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar o cenário: {str(erro)}"
        )

# ============================================================
# ETAPA 7 - ANÁLISE TÉCNICO-ECONÔMICA DAS ALTERNATIVAS
# ============================================================

@app.post("/api/avaliar-alternativas")
async def avaliar_alternativas_endpoint(
    dados: AlternativasRequest
):
    try:
        resultado_tecnico = avaliar_alternativas(
            no_rede=dados.no_rede,
            potencia_fv_kw=dados.potencia_fv_kw,
            irradiancia_w_m2=dados.irradiancia_w_m2,
            carga_kw=dados.carga_kw,
            fator_potencia=dados.fator_potencia
        )

        resultado_completo = aplicar_analise_economica(
            resultado_tecnico
        )

        return resultado_completo

    except Exception as erro:
        raise HTTPException(
            status_code=500,
            detail=str(erro)
        )


@app.post("/api/projetos/{projeto_id}/cenarios/gerar-automaticamente")
async def gerar_cenarios_automaticamente(
    projeto_id: int,
    dados: GeracaoCenariosRequest,
    db: Session = Depends(get_db)
):
    projeto = obter_projeto_ou_404(projeto_id, db)

    total_combinacoes = (
        len(dados.geracoes_fv_kw)
        * len(dados.irradiancias_w_m2)
        * len(dados.cargas_kw)
    )

    if total_combinacoes == 0:
        raise HTTPException(
            status_code=400,
            detail="Informe pelo menos um valor de geração FV, irradiância e carga."
        )

    # ---------------------------------------------------------
    # Remove combinações eletricamente equivalentes.
    #
    # Potência FV efetiva:
    # geracao_fv_kw * irradiancia_w_m2 / 1000
    #
    # Se potência efetiva + carga forem iguais,
    # mantemos apenas uma combinação para simulação.
    # ---------------------------------------------------------

    combinacoes_unicas = []
    chaves_processadas = set()

    for geracao_fv_kw in dados.geracoes_fv_kw:
        for irradiancia_w_m2 in dados.irradiancias_w_m2:
            for carga_kw in dados.cargas_kw:

                potencia_fv_efetiva_kw = round(
                    float(geracao_fv_kw)
                    * float(irradiancia_w_m2)
                    / 1000.0,
                    6
                )

                chave = (
                    potencia_fv_efetiva_kw,
                    round(float(carga_kw), 6)
                )

                if chave in chaves_processadas:
                    continue

                chaves_processadas.add(chave)

                combinacoes_unicas.append({
                    "geracao_fv_kw": geracao_fv_kw,
                    "irradiancia_w_m2": irradiancia_w_m2,
                    "carga_kw": carga_kw,
                    "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw
                })

    total_combinacoes_unicas = len(combinacoes_unicas)

    if total_combinacoes_unicas > 500:
        raise HTTPException(
            status_code=400,
            detail=(
                "O limite atual é de 500 combinações elétricas "
                "únicas por lote."
            )
        )

    cenarios_gerados = []
    erros = []

    numero_cenario = 1

    for combinacao in combinacoes_unicas:

        geracao_fv_kw = combinacao["geracao_fv_kw"]
        irradiancia_w_m2 = combinacao["irradiancia_w_m2"]
        carga_kw = combinacao["carga_kw"]
        potencia_fv_efetiva_kw = combinacao["potencia_fv_efetiva_kw"]

        try:
            resultado = executar_simulacao_cenario(
                projeto=projeto,
                geracao_fv_kw=geracao_fv_kw,
                irradiancia_w_m2=irradiancia_w_m2,
                carga_kw=carga_kw
            )

            cenario = Cenario(
                projeto_id=projeto_id,
                nome=f"AUTO-{numero_cenario:03d}",
                geracao_fv_kw=geracao_fv_kw,
                irradiancia_w_m2=irradiancia_w_m2,
                carga_kw=carga_kw,
                no_rede=resultado["no_rede"],
                fator_potencia=resultado["fator_potencia"],
                tensao_inicial_pu=resultado["tensao_inicial_pu"],
                tensao_resultado_pu=resultado["tensao_resultado_pu"],
                tensao_resultado_v=resultado["tensao_resultado_v"],
                tensao_prevista_ml_pu=resultado["tensao_prevista_ml_pu"],
                erro_absoluto_ml_pu=resultado["erro_absoluto_ml_pu"],
                erro_percentual_ml=resultado["erro_percentual_ml"],
                origem_resultado=resultado["origem_resultado"],
                classificacao_risco=resultado["classificacao_risco"],
                observacao="Cenário gerado automaticamente pelo DEGIA."
            )

            db.add(cenario)
            db.flush()

            cenarios_gerados.append({
                "id": cenario.id,
                "nome": cenario.nome,
                "geracao_fv_kw": geracao_fv_kw,
                "irradiancia_w_m2": irradiancia_w_m2,
                "carga_kw": carga_kw,
                "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw,
                "tensao_resultado_pu": resultado["tensao_resultado_pu"],
                "classificacao_risco": resultado["classificacao_risco"]
            })

        except Exception as erro:
            erros.append({
                "geracao_fv_kw": geracao_fv_kw,
                "irradiancia_w_m2": irradiancia_w_m2,
                "carga_kw": carga_kw,
                "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw,
                "erro": str(erro)
            })

        numero_cenario += 1

    try:
        db.commit()

    except Exception as erro:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar o lote de cenários: {str(erro)}"
        )

    return {
        "projeto_id": projeto_id,
        "total_combinacoes": total_combinacoes,
        "total_combinacoes_unicas": total_combinacoes_unicas,
        "total_descartadas_redundancia": (
            total_combinacoes - total_combinacoes_unicas
        ),
        "total_gerados": len(cenarios_gerados),
        "total_erros": len(erros),
        "cenarios": cenarios_gerados,
        "erros": erros
    }

@app.get("/api/projetos/{projeto_id}/cenarios", response_model=list[CenarioResponse])
def listar_cenarios(projeto_id: int, db: Session = Depends(get_db)):
    obter_projeto_ou_404(projeto_id, db)
    return (
        db.query(Cenario)
        .filter(Cenario.projeto_id == projeto_id)
        .order_by(Cenario.id.desc())
        .all()
    )


@app.get("/api/projetos/{projeto_id}/dataset.csv")
def exportar_dataset_csv(
    projeto_id: int,
    db: Session = Depends(get_db)
):
    projeto = obter_projeto_ou_404(projeto_id, db)

    cenarios = (
        db.query(Cenario)
        .filter(
            Cenario.projeto_id == projeto_id,
            Cenario.tensao_resultado_pu.isnot(None)
        )
        .order_by(Cenario.id)
        .all()
    )

    if not cenarios:
        raise HTTPException(
            status_code=404,
            detail="Nenhum cenário com resultado encontrado para gerar o dataset."
        )

    arquivo = io.StringIO()
    writer = csv.writer(arquivo)

    writer.writerow([
        "cenario_id",
        "geracao_fv_kw",
        "irradiancia_w_m2",
        "carga_kw",
        "no_rede",
        "fator_potencia",
        "tensao_inicial_pu",
        "tensao_resultado_pu",
        "classificacao_risco",
        "origem_resultado"
    ])

    for cenario in cenarios:
        writer.writerow([
            cenario.id,
            cenario.geracao_fv_kw,
            cenario.irradiancia_w_m2,
            cenario.carga_kw,
            cenario.no_rede,
            cenario.fator_potencia,
            cenario.tensao_inicial_pu,
            cenario.tensao_resultado_pu,
            cenario.classificacao_risco,
            cenario.origem_resultado
        ])

    arquivo.seek(0)

    nome_arquivo = f"degia_dataset_projeto_{projeto.id}.csv"

    return StreamingResponse(
        iter([arquivo.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"'
        }
    )


@app.get("/api/projetos/{projeto_id}/dashboard", response_model=DashboardResumo)
def dashboard_projeto(projeto_id: int, db: Session = Depends(get_db)):
    projeto = obter_projeto_ou_404(projeto_id, db)
    cenarios = (
        db.query(Cenario)
        .filter(Cenario.projeto_id == projeto_id)
        .order_by(Cenario.id.asc())
        .all()
    )

    resultados_pu = [c.tensao_resultado_pu for c in cenarios if c.tensao_resultado_pu is not None]
    resultados_v = [c.tensao_resultado_v for c in cenarios if c.tensao_resultado_v is not None]

    def media(valores):
        return sum(valores) / len(valores) if valores else None

    contagem_risco = {"BAIXO": 0, "ATENCAO": 0, "ALTO": 0, "NAO_CLASSIFICADO": 0}
    for cenario in cenarios:
        risco = (cenario.classificacao_risco or "").strip().upper()
        if risco == "BAIXO":
            contagem_risco["BAIXO"] += 1
        elif risco in {"ATENCAO", "ATENÇÃO"}:
            contagem_risco["ATENCAO"] += 1
        elif risco == "ALTO":
            contagem_risco["ALTO"] += 1
        else:
            contagem_risco["NAO_CLASSIFICADO"] += 1

    cenarios_com_pu = [c for c in cenarios if c.tensao_resultado_pu is not None]
    cenario_maior_tensao = max(cenarios_com_pu, key=lambda c: c.tensao_resultado_pu) if cenarios_com_pu else None

    return {
        "projeto": projeto,
        "total_cenarios": len(cenarios),
        "cenarios_com_resultado": len(resultados_pu),
        "tensao_media_pu": media(resultados_pu),
        "tensao_min_pu": min(resultados_pu) if resultados_pu else None,
        "tensao_max_pu": max(resultados_pu) if resultados_pu else None,
        "tensao_media_v": media(resultados_v),
        "tensao_min_v": min(resultados_v) if resultados_v else None,
        "tensao_max_v": max(resultados_v) if resultados_v else None,
        "risco_baixo": contagem_risco["BAIXO"],
        "risco_atencao": contagem_risco["ATENCAO"],
        "risco_alto": contagem_risco["ALTO"],
        "risco_nao_classificado": contagem_risco["NAO_CLASSIFICADO"],
        "cenario_maior_tensao": cenario_maior_tensao,
        "cenarios": cenarios,
    }

@app.post("/api/simular")
async def simular(dados: SimulacaoRequest):
    try:
        resultado = simular_cenario(
            no_rede=dados.no_rede,
            potencia_fv_kw=dados.potencia_fv_kw,
            irradiancia_w_m2=dados.irradiancia_w_m2,
            fator_potencia=dados.fator_potencia
        )

        return {
            "sucesso": True,
            "resultado": resultado
        }

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": str(erro)
        }

@app.post("/api/prever-tensao")
def prever_tensao(dados: PrevisaoMLRequest):
    return prever_tensao_ml(
        potencia_fv_kw=dados.potencia_fv_kw,
        irradiancia_w_m2=dados.irradiancia_w_m2,
        carga_kw=dados.carga_kw
    )


@app.post("/api/comparar-opendss-ml")
async def comparar_opendss_ml(dados: ComparacaoRequest):
    resultado_opendss = simular_cenario(
        no_rede=dados.no_rede,
        potencia_fv_kw=dados.potencia_fv_kw,
        irradiancia_w_m2=dados.irradiancia_w_m2,
        carga_kw=dados.carga_kw,
        fator_potencia=dados.fator_potencia
    )

    resultado_ml = prever_tensao_ml(
        potencia_fv_kw=dados.potencia_fv_kw,
        irradiancia_w_m2=dados.irradiancia_w_m2,
        carga_kw=dados.carga_kw
    )

    tensao_opendss_pu = resultado_opendss["tensao_fv_max_pu"]
    tensao_ml_pu = resultado_ml["tensao_prevista_pu"]

    erro_absoluto_pu = abs(
        tensao_opendss_pu - tensao_ml_pu
    )

    erro_percentual = (
        erro_absoluto_pu / tensao_opendss_pu
    ) * 100

    return {
        "entrada": {
            "potencia_fv_kw": dados.potencia_fv_kw,
            "irradiancia_w_m2": dados.irradiancia_w_m2,
            "carga_kw": dados.carga_kw,
            "no_rede": dados.no_rede,
            "fator_potencia": dados.fator_potencia
        },
        "opendss": {
            "tensao_pu": tensao_opendss_pu,
            "origem": "OPENDSS"
        },
        "machine_learning": {
            "tensao_pu": tensao_ml_pu,
            "classificacao_risco": resultado_ml["classificacao_risco"],
            "origem": "ML_RANDOM_FOREST"
        },
        "comparacao": {
            "erro_absoluto_pu": erro_absoluto_pu,
            "erro_percentual": erro_percentual
        }
    }
