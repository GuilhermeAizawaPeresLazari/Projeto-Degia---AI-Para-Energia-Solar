import joblib
import pandas as pd


# Carregar o modelo salvo
modelo = joblib.load("modelos/modelo_random_forest.joblib")


# Exemplo de entrada
potencia_fv_nominal_kw = 3000
irradiancia_w_m2 = 750
carga_kw = 1000


# Calcular a potência FV efetiva
potencia_fv_efetiva_kw = (
    potencia_fv_nominal_kw * irradiancia_w_m2 / 1000
)


# Montar os dados exatamente com as mesmas features usadas no treinamento
entrada = pd.DataFrame(
    [
        {
            "potencia_fv_efetiva_kw": potencia_fv_efetiva_kw,
            "carga_kw": carga_kw
        }
    ]
)


# Fazer previsão
tensao_prevista_pu = modelo.predict(entrada)[0]


print("=== DEGIA - PREVISÃO COM MODELO SALVO ===")
print(f"Potência FV nominal: {potencia_fv_nominal_kw} kW")
print(f"Irradiância: {irradiancia_w_m2} W/m²")
print(f"Potência FV efetiva: {potencia_fv_efetiva_kw} kW")
print(f"Carga: {carga_kw} kW")
print(f"Tensão prevista: {tensao_prevista_pu:.6f} pu")