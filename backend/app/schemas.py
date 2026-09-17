from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjetoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    uf: str = Field(min_length=2, max_length=2)
    municipio: Optional[str] = Field(default=None, max_length=120)
    concessionaria: Optional[str] = Field(default=None, max_length=120)

    potencia_fv_kwp: float = Field(gt=0)
    carga_local_kw: float = Field(gt=0)
    tensao_referencia_v: float = Field(gt=0)
    fator_potencia: float = Field(default=1.0, gt=0, le=1)

    rede_simulada: str = Field(default="IEEE13", max_length=50)
    no_rede_referencia: Optional[str] = Field(default="675", max_length=80)

    descricao: Optional[str] = None

    @field_validator("uf")
    @classmethod
    def normalizar_uf(cls, valor: str) -> str:
        return valor.strip().upper()


class ProjetoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    uf: Optional[str] = None
    municipio: Optional[str] = None
    concessionaria: Optional[str] = None
    potencia_fv_kwp: float
    carga_local_kw: float
    tensao_referencia_v: float
    fator_potencia: float = 1.0
    rede_simulada: str = "IEEE13"
    no_rede_referencia: Optional[str] = "675"
    descricao: Optional[str] = None
    criado_em: datetime


class CenarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)

    geracao_fv_kw: Optional[float] = Field(default=None, ge=0)
    irradiancia_w_m2: Optional[float] = Field(default=None, ge=0)
    carga_kw: Optional[float] = Field(default=None, ge=0)

    # Contexto herdado do projeto; o front não precisa enviar.
    no_rede: Optional[str] = None
    fator_potencia: Optional[float] = Field(default=None, gt=0, le=1)

    tensao_inicial_pu: Optional[float] = Field(default=None, gt=0)
    tensao_resultado_v: Optional[float] = Field(default=None, gt=0)
    tensao_resultado_pu: Optional[float] = Field(default=None, gt=0)

    origem_resultado: str = Field(default="PENDENTE")
    classificacao_risco: Optional[str] = None
    observacao: Optional[str] = None


class CenarioResponse(CenarioCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    projeto_id: int

    tensao_prevista_ml_pu: Optional[float] = None
    erro_absoluto_ml_pu: Optional[float] = None
    erro_percentual_ml: Optional[float] = None

    criado_em: datetime


class LocalidadeReferencia(BaseModel):
    uf: str
    municipio: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    irradiancia_w_m2: Optional[float] = None
    fonte_irradiancia: str
    observacao: Optional[str] = None


class DashboardResumo(BaseModel):
    projeto: ProjetoResponse
    total_cenarios: int
    cenarios_com_resultado: int
    tensao_media_pu: Optional[float] = None
    tensao_min_pu: Optional[float] = None
    tensao_max_pu: Optional[float] = None
    tensao_media_v: Optional[float] = None
    tensao_min_v: Optional[float] = None
    tensao_max_v: Optional[float] = None
    risco_baixo: int = 0
    risco_atencao: int = 0
    risco_alto: int = 0
    risco_nao_classificado: int = 0
    cenario_maior_tensao: Optional[CenarioResponse] = None
    cenarios: list[CenarioResponse]

class GeracaoCenariosRequest(BaseModel):
    geracoes_fv_kw: list[float]
    irradiancias_w_m2: list[float]
    cargas_kw: list[float]