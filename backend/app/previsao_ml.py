from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_MODELO = (
    BASE_DIR
    / "ml"
    / "modelo_random_forest.joblib"
)


modelo_ml = joblib.load(ARQUIVO_MODELO)


def prever_tensao_ml(
    potencia_fv_kw: float,
    irradiancia_w_m2: float,
    carga_kw: float
):
    potencia_fv_efetiva_kw = (
        potencia_fv_kw
        * irradiancia_w_m2
        / 1000.0
    )

    entrada = pd.DataFrame(
        [
            {
                "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw,
                "carga_kw": carga_kw
            }
        ]
    )

    tensao_prevista_pu = float(
        modelo_ml.predict(entrada)[0]
    )

    if tensao_prevista_pu <= 1.05:
        classificacao_risco = "BAIXO"
    elif tensao_prevista_pu <= 1.0591:
        classificacao_risco = "ATENÇÃO"
    else:
        classificacao_risco = "ALTO"

    return {
        "potencia_fv_kw": potencia_fv_kw,
        "irradiancia_w_m2": irradiancia_w_m2,
        "carga_kw": carga_kw,
        "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw,
        "tensao_prevista_pu": tensao_prevista_pu,
        "classificacao_risco": classificacao_risco,
        "origem_resultado": "ML_RANDOM_FOREST"
    }