import opendssdirect as dss
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_DSS = (
    BASE_DIR
    / "opendss"
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
    carga_kw=0,
    fator_potencia=1.0
):
    # ==================================================
    # 1. CARREGAR REDE IEEE 13-BUS
    # ==================================================

    carregar_rede()

    # ==================================================
    # 2. ADICIONAR CARGA DO CENÁRIO
    # ==================================================

    # No MVP, a carga local é modelada como:
    # - trifásica
    # - conectada no mesmo barramento analisado
    # - fator de potência da carga = 1.0
    #
    # Posteriormente podemos separar o FP da carga
    # do FP do inversor fotovoltaico.

    if carga_kw is not None and carga_kw > 0:
        comando_carga = (
            "New Load.CARGA_DEGIA "
            f"phases=3 "
            f"bus1={no_rede} "
            f"kV=4.16 "
            f"kW={carga_kw} "
            "pf=1.0 "
            "conn=wye "
            "model=1"
        )

        dss.Text.Command(comando_carga)

    # ==================================================
    # 3. EXECUTAR CASO SEM FV
    # ==================================================

    dss.Solution.Solve()

    if not dss.Solution.Converged():
        raise RuntimeError(
            "A simulação com a carga do cenário não convergiu."
        )

    # Agora a tensão inicial já considera a carga
    # informada no cenário.
    tensao_base = obter_tensoes_bus(no_rede)

    # ==================================================
    # 4. CONVERTER IRRADIÂNCIA
    # ==================================================

    # OpenDSS utiliza irradiance em pu.
    # 1000 W/m² = 1.0 pu
    irradiancia_pu = irradiancia_w_m2 / 1000.0

    # ==================================================
    # 5. ADICIONAR SISTEMA FOTOVOLTAICO
    # ==================================================

    if potencia_fv_kw is not None and potencia_fv_kw > 0:
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
    # 6. EXECUTAR SIMULAÇÃO COM CARGA + FV
    # ==================================================

    dss.Solution.Solve()

    if not dss.Solution.Converged():
        raise RuntimeError(
            "A simulação com carga e sistema FV não convergiu."
        )

    tensao_fv = obter_tensoes_bus(no_rede)

    # ==================================================
    # 7. RESULTADO
    # ==================================================

    return {
        "no_rede": no_rede,

        "potencia_fv_kw": potencia_fv_kw,

        "irradiancia_w_m2": irradiancia_w_m2,

        "carga_kw": carga_kw,

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