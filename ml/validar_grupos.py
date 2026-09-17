import pandas as pd

from sklearn.model_selection import GroupKFold, cross_validate
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor


# ============================================================
# 1. CARREGAR DATASET V2
# ============================================================

df = pd.read_csv("dataset/degia_dataset_v2.csv")


# ============================================================
# 2. POTÊNCIA FV EFETIVA
# ============================================================

df["potencia_fv_efetiva_kw"] = (
    df["geracao_fv_kw"]
    * df["irradiancia_w_m2"]
    / 1000.0
)


X = df[
    [
        "potencia_fv_efetiva_kw",
        "carga_kw"
    ]
]

y = df["tensao_resultado_pu"]


# Cada nível de potência efetiva será considerado um grupo.
#
# Dessa forma, quando um grupo estiver no teste,
# aquele nível inteiro de potência não estará no treino.
grupos = df["potencia_fv_efetiva_kw"]


print("==============================================")
print("DEGIA - VALIDAÇÃO POR GRUPOS")
print("==============================================")
print(f"Total de registros: {len(df)}")
print(f"Níveis de potência efetiva: {grupos.nunique()}")


# ============================================================
# 3. GROUP K-FOLD
# ============================================================

group_kfold = GroupKFold(
    n_splits=5
)

metricas = {
    "mae": "neg_mean_absolute_error",
    "rmse": "neg_root_mean_squared_error",
    "r2": "r2"
}


modelos = {
    "REGRESSÃO LINEAR": LinearRegression(),

    "RANDOM FOREST": RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        n_jobs=-1
    ),

    "XGBOOST": XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )
}


# ============================================================
# 4. AVALIAÇÃO
# ============================================================

for nome, modelo in modelos.items():

    resultado = cross_validate(
        modelo,
        X,
        y,
        groups=grupos,
        cv=group_kfold,
        scoring=metricas
    )

    mae = -resultado["test_mae"]
    rmse = -resultado["test_rmse"]
    r2 = resultado["test_r2"]

    print()
    print("==============================================")
    print(nome)
    print("==============================================")

    for i in range(5):
        print(
            f"Rodada {i + 1}: "
            f"MAE={mae[i]:.8f} | "
            f"RMSE={rmse[i]:.8f} | "
            f"R²={r2[i]:.6f}"
        )

    print()
    print(f"MAE médio:        {mae.mean():.8f}")
    print(f"RMSE médio:       {rmse.mean():.8f}")
    print(f"R² médio:         {r2.mean():.6f}")
    print(f"Desvio padrão R²: {r2.std():.6f}")
