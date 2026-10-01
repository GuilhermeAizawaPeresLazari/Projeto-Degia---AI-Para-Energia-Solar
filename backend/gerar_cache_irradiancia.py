import json
import math
import time
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CAPITAIS_UF = {
    "AC": "Rio Branco",
    "AL": "Maceió",
    "AP": "Macapá",
    "AM": "Manaus",
    "BA": "Salvador",
    "CE": "Fortaleza",
    "DF": "Brasília",
    "ES": "Vitória",
    "GO": "Goiânia",
    "MA": "São Luís",
    "MT": "Cuiabá",
    "MS": "Campo Grande",
    "MG": "Belo Horizonte",
    "PA": "Belém",
    "PB": "João Pessoa",
    "PR": "Curitiba",
    "PE": "Recife",
    "PI": "Teresina",
    "RJ": "Rio de Janeiro",
    "RN": "Natal",
    "RS": "Porto Alegre",
    "RO": "Porto Velho",
    "RR": "Boa Vista",
    "SC": "Florianópolis",
    "SP": "São Paulo",
    "SE": "Aracaju",
    "TO": "Palmas",
}


NOME_UF = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}


def requisitar_json(url, timeout=30):
    req = Request(
        url,
        headers={
            "User-Agent": "DEGIA-MVP/0.7"
        }
    )

    with urlopen(req, timeout=timeout) as resposta:
        return json.loads(
            resposta.read().decode("utf-8")
        )


def buscar_coordenadas(municipio, uf):

    parametros = urlencode({
        "name": municipio,
        "count": 10,
        "language": "pt",
        "format": "json",
        "countryCode": "BR",
    })

    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + parametros
    )

    dados = requisitar_json(url, timeout=15)

    resultados = dados.get("results") or []

    nome_estado = NOME_UF[uf]

    # Primeiro tenta localizar exatamente município + UF
    for item in resultados:

        if (
            item.get("country_code") == "BR"
            and
            (item.get("admin1") or "").casefold()
            == nome_estado.casefold()
        ):
            return {
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "timezone": item.get("timezone"),
            }

    # Se não encontrar pela UF, não arriscamos usar outra cidade
    raise RuntimeError(
        f"Não foi possível localizar com segurança "
        f"{municipio}/{uf}."
    )


def buscar_historico_12h(municipio, uf):

    local = buscar_coordenadas(municipio, uf)

    latitude = local["latitude"]
    longitude = local["longitude"]
    timezone = local["timezone"]

    if not timezone:
        raise RuntimeError(
            f"Timezone não encontrado para {municipio}/{uf}."
        )

    # Usamos um período histórico já consolidado.
    # O objetivo aqui é produzir contingência local.
    fim = date.today() - timedelta(days=7)
    inicio = fim - timedelta(days=365)

    parametros = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "start_date": inicio.isoformat(),
        "end_date": fim.isoformat(),
        "hourly": "shortwave_radiation_instant",
        "timezone": timezone,
    })

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        + parametros
    )

    dados = requisitar_json(url, timeout=60)

    hourly = dados.get("hourly") or {}

    horarios = hourly.get("time") or []

    valores = (
        hourly.get("shortwave_radiation_instant")
        or []
    )

    registros = []

    for horario, valor in zip(horarios, valores):

        if not horario.endswith("T12:00"):
            continue

        if valor is None:
            continue

        try:
            numero = float(valor)
        except (TypeError, ValueError):
            continue

        if (
            math.isfinite(numero)
            and numero >= 0
        ):
            registros.append(
                (horario, numero)
            )

    if not registros:
        raise RuntimeError(
            f"Nenhum dado válido das 12h encontrado "
            f"para {municipio}/{uf}."
        )

    # Para o fallback queremos um valor histórico
    # forte das 12h.
    #
    # Em vez de usar o maior valor absoluto de um único
    # dia, usamos o percentil 95 dos valores históricos
    # das 12h. Isso evita que um possível extremo isolado
    # determine toda a contingência.

    valores_ordenados = sorted(
        valor for _, valor in registros
    )

    indice_p95 = round(
        0.95 * (len(valores_ordenados) - 1)
    )

    irradiancia_referencia = (
        valores_ordenados[indice_p95]
    )

    # Localiza um dia real que tenha aproximadamente
    # esse valor, apenas para registrar a proveniência.
    registro_referencia = min(
        registros,
        key=lambda item: abs(
            item[1] - irradiancia_referencia
        )
    )

    horario_referencia = registro_referencia[0]

    return {
        "latitude": latitude,
        "longitude": longitude,

        "irradiancia_w_m2": round(
            irradiancia_referencia,
            2
        ),

        "fonte_irradiancia": (
            "Open-Meteo Historical Weather API — "
            "shortwave_radiation_instant"
        ),

        "observacao": (
            f"Fallback histórico DEGIA para "
            f"{municipio}/{uf}. "
            f"Referência baseada no percentil 95 "
            f"dos valores de irradiância das 12h "
            f"entre {inicio.isoformat()} e "
            f"{fim.isoformat()}. "
            f"Registro histórico representativo: "
            f"{horario_referencia[:10]} às 12h."
        ),

        "periodo_inicio": inicio.isoformat(),
        "periodo_fim": fim.isoformat(),

        "metodo_fallback": (
            "P95_IRRADIANCIA_12H"
        ),
    }


def gerar_cache():

    cache = {}

    total = len(CAPITAIS_UF)

    print()
    print("=" * 60)
    print("DEGIA - GERADOR DE CACHE DE IRRADIÂNCIA")
    print("=" * 60)
    print()

    for indice, (uf, municipio) in enumerate(
        CAPITAIS_UF.items(),
        start=1
    ):

        print(
            f"[{indice:02d}/{total}] "
            f"{uf} - {municipio}"
        )

        try:

            referencia = buscar_historico_12h(
                municipio,
                uf
            )

            cache[uf] = referencia

            print(
                "     OK → "
                f"{referencia['irradiancia_w_m2']} W/m²"
            )

        except Exception as erro:

            print(
                f"     ERRO → {erro}"
            )

        # Evita fazer todas as chamadas instantaneamente
        time.sleep(0.5)

    caminho = "cache_irradiancia.json"

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            cache,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    print()
    print("=" * 60)

    print(
        f"Cache gerado: "
        f"{len(cache)}/{total} UFs"
    )

    print(
        f"Arquivo: {caminho}"
    )

    if len(cache) != total:

        faltantes = [
            uf
            for uf in CAPITAIS_UF
            if uf not in cache
        ]

        print(
            "UFs sem cache:",
            ", ".join(faltantes)
        )

    else:

        print(
            "SUCESSO: todas as 27 UFs possuem fallback."
        )

    print("=" * 60)
    print()


if __name__ == "__main__":
    gerar_cache()