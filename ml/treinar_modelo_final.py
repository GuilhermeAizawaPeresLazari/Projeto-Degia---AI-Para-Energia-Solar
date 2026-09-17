import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


# ============================================================
# 1. CAMINHOS
# ============================================================

DATASET = Path("dataset/degia_dataset_v2.csv")
MODELO = Path("modelos/modelo_random_forest.joblib")
METADADOS = Path("modelos/modelo_random_forest_metadata.json")

MODELO.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CARREGAR DATASET V2
# ============================================================

df = pd.read_csv(DATASET)


# ============================================================
# 3. ENGENHARIA DE ATRIBUTOS
# ============================================================

df["potencia_fv_efetiva_kw"] = (
    df["geracao_fv_kw"]
    * df["irradiancia_w_m2"]
    / 1000.0
)


# ============================================================
# 4. ENTRADAS E ALVO
# ============================================================

features = [
    "potencia_fv_efetiva_kw",
    "carga_kw"
]

target = "tensao_resultado_pu"

X = df[features]
y = df[target]


# ============================================================
# 5. MODELO FINAL
# ============================================================

modelo = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)


# Treinamento final com TODOS os registros da V2.
modelo.fit(X, y)


# ============================================================
# 6. SALVAR MODELO
# ============================================================

joblib.dump(
    modelo,
    MODELO
)


# ============================================================
# 7. METADADOS DO MODELO
# ============================================================

metadata = {
    "projeto": "DEGIA",
    "versao_modelo": "2.0",
    "algoritmo": "RandomForestRegressor",
    "dataset": "degia_dataset_v2.csv",
    "total_registros_treinamento": int(len(df)),
    "features": features,
    "target": target,

    "dominio_treinamento": {
        "potencia_fv_efetiva_kw_min": float(
            X["potencia_fv_efetiva_kw"].min()
        ),
        "potencia_fv_efetiva_kw_max": float(
            X["potencia_fv_efetiva_kw"].max()
        ),
        "carga_kw_min": float(
            X["carga_kw"].min()
        ),
        "carga_kw_max": float(
            X["carga_kw"].max()
        )
    },

    "simulacao": {
        "rede": "IEEE13",
        "no_rede": "675",
        "fator_potencia": 1.0,
        "origem_target": "OpenDSS"
    },

    "validacao_kfold": {
        "folds": 5,
        "mae_medio": 0.00066615,
        "rmse_medio": 0.00111018,
        "r2_medio": 0.901974,
        "r2_desvio_padrao": 0.040484
    },

    "validacao_group_kfold": {
        "folds": 5,
        "grupo": "potencia_fv_efetiva_kw",
        "mae_medio": 0.00048070,
        "rmse_medio": 0.00082210,
        "r2_medio": 0.944300,
        "r2_desvio_padrao": 0.035383
    },

    "observacao": (
        "Modelo final treinado com todos os 360 estados "
        "eletricos unicos do Dataset V2. As metricas registradas "
        "foram obtidas anteriormente por validacao cruzada e nao "
        "sobre os dados utilizados no treinamento final."
    ),

    "gerado_em": datetime.now().isoformat()
}


with open(
    METADADOS,
    "w",
    encoding="utf-8"
) as arquivo:
    json.dump(
        metadata,
        arquivo,
        ensure_ascii=False,
        indent=4
    )


# ============================================================
# 8. RESULTADO
# ============================================================

print("==============================================")
print("DEGIA - MODELO FINAL V2")
print("==============================================")
print(f"Algoritmo: Random Forest")
print(f"Registros utilizados: {len(df)}")
print(f"Features: {features}")
print(f"Target: {target}")
print()
print(f"Modelo salvo em: {MODELO}")
print(f"Metadados salvos em: {METADADOS}")
print()
print("Modelo final treinado com sucesso.")
