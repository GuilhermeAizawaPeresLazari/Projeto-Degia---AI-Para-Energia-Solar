from simulador import simular_cenario


resultado = simular_cenario(
    no_rede="675",
    potencia_fv_kw=500,
    irradiancia_w_m2=1000,
    fator_potencia=1.0
)

print()
print("=== RESULTADO DEGIA ===")

print(
    f"Nó: {resultado['no_rede']}"
)

print(
    f"Potência FV: "
    f"{resultado['potencia_fv_kw']} kW"
)

print(
    f"Irradiância: "
    f"{resultado['irradiancia_w_m2']} W/m²"
)

print(
    f"FP: "
    f"{resultado['fator_potencia']}"
)

print()

print(
    f"Tensão base: "
    f"{resultado['tensao_base_min_pu']:.4f} "
    f"a "
    f"{resultado['tensao_base_max_pu']:.4f} pu"
)

print(
    f"Tensão com FV: "
    f"{resultado['tensao_fv_min_pu']:.4f} "
    f"a "
    f"{resultado['tensao_fv_max_pu']:.4f} pu"
)

print()

print(
    f"Variação máxima: "
    f"{resultado['variacao_max_pu']:+.4f} pu"
)
