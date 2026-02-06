#!/usr/bin/env python3
"""Weather forecast CLI using Open-Meteo API."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import TYPE_CHECKING

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if TYPE_CHECKING:
    from typing import NoReturn

# Exit codes
EXIT_OK = 0
EXIT_LOCATION_NOT_FOUND = 1
EXIT_NETWORK_ERROR = 2
EXIT_API_ERROR = 3
EXIT_INVALID_INPUT = 4
EXIT_AMBIGUOUS = 5

# Timeouts (connect, read)
TIMEOUT = (5, 15)
MAX_RETRIES = 3

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Translations
LANG = {
    "de": {
        "weekdays": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        "weather": {
            0: "Klar",
            1: "Überwiegend klar",
            2: "Teilweise bewölkt",
            3: "Bewölkt",
            45: "Nebel",
            48: "Nebel mit Reif",
            51: "Leichter Nieselregen",
            53: "Mäßiger Nieselregen",
            55: "Starker Nieselregen",
            56: "Gefrierender Nieselregen (leicht)",
            57: "Gefrierender Nieselregen (stark)",
            61: "Leichter Regen",
            63: "Mäßiger Regen",
            65: "Starker Regen",
            66: "Gefrierender Regen (leicht)",
            67: "Gefrierender Regen (stark)",
            71: "Leichter Schneefall",
            73: "Mäßiger Schneefall",
            75: "Starker Schneefall",
            77: "Schneegriesel",
            80: "Leichte Regenschauer",
            81: "Mäßige Regenschauer",
            82: "Starke Regenschauer",
            85: "Leichte Schneeschauer",
            86: "Starke Schneeschauer",
            95: "Gewitter",
            96: "Gewitter mit leichtem Hagel",
            99: "Gewitter mit starkem Hagel",
        },
        "error": "Fehler",
        "weather_for": "Wetter für",
        "condition": "Wetterlage",
        "temperature": "Temperatur",
        "precipitation": "Niederschlag",
        "wind_max": "Wind (max)",
        "unknown": "Unbekannt",
        "to": "bis",
        "timeout_location": "Zeitüberschreitung bei der Ortssuche.",
        "timeout_plz": "Zeitüberschreitung bei der PLZ-Suche.",
        "timeout_weather": "Zeitüberschreitung bei der Wetter-Anfrage.",
        "no_connection": "Keine Verbindung zum Server.",
        "api_error": "API-Fehler",
        "request_error": "Anfragefehler",
        "invalid_response": "Ungültige Server-Antwort.",
        "location_not_found": "Ort '{name}' nicht gefunden.",
        "plz_not_found": "PLZ '{plz}' nicht gefunden.",
        "ambiguous_name": "'{name}' ist nicht eindeutig. Bitte PLZ verwenden:",
        "ambiguous_plz": "PLZ '{plz}' existiert in mehreren Ländern: {countries}",
        "use_plz": "weather.py --plz <PLZ>",
        "use_country": "Bitte mit --land eingrenzen, z.B.: weather.py --plz {plz} --land DE",
        "missing_coords": "Koordinaten fehlen.",
        "incomplete_data": "Unvollständige Wetterdaten.",
        "note_plz_used": "Hinweis: Ortsname '{name}' wird ignoriert, verwende PLZ.",
        "desc": "Wettervorhersage für einen Ort",
        "epilog": "Beispiel: weather.py Berlin  oder  weather.py --plz 10115",
        "help_location": "Name des Ortes",
        "help_plz": "Postleitzahl",
        "help_country": "Ländercode (DE, AT, CH, ...)",
        "help_days": "Vorhersagetage (Standard: 1)",
        "help_json": "JSON-Ausgabe",
        "help_lang": "Sprache: de oder en (Standard: en)",
    },
    "en": {
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "weather": {
            0: "Clear",
            1: "Mostly clear",
            2: "Partly cloudy",
            3: "Cloudy",
            45: "Fog",
            48: "Freezing fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Heavy drizzle",
            56: "Light freezing drizzle",
            57: "Heavy freezing drizzle",
            61: "Light rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Light snowfall",
            73: "Moderate snowfall",
            75: "Heavy snowfall",
            77: "Snow grains",
            80: "Light rain showers",
            81: "Moderate rain showers",
            82: "Heavy rain showers",
            85: "Light snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with light hail",
            99: "Thunderstorm with heavy hail",
        },
        "error": "Error",
        "weather_for": "Weather for",
        "condition": "Condition",
        "temperature": "Temperature",
        "precipitation": "Precipitation",
        "wind_max": "Wind (max)",
        "unknown": "Unknown",
        "to": "to",
        "timeout_location": "Location search timed out.",
        "timeout_plz": "Postal code search timed out.",
        "timeout_weather": "Weather request timed out.",
        "no_connection": "No connection to server.",
        "api_error": "API error",
        "request_error": "Request error",
        "invalid_response": "Invalid server response.",
        "location_not_found": "Location '{name}' not found.",
        "plz_not_found": "Postal code '{plz}' not found.",
        "ambiguous_name": "'{name}' is ambiguous. Please use postal code:",
        "ambiguous_plz": "Postal code '{plz}' exists in multiple countries: {countries}",
        "use_plz": "weather.py --plz <postal_code>",
        "use_country": "Please specify country, e.g.: weather.py --plz {plz} --country DE",
        "missing_coords": "Coordinates missing.",
        "incomplete_data": "Incomplete weather data.",
        "note_plz_used": "Note: Location '{name}' ignored, using postal code.",
        "desc": "Weather forecast for a location",
        "epilog": "Example: weather.py Berlin  or  weather.py --plz 10115",
        "help_location": "Location name",
        "help_plz": "Postal code",
        "help_country": "Country code (DE, AT, CH, ...)",
        "help_days": "Forecast days (default: 1)",
        "help_json": "JSON output",
        "help_lang": "Language: de or en (default: en)",
    },
}

# Current language (set during argument parsing)
_lang = "en"


def t(key: str) -> str:
    """Get translation for key."""
    return LANG[_lang].get(key, key)


def get_weather_desc(code: int) -> str:
    """Get weather description for code."""
    return LANG[_lang]["weather"].get(code, f"Code {code}")


def get_weekday(idx: int) -> str:
    """Get weekday name."""
    return LANG[_lang]["weekdays"][idx]


def error_exit(message: str, code: int) -> NoReturn:
    """Exit with error message."""
    print(f"{t('error')}: {message}", file=sys.stderr)
    sys.exit(code)


def create_session() -> requests.Session:
    """Create session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "weather-cli/1.0"})
    return session


def search_by_name(
    session: requests.Session, name: str, country_code: str | None = None
) -> tuple[float, float, str]:
    """Search location by name via Open-Meteo."""
    params: dict = {"name": name, "count": 5, "language": _lang}
    if country_code:
        params["countryCode"] = country_code.upper()

    try:
        response = session.get(GEOCODING_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        error_exit(t("timeout_location"), EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit(t("no_connection"), EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"{t('api_error')}: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"{t('request_error')}: {e}", EXIT_NETWORK_ERROR)

    try:
        data = response.json()
    except json.JSONDecodeError:
        error_exit(t("invalid_response"), EXIT_API_ERROR)

    results = data.get("results", [])
    if not results:
        error_exit(t("location_not_found").format(name=name), EXIT_LOCATION_NOT_FOUND)

    # Check if unambiguous (same coordinates)
    first = results[0]
    if len(results) > 1:
        has_different = any(
            r.get("latitude") != first.get("latitude") or
            r.get("longitude") != first.get("longitude")
            for r in results[1:]
        )
        if has_different:
            print(t("ambiguous_name").format(name=name), file=sys.stderr)
            print(f"  {t('use_plz')}", file=sys.stderr)
            sys.exit(EXIT_AMBIGUOUS)

    lat = first.get("latitude")
    lon = first.get("longitude")
    if lat is None or lon is None:
        error_exit(t("missing_coords"), EXIT_API_ERROR)

    # Build location name
    location_name = first.get("name", name)
    country = first.get("country", "")
    full_name = f"{location_name}, {country}" if country else location_name

    return lat, lon, full_name


def search_by_plz(
    session: requests.Session, plz: str, country_code: str | None = None
) -> tuple[float, float, str]:
    """Search location by postal code via Nominatim."""
    params: dict = {"postalcode": plz, "format": "json", "addressdetails": 1, "limit": 10}
    if country_code:
        params["countrycodes"] = country_code.lower()

    try:
        response = session.get(NOMINATIM_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        error_exit(t("timeout_plz"), EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit(t("no_connection"), EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"{t('api_error')}: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"{t('request_error')}: {e}", EXIT_NETWORK_ERROR)

    try:
        results = response.json()
    except json.JSONDecodeError:
        error_exit(t("invalid_response"), EXIT_API_ERROR)

    if not results:
        error_exit(t("plz_not_found").format(plz=plz), EXIT_LOCATION_NOT_FOUND)

    # Check if postal code exists in multiple countries
    if not country_code and len(results) > 1:
        countries = {r.get("address", {}).get("country_code", "").upper() for r in results}
        if len(countries) > 1:
            country_list = ", ".join(sorted(countries))
            print(t("ambiguous_plz").format(plz=plz, countries=country_list), file=sys.stderr)
            print(t("use_country").format(plz=plz), file=sys.stderr)
            sys.exit(EXIT_AMBIGUOUS)

    result = results[0]
    lat = float(result["lat"])
    lon = float(result["lon"])

    # Build location name
    addr = result.get("address", {})
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb", "")
    country = addr.get("country", "")
    postal = addr.get("postcode", plz)

    parts = [f"{postal} {city}".strip()]
    if country:
        parts.append(country)
    full_name = ", ".join(p for p in parts if p)

    return lat, lon, full_name


def get_weather(session: requests.Session, lat: float, lon: float, days: int) -> dict:
    """Fetch weather forecast."""
    try:
        response = session.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                "hourly": "temperature_2m,precipitation,weather_code",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        error_exit(t("timeout_weather"), EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit(t("no_connection"), EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"{t('api_error')}: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"{t('request_error')}: {e}", EXIT_NETWORK_ERROR)

    try:
        data = response.json()
    except json.JSONDecodeError:
        error_exit(t("invalid_response"), EXIT_API_ERROR)

    if "daily" not in data or "hourly" not in data:
        error_exit(t("incomplete_data"), EXIT_API_ERROR)

    return data


def safe_float(value: float | None, default: float = 0.0) -> float:
    """Safely convert to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_weather(data: dict, location: str) -> str:
    """Format weather data for text output."""
    daily = data["daily"]
    hourly = data["hourly"]
    num_days = len(daily["time"])

    lines = [f"{t('weather_for')} {location}", "=" * 50]

    for day_idx in range(num_days):
        try:
            dt = datetime.fromisoformat(daily["time"][day_idx])
            date = f"{dt.strftime('%d.%m.%Y')} ({get_weekday(dt.weekday())})"
        except (ValueError, TypeError):
            date = daily["time"][day_idx] or t("unknown")

        weather_code = daily["weather_code"][day_idx]
        weather_desc = get_weather_desc(weather_code)

        temp_min = safe_float(daily["temperature_2m_min"][day_idx])
        temp_max = safe_float(daily["temperature_2m_max"][day_idx])
        precip = safe_float(daily["precipitation_sum"][day_idx])
        wind = safe_float(daily["wind_speed_10m_max"][day_idx])

        if day_idx > 0:
            lines.append("")

        lines.extend([
            "",
            date,
            "-" * 50,
            f"{t('condition'):14} {weather_desc}",
            f"{t('temperature'):14} {temp_min:.1f}°C {t('to')} {temp_max:.1f}°C",
            f"{t('precipitation'):14} {precip:.1f} mm",
            f"{t('wind_max'):14} {wind:.1f} km/h",
        ])

        lines.append("")
        start_hour = day_idx * 24
        end_hour = start_hour + 24

        for i in range(start_hour, min(end_hour, len(hourly["time"]))):
            try:
                hour = datetime.fromisoformat(hourly["time"][i]).strftime("%H:%M")
            except (ValueError, TypeError):
                hour = "??:??"

            temp = safe_float(hourly["temperature_2m"][i])
            hour_precip = safe_float(hourly["precipitation"][i])
            code = hourly["weather_code"][i]
            desc = get_weather_desc(code)

            precip_str = f", {hour_precip:.1f}mm" if hour_precip > 0 else ""
            lines.append(f"  {hour}  {temp:5.1f}°C  {desc}{precip_str}")

    return "\n".join(lines)


def format_weather_json(data: dict, location: str) -> dict:
    """Format weather data as JSON."""
    daily = data["daily"]
    hourly = data["hourly"]
    num_days = len(daily["time"])

    result: dict = {"location": location, "days": []}

    for day_idx in range(num_days):
        weather_code = daily["weather_code"][day_idx]

        day_data: dict = {
            "date": daily["time"][day_idx],
            "weather_code": weather_code,
            "weather_description": get_weather_desc(weather_code),
            "temperature_min": safe_float(daily["temperature_2m_min"][day_idx]),
            "temperature_max": safe_float(daily["temperature_2m_max"][day_idx]),
            "precipitation_sum": safe_float(daily["precipitation_sum"][day_idx]),
            "wind_speed_max": safe_float(daily["wind_speed_10m_max"][day_idx]),
            "hourly": [],
        }

        start_hour = day_idx * 24
        end_hour = start_hour + 24

        for i in range(start_hour, min(end_hour, len(hourly["time"]))):
            code = hourly["weather_code"][i]
            day_data["hourly"].append({
                "time": hourly["time"][i],
                "temperature": safe_float(hourly["temperature_2m"][i]),
                "precipitation": safe_float(hourly["precipitation"][i]),
                "weather_code": code,
                "weather_description": get_weather_desc(code),
            })

        result["days"].append(day_data)

    return result


def main() -> int:
    """Main function."""
    global _lang

    # Pre-parse for language to set up translations for help text
    for i, arg in enumerate(sys.argv[1:]):
        if arg in ("--lang", "-L") and i + 1 < len(sys.argv) - 1:
            lang_val = sys.argv[i + 2]
            if lang_val in ("en", "de"):
                _lang = lang_val
            break
        if arg.startswith("--lang="):
            lang_val = arg.split("=", 1)[1]
            if lang_val in ("en", "de"):
                _lang = lang_val
            break

    parser = argparse.ArgumentParser(
        description=t("desc"),
        epilog=t("epilog"),
    )
    parser.add_argument("ort", nargs="?", help=t("help_location"))
    parser.add_argument("--plz", "-p", type=str, help=t("help_plz"))
    parser.add_argument("--land", "--country", "-l", type=str, metavar="CODE", help=t("help_country"))
    parser.add_argument(
        "--tage", "--days", "-t",
        type=int,
        default=1,
        choices=range(1, 17),
        metavar="1-16",
        help=t("help_days"),
    )
    parser.add_argument("--json", "-j", action="store_true", help=t("help_json"))
    parser.add_argument("--lang", "-L", type=str, choices=["de", "en"], default="en", help=t("help_lang"))
    args = parser.parse_args()

    # Set language from parsed args
    _lang = args.lang

    if not args.ort and not args.plz:
        parser.print_help()
        return EXIT_INVALID_INPUT

    if args.ort and args.plz:
        print(t("note_plz_used").format(name=args.ort), file=sys.stderr)

    session = create_session()

    try:
        if args.plz:
            lat, lon, location = search_by_plz(session, args.plz, args.land)
        else:
            lat, lon, location = search_by_name(session, args.ort.strip(), args.land)

        weather = get_weather(session, lat, lon, args.tage)

        if args.json:
            print(json.dumps(format_weather_json(weather, location), ensure_ascii=False, indent=2))
        else:
            print(format_weather(weather, location))

        return EXIT_OK

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
