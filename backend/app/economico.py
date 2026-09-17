from copy import deepcopy


# ============================================================
# HIPÓTESES ECONÔMICAS DO MVP
#
# Valores acadêmicos/hipotéticos.
# Não representam tarifa oficial ou orçamento de mercado.
# ============================================================

TARIFA_ENERGIA_R_KWH = 0.95
HORIZONTE_ANALISE_H = 1.0

# Custo hipotético de configuração/acionamento do controle
# de fator de potência.
CUSTO_AJUSTE_FP_R = 50.0


def calcular_custo_alternativa(
    alternativa: dict,
    cenario_original: dict
) -> dict:

    tipo = alternativa["tipo"]

    potencia_original = cenario_original["potencia_fv_kw"]
    irradiancia = cenario_original["irradiancia_w_m2"]
    carga_original = cenario_original["carga_kw"]

    custo = 0.0
    descricao_custo = ""

    energia_afetada_kwh = 0.0


    # ========================================================
    # 1. CURTAILMENT
    # ========================================================

    if tipo == "CURTAILMENT":

        potencia_reduzida_nominal = (
            potencia_original
            - alternativa["potencia_fv_kw"]
        )

        potencia_reduzida_efetiva = (
            potencia_reduzida_nominal
            * irradiancia
            / 1000.0
        )

        energia_afetada_kwh = (
            potencia_reduzida_efetiva
            * HORIZONTE_ANALISE_H
        )

        custo = (
            energia_afetada_kwh
            * TARIFA_ENERGIA_R_KWH
        )

        descricao_custo = (
            "Custo estimado pela energia FV "
            "não aproveitada durante o horizonte analisado."
        )


    # ========================================================
    # 2. AUMENTO DA CARGA LOCAL
    # ========================================================

    elif tipo == "CARGA_LOCAL":

        carga_adicional_kw = max(
            alternativa["carga_kw"] - carga_original,
            0
        )

        energia_afetada_kwh = (
            carga_adicional_kw
            * HORIZONTE_ANALISE_H
        )

        custo = (
            energia_afetada_kwh
            * TARIFA_ENERGIA_R_KWH
        )

        descricao_custo = (
            "Custo estimado pelo consumo adicional "
            "de energia no período analisado."
        )


    # ========================================================
    # 3. AJUSTE DO FATOR DE POTÊNCIA
    # ========================================================

    elif tipo == "FATOR_POTENCIA":

        custo = CUSTO_AJUSTE_FP_R

        descricao_custo = (
            "Custo técnico hipotético associado "
            "à configuração/acionamento do controle "
            "de fator de potência."
        )


    return {
        "custo_estimado_r": round(custo, 2),
        "energia_afetada_kwh": round(
            energia_afetada_kwh,
            4
        ),
        "descricao_custo": descricao_custo
    }


def aplicar_analise_economica(
    resultado_tecnico: dict
) -> dict:

    resultado = deepcopy(resultado_tecnico)

    cenario_original = resultado["cenario_original"]

    alternativas = []


    # ========================================================
    # CALCULAR CUSTO DE CADA ALTERNATIVA
    # ========================================================

    for alternativa in resultado["alternativas"]:

        alternativa_completa = deepcopy(
            alternativa
        )

        dados_economicos = calcular_custo_alternativa(
            alternativa=alternativa,
            cenario_original=cenario_original
        )

        alternativa_completa.update(
            dados_economicos
        )

        alternativas.append(
            alternativa_completa
        )


    # ========================================================
    # RANKING TÉCNICO-ECONÔMICO
    #
    # Prioridades:
    #
    # 1. Resolver o risco
    # 2. Menor custo
    # 3. Ficar mais próximo de 1.05 pu
    # ========================================================

    def chave_ranking(item):

        prioridade_resolucao = (
            0 if item["resolve_risco"] else 1
        )

        custo = item["custo_estimado_r"]

        distancia_limite = abs(
            1.05
            - item["tensao_resultado_pu"]
        )

        return (
            prioridade_resolucao,
            custo,
            distancia_limite
        )


    ranking = sorted(
        alternativas,
        key=chave_ranking
    )


    melhor_tecnico_economica = (
        ranking[0]
        if ranking
        else None
    )


    # ========================================================
    # RESPOSTA
    # ========================================================

    resultado["alternativas"] = alternativas

    resultado["analise_economica"] = {
        "tarifa_energia_r_kwh": TARIFA_ENERGIA_R_KWH,
        "horizonte_analise_h": HORIZONTE_ANALISE_H,
        "custo_ajuste_fp_r": CUSTO_AJUSTE_FP_R,
        "natureza_dos_valores": (
            "HIPOTETICOS_PARA_PROTOTIPO_ACADEMICO"
        )
    }

    resultado["ranking_tecnico_economico"] = ranking

    resultado[
        "melhor_alternativa_tecnico_economica"
    ] = melhor_tecnico_economica

    return resultado
