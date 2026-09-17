import pandas as pd

from sklearn.model_selection import KFold, cross_validate
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor


# ============================================================
# 1. CARREGAR DATASET V2
# ============================================================

CAMINHO_DATASET = "dataset/degia_dataset_v2.csv"

df = pd.read_csv(CAMINHO_DATASET)


# ============================================================
# 2. ENGENHARIA DE ATRIBUTOS
# ============================================================

df["potencia_fv_efetiva_kw"] = (
    df["geracao_fv_kw"]
    * df["irradiancia_w_m2"]
    / 1000.0
)


# ============================================================
# 3. VALIDAR DATASET
# ============================================================

colunas_entrada = [
    "potencia_fv_efetiva_kw",
    "carga_kw"
]

duplicados = df.duplicated(
    subset=colunas_entrada
).sum()

entradas_unicas = df[
    colunas_entrada
].drop_duplicates().shape[0]


print("==============================================")
print("DEGIA - VALIDAÇÃO DO DATASET V2")
print("==============================================")
print(f"Total de registros:        {len(df)}")
print(f"Entradas elétricas únicas: {entradas_unicas}")
print(f"Entradas duplicadas:       {duplicados}")


if duplicados > 0:
    raise ValueError(
        "O Dataset V2 possui entradas elétricas duplicadas."
    )


# ============================================================
# 4. ENTRADAS E ALVO
# ============================================================

X = df[
    [
        "potencia_fv_efetiva_kw",
        "carga_kw"
    ]
]

y = df["tensao_resultado_pu"]


print()
print("Faixa das variáveis:")
print(
    f"Potência FV efetiva: "
    f"{X['potencia_fv_efetiva_kw'].min():.2f} "
    f"a {X['potencia_fv_efetiva_kw'].max():.2f} kW"
)
print(
    f"Carga: "
    f"{X['carga_kw'].min():.2f} "
    f"a {X['carga_kw'].max():.2f} kW"
)
print(
    f"Tensão: "
    f"{y.min():.6f} "
    f"a {y.max():.6f} pu"
)


# ============================================================
# 5. VALIDAÇÃO CRUZADA
# ============================================================

kfold = KFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

metricas = {
    "mae": "neg_mean_absolute_error",
    "rmse": "neg_root_mean_squared_error",
    "r2": "r2"
}


# ============================================================
# 6. MODELOS
# ============================================================

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
# 7. AVALIAR MODELOS
# ============================================================

resultados_finais = []


for nome, modelo in modelos.items():

    print()
    print("==============================================")
    print(f"DEGIA - {nome}")
    print("==============================================")

    resultado = cross_validate(
        modelo,
        X,
        y,
        cv=kfold,
        scoring=metricas
    )

    mae = -resultado["test_mae"]
    rmse = -resultado["test_rmse"]
    r2 = resultado["test_r2"]

    print()
    print("Resultados por rodada:")

    for i in range(5):
        print(
            f"Rodada {i + 1}: "
            f"MAE={mae[i]:.8f} | "
            f"RMSE={rmse[i]:.8f} | "
            f"R²={r2[i]:.6f}"
        )

    print()
    print("Médias:")
    print(f"MAE médio:        {mae.mean():.8f}")
    print(f"RMSE médio:       {rmse.mean():.8f}")
    print(f"R² médio:         {r2.mean():.6f}")
    print(f"Desvio padrão R²: {r2.std():.6f}")

    resultados_finais.append(
        {
            "modelo": nome,
            "mae": mae.mean(),
            "rmse": rmse.mean(),
            "r2": r2.mean(),
            "r2_std": r2.std()
        }
    )


# ============================================================
# 8. RANKING FINAL
# ============================================================

ranking = pd.DataFrame(resultados_finais)

ranking = ranking.sort_values(
    by="rmse",
    ascending=True
)


print()
print("==============================================")
print("RANKING FINAL - DATASET V2")
print("==============================================")

print(
    ranking.to_string(
        index=False,
        formatters={
            "mae": "{:.8f}".format,
            "rmse": "{:.8f}".format,
            "r2": "{:.6f}".format,
            "r2_std": "{:.6f}".format
        }
    )
)

print()
print(
    "Nenhum modelo foi salvo nesta execução."
)
