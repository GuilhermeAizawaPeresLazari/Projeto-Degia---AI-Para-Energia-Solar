-- Migração opcional para quem já utilizava o MVP 0.2.
-- O back-end também executa estes ADD COLUMN IF NOT EXISTS automaticamente ao iniciar.

ALTER TABLE projeto ADD COLUMN IF NOT EXISTS uf VARCHAR(2);
ALTER TABLE projeto ADD COLUMN IF NOT EXISTS municipio VARCHAR(120);
ALTER TABLE projeto ADD COLUMN IF NOT EXISTS fator_potencia DOUBLE PRECISION DEFAULT 1.0;
ALTER TABLE projeto ADD COLUMN IF NOT EXISTS rede_simulada VARCHAR(50) DEFAULT 'IEEE13';
ALTER TABLE projeto ADD COLUMN IF NOT EXISTS no_rede_referencia VARCHAR(80) DEFAULT '675';

ALTER TABLE cenario ADD COLUMN IF NOT EXISTS no_rede VARCHAR(80);
ALTER TABLE cenario ADD COLUMN IF NOT EXISTS fator_potencia DOUBLE PRECISION;

-- O campo hora de versões antigas pode permanecer fisicamente no banco sem ser utilizado.
-- Ele foi removido do model, da API e da interface do MVP 0.3.
