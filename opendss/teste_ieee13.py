import opendssdirect as dss
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_DSS = (
    BASE_DIR
    / "electricdss-tst"
    / "Version8"
    / "Distrib"
    / "IEEETestCases"
    / "13Bus"
    / "IEEE13Nodeckt.dss"
)


def carregar_rede():
    dss.Basic.ClearAll()

    dss.Text.Command(f'Redirect "{ARQUIVO_DSS}"')

    dss.Solution.Solve()

    if not dss.Solution.Converged():
        raise RuntimeError("A simulação não convergiu.")


def obter_tensoes_bus(bus_name):
    dss.Circuit.SetActiveBus(bus_name)

    valores = dss.Bus.puVmagAngle()

    magnitudes = valores[0::2]

    return {
        "min": min(magnitudes),
        "max": max(magnitudes),
        "fases": magnitudes
    }


# ==================================================
# 1. CASO BASE
# ==================================================

carregar_rede()

tensao_base = obter_tensoes_bus("675")

print()
print("=== CASO BASE ===")

print(
    f"Bus 675: "
    f"min={tensao_base['min']:.4f} pu "
    f"max={tensao_base['max']:.4f} pu"
)


# ==================================================
# 2. ADICIONAR SISTEMA FOTOVOLTAICO
# ==================================================

dss.Text.Command(
    "New PVSystem.PV_DEGIA phases=3 bus1=675 kV=4.16 kVA=500 Pmpp=500 irradiance=1 pf=1 conn=wye"
)

# Executa novamente o fluxo de potência
dss.Solution.Solve()

if not dss.Solution.Converged():
    raise RuntimeError(
        "A simulação com sistema FV não convergiu."
    )


# ==================================================
# 3. RESULTADO COM FV
# ==================================================

tensao_fv = obter_tensoes_bus("675")

print()
print("=== CASO COM FV ===")

print(
    f"Bus 675: "
    f"min={tensao_fv['min']:.4f} pu "
    f"max={tensao_fv['max']:.4f} pu"
)


# ==================================================
# 4. COMPARAÇÃO
# ==================================================

print()
print("=== COMPARAÇÃO ===")

variacao_min = tensao_fv["min"] - tensao_base["min"]
variacao_max = tensao_fv["max"] - tensao_base["max"]

print(
    f"Variação mínima: {variacao_min:+.4f} pu"
)

print(
    f"Variação máxima: {variacao_max:+.4f} pu"
)

print()
print("Fases - caso base:")
print(
    [round(v, 4) for v in tensao_base["fases"]]
)

print()

print("Fases - com FV:")
print(
    [round(v, 4) for v in tensao_fv["fases"]]
)
