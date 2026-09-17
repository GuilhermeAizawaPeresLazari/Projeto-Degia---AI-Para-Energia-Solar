from app.simulador import simular_cenario


LIMITE_BAIXO_PU = 1.05
LIMITE_ATENCAO_PU = 1.0591


def classificar_risco(tensao_pu: float) -> str:
    if tensao_pu <= LIMITE_BAIXO_PU:
        return "BAIXO"
    elif tensao_pu <= LIMITE_ATENCAO_PU:
        return "ATENÇÃO"
    else:
        return "ALTO"


def criar_resultado_alternativa(
    codigo,
    nome,
    tipo,
    tensao_original,
    tensao_resultado,
    potencia_fv_kw,
    carga_kw,
    fator_potencia,
    intensidade=None
):
    reducao = tensao_original - tensao_resultado

    return {
        "codigo": codigo,
        "nome": nome,
        "tipo": tipo,
        "intensidade": intensidade,
        "potencia_fv_kw": potencia_fv_kw,
        "carga_kw": carga_kw,
        "fator_potencia": fator_potencia,
        "tensao_resultado_pu": tensao_resultado,
        "reducao_tensao_pu": reducao,
        "melhora_tensao": reducao > 0,
        "resolve_risco": tensao_resultado <= LIMITE_BAIXO_PU,
        "classificacao_risco": classificar_risco(
            tensao_resultado
        )
    }


def avaliar_alternativas(
    no_rede: str,
    potencia_fv_kw: float,
    irradiancia_w_m2: float,
    carga_kw: float,
    fator_potencia: float = 1.0
):
    alternativas = []

    # ========================================================
    # 1. CENÁRIO ORIGINAL
    # ========================================================

    original = simular_cenario(
        no_rede=no_rede,
        potencia_fv_kw=potencia_fv_kw,
        irradiancia_w_m2=irradiancia_w_m2,
        carga_kw=carga_kw,
        fator_potencia=fator_potencia
    )

    tensao_original = original["tensao_fv_max_pu"]

    # ========================================================
    # 2. CURTAILMENT / REDUÇÃO DA POTÊNCIA FV
    # ========================================================

    for percentual in [10, 20, 30, 40]:

        fator_reducao = 1 - percentual / 100
        nova_potencia = potencia_fv_kw * fator_reducao

        resultado = simular_cenario(
            no_rede=no_rede,
            potencia_fv_kw=nova_potencia,
            irradiancia_w_m2=irradiancia_w_m2,
            carga_kw=carga_kw,
            fator_potencia=fator_potencia
        )

        tensao = resultado["tensao_fv_max_pu"]

        alternativas.append(
            criar_resultado_alternativa(
                codigo=f"REDUCAO_FV_{percentual}",
                nome=(
                    f"Redução de {percentual}% "
                    "da potência FV"
                ),
                tipo="CURTAILMENT",
                intensidade=percentual,
                tensao_original=tensao_original,
                tensao_resultado=tensao,
                potencia_fv_kw=nova_potencia,
                carga_kw=carga_kw,
                fator_potencia=fator_potencia
            )
        )

    # ========================================================
    # 3. AUMENTO DA CARGA LOCAL
    # ========================================================

    for percentual in [10, 20]:

        fator_aumento = 1 + percentual / 100
        nova_carga = carga_kw * fator_aumento

        resultado = simular_cenario(
            no_rede=no_rede,
            potencia_fv_kw=potencia_fv_kw,
            irradiancia_w_m2=irradiancia_w_m2,
            carga_kw=nova_carga,
            fator_potencia=fator_potencia
        )

        tensao = resultado["tensao_fv_max_pu"]

        alternativas.append(
            criar_resultado_alternativa(
                codigo=f"AUMENTO_CARGA_{percentual}",
                nome=(
                    f"Aumento de {percentual}% "
                    "da carga local"
                ),
                tipo="CARGA_LOCAL",
                intensidade=percentual,
                tensao_original=tensao_original,
                tensao_resultado=tensao,
                potencia_fv_kw=potencia_fv_kw,
                carga_kw=nova_carga,
                fator_potencia=fator_potencia
            )
        )

    # ========================================================
    # 4. AJUSTE DE FATOR DE POTÊNCIA
    #
    # No modelo atual do OpenDSS, valores negativos testados
    # produziram redução da tensão no barramento 675.
    # ========================================================

    for novo_fp in [-0.98, -0.95]:

        resultado = simular_cenario(
            no_rede=no_rede,
            potencia_fv_kw=potencia_fv_kw,
            irradiancia_w_m2=irradiancia_w_m2,
            carga_kw=carga_kw,
            fator_potencia=novo_fp
        )

        tensao = resultado["tensao_fv_max_pu"]

        alternativas.append(
            criar_resultado_alternativa(
                codigo=(
                    "AJUSTE_FP_"
                    + str(abs(novo_fp)).replace(".", "")
                    + "_NEG"
                ),
                nome=(
                    "Ajuste do fator de potência "
                    f"para {novo_fp}"
                ),
                tipo="FATOR_POTENCIA",
                intensidade=novo_fp,
                tensao_original=tensao_original,
                tensao_resultado=tensao,
                potencia_fv_kw=potencia_fv_kw,
                carga_kw=carga_kw,
                fator_potencia=novo_fp
            )
        )

    # ========================================================
    # 5. FILTRAR ALTERNATIVAS QUE REALMENTE MELHORAM
    # ========================================================

    alternativas_que_melhoram = [
        alternativa
        for alternativa in alternativas
        if alternativa["melhora_tensao"]
    ]

    alternativas_que_resolvem = [
        alternativa
        for alternativa in alternativas_que_melhoram
        if alternativa["resolve_risco"]
    ]

    # ========================================================
    # 6. RECOMENDAÇÃO TÉCNICA
    #
    # Se alguma alternativa resolve:
    # escolhemos a que fica mais próxima de 1.05 pu por baixo,
    # evitando uma correção excessiva.
    #
    # Se nenhuma resolve:
    # escolhemos a que apresenta a menor tensão.
    # ========================================================

    melhor_alternativa = None

    if alternativas_que_resolvem:

        melhor_alternativa = min(
            alternativas_que_resolvem,
            key=lambda item: (
                LIMITE_BAIXO_PU
                - item["tensao_resultado_pu"]
            )
        )

    elif alternativas_que_melhoram:

        melhor_alternativa = min(
            alternativas_que_melhoram,
            key=lambda item: item["tensao_resultado_pu"]
        )

    # ========================================================
    # 7. RESPOSTA
    # ========================================================

    return {
        "cenario_original": {
            "potencia_fv_kw": potencia_fv_kw,
            "irradiancia_w_m2": irradiancia_w_m2,
            "carga_kw": carga_kw,
            "fator_potencia": fator_potencia,
            "tensao_resultado_pu": tensao_original,
            "classificacao_risco": classificar_risco(
                tensao_original
            )
        },

        "resumo": {
            "total_alternativas": len(alternativas),
            "total_que_melhoram": len(
                alternativas_que_melhoram
            ),
            "total_que_resolvem": len(
                alternativas_que_resolvem
            )
        },

        "alternativas": alternativas,

        "melhor_alternativa_tecnica": melhor_alternativa
    }
