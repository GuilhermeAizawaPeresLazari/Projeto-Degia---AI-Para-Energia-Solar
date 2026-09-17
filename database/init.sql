CREATE TABLE IF NOT EXISTS projeto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,

    uf VARCHAR(2),
    municipio VARCHAR(120),
    concessionaria VARCHAR(120),

    potencia_fv_kwp DOUBLE PRECISION NOT NULL,
    carga_local_kw DOUBLE PRECISION NOT NULL,
    tensao_referencia_v DOUBLE PRECISION NOT NULL,
    fator_potencia DOUBLE PRECISION NOT NULL DEFAULT 1.0,

    rede_simulada VARCHAR(50) NOT NULL DEFAULT 'IEEE13',
    no_rede_referencia VARCHAR(80) DEFAULT '675',

    descricao TEXT,
    criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cenario (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES projeto(id) ON DELETE CASCADE,

    nome VARCHAR(150) NOT NULL,

    geracao_fv_kw DOUBLE PRECISION,
    irradiancia_w_m2 DOUBLE PRECISION,
    carga_kw DOUBLE PRECISION,
    no_rede VARCHAR(80),
    fator_potencia DOUBLE PRECISION,

    tensao_inicial_pu DOUBLE PRECISION,
    tensao_resultado_v DOUBLE PRECISION,
    tensao_resultado_pu DOUBLE PRECISION,

    origem_resultado VARCHAR(30) NOT NULL DEFAULT 'PENDENTE',
    classificacao_risco VARCHAR(40),
    observacao TEXT,

    criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cenario_projeto
ON cenario(projeto_id);
