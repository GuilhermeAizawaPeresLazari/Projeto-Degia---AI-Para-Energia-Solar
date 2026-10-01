from copy import deepcopy
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ============================================================
# HIPÓTESES ECONÔMICAS DO MVP
#
# Valores acadêmicos/hipotéticos.
# Não representam tarifa oficial ou orçamento de mercado.
# ============================================================

TARIFA_ENERGIA_R_KWH = 0.75

# Performance Ratio (PR) hipotético do protótipo.
# Representa perdas globais do sistema fotovoltaico
# (temperatura, inversor, cabos, mismatch etc.).

# Custo hipotético de configuração/acionamento do controle
# de fator de potência.
CUSTO_AJUSTE_FP_R = 50.0

# ============================================================
# REFERÊNCIA SOLAR PARA ANÁLISE ECONÔMICA
# ============================================================

# Coordenadas representativas das capitais.
# Como o MVP trabalha com UF, a capital é utilizada como
# referência geográfica e não como localização exata do projeto.
COORDENADAS_UF = {
    "AC": (-9.9754, -67.8249),
    "AL": (-9.6658, -35.7353),
    "AP": (0.0349, -51.0694),
    "AM": (-3.1190, -60.0217),
    "BA": (-12.9777, -38.5016),
    "CE": (-3.7319, -38.5267),
    "DF": (-15.7939, -47.8828),
    "ES": (-20.3155, -40.3128),
    "GO": (-16.6869, -49.2648),
    "MA": (-2.5307, -44.3068),
    "MT": (-15.6014, -56.0979),
    "MS": (-20.4697, -54.6201),
    "MG": (-19.9167, -43.9345),
    "PA": (-1.4558, -48.4902),
    "PB": (-7.1195, -34.8450),
    "PR": (-25.4284, -49.2733),
    "PE": (-8.0476, -34.8770),
    "PI": (-5.0892, -42.8019),
    "RJ": (-22.9068, -43.1729),
    "RN": (-5.7945, -35.2110),
    "RS": (-30.0346, -51.2177),
    "RO": (-8.7608, -63.8999),
    "RR": (2.8235, -60.6758),
    "SC": (-27.5954, -48.5480),
    "SP": (-23.5505, -46.6333),
    "SE": (-10.9472, -37.0731),
    "TO": (-10.1840, -48.3336),
}

PERDAS_SISTEMA_PVGIS_PERCENTUAL = 14.0


def obter_producao_solar_mensal_pvgis(uf: str) -> dict:

    sigla = uf.strip().upper()

    coordenadas = COORDENADAS_UF.get(sigla)

    if coordenadas is None:
        raise ValueError(
            f"UF inválida para análise econômica: {uf}"
        )

    latitude, longitude = coordenadas

    parametros = urlencode({
        "lat": latitude,
        "lon": longitude,
        "peakpower": 1,
        "loss": PERDAS_SISTEMA_PVGIS_PERCENTUAL,
        "outputformat": "json"
    })

    url = (
        "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?"
        + parametros
    )

    requisicao = Request(
        url,
        headers={
            "User-Agent": "DEGIA-MVP/0.7"
        }
    )

    with urlopen(
        requisicao,
        timeout=20
    ) as resposta:

        dados = json.loads(
            resposta.read().decode("utf-8")
        )

    mensal = (
        dados
        .get("outputs", {})
        .get("monthly", {})
        .get("fixed", [])
    )

    if not mensal:
        raise RuntimeError(
            "PVGIS não retornou dados mensais de produção."
        )

    producao_anual_kwh_kwp = sum(
        float(mes["E_m"])
        for mes in mensal
    )

    producao_media_mensal_kwh_kwp = (
        producao_anual_kwh_kwp / 12
    )

    return {
        "uf": sigla,
        "latitude": latitude,
        "longitude": longitude,
        "producao_anual_kwh_kwp": round(
            producao_anual_kwh_kwp,
            2
        ),
        "producao_media_mensal_kwh_kwp": round(
            producao_media_mensal_kwh_kwp,
            2
        ),
        "perdas_percentual": (
            PERDAS_SISTEMA_PVGIS_PERCENTUAL
        ),
        "fonte": "PVGIS - European Commission JRC"
    }


def calcular_custo_alternativa(
    alternativa: dict,
    cenario_original: dict,
    producao_media_mensal_kwh_kwp: float
) -> dict:

    tipo = alternativa["tipo"]

    potencia_original = cenario_original["potencia_fv_kw"]

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

        energia_afetada_kwh = (
            potencia_reduzida_nominal
            * producao_media_mensal_kwh_kwp
        )

        custo = (
            energia_afetada_kwh
            * TARIFA_ENERGIA_R_KWH
        )

        descricao_custo = (
            "Impacto financeiro mensal médio estimado "
            "pela redução da potência fotovoltaica."
        )



    # ========================================================
    # 2. AJUSTE DO FATOR DE POTÊNCIA
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
    resultado_tecnico: dict,
    uf: str
) -> dict:

    resultado = deepcopy(resultado_tecnico)

    cenario_original = resultado["cenario_original"]

    referencia_solar = obter_producao_solar_mensal_pvgis(
        uf
    )

    producao_media_mensal_kwh_kwp = (
        referencia_solar[
            "producao_media_mensal_kwh_kwp"
        ]
    )

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
            cenario_original=cenario_original,
            producao_media_mensal_kwh_kwp=(
                producao_media_mensal_kwh_kwp
            )
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
        "producao_media_mensal_kwh_kwp": (
            producao_media_mensal_kwh_kwp
        ),
        "perdas_pvgis_percentual": referencia_solar[
            "perdas_percentual"
        ],
        "fonte_solar": referencia_solar["fonte"],
        "uf_referencia": referencia_solar["uf"],
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
