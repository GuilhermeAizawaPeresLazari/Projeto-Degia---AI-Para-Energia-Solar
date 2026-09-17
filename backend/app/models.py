from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Projeto(Base):
    __tablename__ = "projeto"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)

    # Localização / contexto do projeto
    uf = Column(String(2), nullable=True)
    municipio = Column(String(120), nullable=True)
    concessionaria = Column(String(120), nullable=True)

    # Dados elétricos principais
    potencia_fv_kwp = Column(Float, nullable=False)
    carga_local_kw = Column(Float, nullable=False)
    tensao_referencia_v = Column(Float, nullable=False)
    fator_potencia = Column(Float, nullable=False, default=1.0)

    # Referência da rede simulada. O nó pertence ao modelo elétrico,
    # e não é inferido simplesmente pela UF/município.
    rede_simulada = Column(String(50), nullable=False, default="IEEE13")
    no_rede_referencia = Column(String(80), nullable=True, default="675")

    descricao = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    cenarios = relationship(
        "Cenario",
        back_populates="projeto",
        cascade="all, delete-orphan",
    )


class Cenario(Base):
    __tablename__ = "cenario"


    id = Column(Integer, primary_key=True, index=True)
    projeto_id = Column(
        Integer,
        ForeignKey("projeto.id", ondelete="CASCADE"),
        nullable=False,
    )

    nome = Column(String(150), nullable=False)

    # Entradas variáveis do cenário
    geracao_fv_kw = Column(Float, nullable=True)
    irradiancia_w_m2 = Column(Float, nullable=True)
    carga_kw = Column(Float, nullable=True)

    # Estes valores são copiados do contexto do projeto quando o cenário é criado.
    no_rede = Column(String(80), nullable=True)
    fator_potencia = Column(Float, nullable=True)

    # Saídas / resultados. Permanecem opcionais até a integração OpenDSS/ML.
    tensao_inicial_pu = Column(Float, nullable=True)
    tensao_resultado_v = Column(Float, nullable=True)
    tensao_resultado_pu = Column(Float, nullable=True)
    tensao_prevista_ml_pu = Column(Float, nullable=True)
    erro_absoluto_ml_pu = Column(Float, nullable=True)
    erro_percentual_ml = Column(Float, nullable=True)
    origem_resultado = Column(String(30), nullable=False, default="PENDENTE")
    classificacao_risco = Column(String(40), nullable=True)

    observacao = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    projeto = relationship("Projeto", back_populates="cenarios")
