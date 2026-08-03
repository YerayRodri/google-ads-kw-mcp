"""
Google Ads Keyword Volumes — Servidor MCP
Expone volúmenes de búsqueda de Google Ads para agentes de IA.
Usa KeywordPlanIdeaService (gRPC) — sin coste de DataForSEO.

Credenciales:
- client_id, client_secret, refresh_token → ~/.config/google-ads-mcp/credentials.json
- developer_token, login_customer_id → env vars GOOGLE_ADS_DEVELOPER_TOKEN y GOOGLE_ADS_LOGIN_CUSTOMER_ID
"""

import json
import os
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from mcp.server.fastmcp import FastMCP

CREDENTIALS_PATH = Path(
    os.environ.get(
        "GOOGLE_ADS_CREDENTIALS_PATH",
        str(Path.home() / ".config/google-ads-mcp/credentials.json"),
    )
)


def _load_credentials() -> dict:
    raw = json.loads(CREDENTIALS_PATH.read_text())
    developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if not developer_token or not login_customer_id:
        raise RuntimeError(
            "Faltan env vars GOOGLE_ADS_DEVELOPER_TOKEN y/o GOOGLE_ADS_LOGIN_CUSTOMER_ID"
        )
    return {
        "developer_token": developer_token,
        "client_id": raw["client_id"],
        "client_secret": raw["client_secret"],
        "refresh_token": raw["refresh_token"],
        "login_customer_id": login_customer_id,
        "use_proto_plus": True,
    }


COUNTRY_MAP = {
    "ES": "geoTargetConstants/2724",
    "MX": "geoTargetConstants/2484",
    "AR": "geoTargetConstants/2032",
    "CO": "geoTargetConstants/2170",
    "US": "geoTargetConstants/2840",
    "UK": "geoTargetConstants/2826",
    "GB": "geoTargetConstants/2826",
    "FR": "geoTargetConstants/2250",
    "DE": "geoTargetConstants/2276",
    "IT": "geoTargetConstants/2380",
    "BR": "geoTargetConstants/2076",
    "PT": "geoTargetConstants/2620",
    "CL": "geoTargetConstants/2152",
    "PE": "geoTargetConstants/2604",
    "EC": "geoTargetConstants/2218",
    "VE": "geoTargetConstants/2862",
    "NL": "geoTargetConstants/2528",
    "AU": "geoTargetConstants/2036",
    "CA": "geoTargetConstants/2124",
    "JP": "geoTargetConstants/2392",
}

LANGUAGE_MAP = {
    "es": "languageConstants/1003",
    "en": "languageConstants/1000",
    "fr": "languageConstants/1002",
    "de": "languageConstants/1001",
    "it": "languageConstants/1004",
    "pt": "languageConstants/1014",
    "nl": "languageConstants/1010",
    "ja": "languageConstants/1005",
    "zh": "languageConstants/1017",
    "ru": "languageConstants/1013",
    "ar": "languageConstants/1019",
}

mcp = FastMCP("google-ads-kw")


@mcp.tool()
def get_keyword_volumes(
    keywords: list[str],
    customer_id: str,
    country: str = "ES",
    language: str = "es",
) -> str:
    """
    Obtiene volúmenes de búsqueda mensuales de Google Ads para un array de palabras clave.
    Gratuito — usa la API de Google Ads directamente (sin coste de DataForSEO).

    Args:
        keywords: Array de palabras clave, máximo 20 por llamada.
                  Ejemplo: ["surf lessons", "escuela surf", "clases de surf"]
        customer_id: ID de cuenta Google Ads (sin guiones).
        country:  Código de país ISO. Países disponibles: ES, MX, AR, CO, US, GB,
                  FR, DE, IT, BR, PT, CL, PE, EC, VE, NL, AU, CA, JP.
                  Por defecto: ES (España).
        language: Código de idioma. Disponibles: es, en, fr, de, it, pt, nl, ja, zh, ru, ar.
                  Por defecto: es (español).

    Returns:
        JSON con lista de {keyword, avg_monthly_searches, competition, competition_index,
        low_top_of_page_bid_micros, high_top_of_page_bid_micros}
    """
    if not keywords:
        return json.dumps({"error": "La lista de keywords no puede estar vacía."})

    if len(keywords) > 20:
        return json.dumps({"error": f"Máximo 20 keywords por llamada. Enviaste {len(keywords)}."})

    country_upper = country.upper()
    language_lower = language.lower()

    if country_upper not in COUNTRY_MAP:
        available = ", ".join(sorted(COUNTRY_MAP.keys()))
        return json.dumps({"error": f"País '{country}' no soportado. Disponibles: {available}"})

    if language_lower not in LANGUAGE_MAP:
        available = ", ".join(sorted(LANGUAGE_MAP.keys()))
        return json.dumps({"error": f"Idioma '{language}' no soportado. Disponibles: {available}"})

    try:
        client = GoogleAdsClient.load_from_dict(_load_credentials())
        kw_service = client.get_service("KeywordPlanIdeaService")

        request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        request.customer_id = customer_id
        request.keywords.extend(keywords)
        request.language = LANGUAGE_MAP[language_lower]
        request.geo_target_constants.append(COUNTRY_MAP[country_upper])
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )

        response = kw_service.generate_keyword_historical_metrics(request=request)

        results = []
        for result in response.results:
            metrics = result.keyword_metrics
            results.append({
                "keyword": result.text,
                "avg_monthly_searches": metrics.avg_monthly_searches,
                "competition": metrics.competition.name,
                "competition_index": metrics.competition_index,
                "low_top_of_page_bid_micros": metrics.low_top_of_page_bid_micros,
                "high_top_of_page_bid_micros": metrics.high_top_of_page_bid_micros,
            })

        return json.dumps({
            "country": country_upper,
            "language": language_lower,
            "results": results,
            "total": len(results),
        }, ensure_ascii=False, indent=2)

    except GoogleAdsException as ex:
        errors = [
            {"code": str(e.error_code), "message": e.message}
            for e in ex.failure.errors
        ]
        return json.dumps({"error": "GoogleAdsException", "details": errors})
    except Exception as e:
        return json.dumps({"error": type(e).__name__, "message": str(e)})


@mcp.tool()
def list_keyword_countries() -> str:
    """
    Lista todos los países disponibles para consultar volúmenes de búsqueda.

    Returns:
        JSON con {código: descripción} de cada país soportado.
    """
    country_names = {
        "ES": "España", "MX": "México", "AR": "Argentina", "CO": "Colombia",
        "US": "Estados Unidos", "GB": "Reino Unido", "FR": "Francia",
        "DE": "Alemania", "IT": "Italia", "BR": "Brasil", "PT": "Portugal",
        "CL": "Chile", "PE": "Perú", "EC": "Ecuador", "VE": "Venezuela",
        "NL": "Países Bajos", "AU": "Australia", "CA": "Canadá", "JP": "Japón",
    }
    return json.dumps(country_names, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
