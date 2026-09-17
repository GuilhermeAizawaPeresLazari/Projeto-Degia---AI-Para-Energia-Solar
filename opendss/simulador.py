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

    dss.Text.Command(
        f'Redirect "{ARQUIVO_DSS}"'
    )

    dss.Solution.Solve()

    if not dss.Solution.Converged():
        raise RuntimeError(
            "A simulação base não convergiu."
        )


def obter_tensoes_bus(bus_name):
    dss.Circuit.SetActiveBus(bus_name)

    valores = dss.Bus.puVmagAngle()

    magnitudes = valores[0::2]

    if not magnitudes:
        raise ValueError(
            f"Nenhuma tensão encontrada para o barramento {bus_name}"
        )

    return {
        "min_pu": min(magnitudes),
        "max_pu": max(magnitudes),
        "fases_pu": magnitudes
    }


def simular_cenario(
    no_rede,
    potencia_fv_kw,
    irradiancia_w_m2,
    fator_potencia=1.0
):
    # ==================================================
    # 1. CASO BASE
    # ==================================================

    carregar_rede()

    tensao_base = obter_tensoes_bus(no_rede)

    # ==================================================
    # 2. CONVERTER IRRADIÂNCIA
    # ==================================================

    # OpenDSS usa irradiance em pu.
    # 1000 W/m² = 1.0
    irradiancia_pu = irradiancia_w_m2 / 1000.0

    # ==================================================
    # 3. ADICIONAR PV
    # ==================================================

    comando_pv = (
        "New PVSystem.PV_DEGIA "
        f"phases=3 "
        f"bus1={no_rede} "
        f"kV=4.16 "
        f"kVA={potencia_fv_kw} "
        f"Pmpp={potencia_fv_kw} "
        f"irradiance={irradiancia_pu} "
        f"pf={fator_potencia} "
        "conn=wye"
    )

    dss.Text.Command(comando_pv)

    # ==================================================
    # 4. EXECUTAR SIMULAÇÃO COM FV
    # ==================================================

    dss.Solution.Solve()

    if not dss.Solution.Converged():
        raise RuntimeError(
            "A simulação com sistema FV não convergiu."
        )

    tensao_fv = obter_tensoes_bus(no_rede)

    # ==================================================
    # 5. RESULTADO
    # ==================================================

    return {
        "no_rede": no_rede,

        "potencia_fv_kw": potencia_fv_kw,

        "irradiancia_w_m2": irradiancia_w_m2,

        "fator_potencia": fator_potencia,

        "tensao_base_min_pu": tensao_base["min_pu"],

        "tensao_base_max_pu": tensao_base["max_pu"],

        "tensao_fv_min_pu": tensao_fv["min_pu"],

        "tensao_fv_max_pu": tensao_fv["max_pu"],

        "variacao_min_pu": (
            tensao_fv["min_pu"]
            - tensao_base["min_pu"]
        ),

        "variacao_max_pu": (
            tensao_fv["max_pu"]
            - tensao_base["max_pu"]
        ),

        "fases_base_pu": tensao_base["fases_pu"],

        "fases_fv_pu": tensao_fv["fases_pu"]
    }
