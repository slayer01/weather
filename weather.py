#!/usr/bin/env python3
"""Wettervorhersage mit Open-Meteo API."""

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

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
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
}


def error_exit(message: str, code: int) -> NoReturn:
    """Beende mit Fehlermeldung."""
    print(f"Fehler: {message}", file=sys.stderr)
    sys.exit(code)


def create_session() -> requests.Session:
    """Erstelle Session mit Retry-Logik."""
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
    """Suche Ort per Name über Open-Meteo."""
    params: dict = {"name": name, "count": 5, "language": "de"}
    if country_code:
        params["countryCode"] = country_code.upper()

    try:
        response = session.get(GEOCODING_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        error_exit("Zeitüberschreitung bei der Ortssuche.", EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit("Keine Verbindung zum Server.", EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"API-Fehler: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"Anfragefehler: {e}", EXIT_NETWORK_ERROR)

    try:
        data = response.json()
    except json.JSONDecodeError:
        error_exit("Ungültige Server-Antwort.", EXIT_API_ERROR)

    results = data.get("results", [])
    if not results:
        error_exit(f"Ort '{name}' nicht gefunden.", EXIT_LOCATION_NOT_FOUND)

    # Prüfe ob eindeutig (gleiche Koordinaten)
    first = results[0]
    if len(results) > 1:
        has_different = any(
            r.get("latitude") != first.get("latitude") or
            r.get("longitude") != first.get("longitude")
            for r in results[1:]
        )
        if has_different:
            print(f"'{name}' ist nicht eindeutig. Bitte PLZ verwenden:", file=sys.stderr)
            print(f"  weather.py --plz <PLZ>", file=sys.stderr)
            sys.exit(EXIT_AMBIGUOUS)

    lat = first.get("latitude")
    lon = first.get("longitude")
    if lat is None or lon is None:
        error_exit("Koordinaten fehlen.", EXIT_API_ERROR)

    # Baue Ortsnamen
    location_name = first.get("name", name)
    country = first.get("country", "")
    full_name = f"{location_name}, {country}" if country else location_name

    return lat, lon, full_name


def search_by_plz(
    session: requests.Session, plz: str, country_code: str | None = None
) -> tuple[float, float, str]:
    """Suche Ort per PLZ über Nominatim."""
    params: dict = {"postalcode": plz, "format": "json", "addressdetails": 1, "limit": 10}
    if country_code:
        params["countrycodes"] = country_code.lower()

    try:
        response = session.get(NOMINATIM_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        error_exit("Zeitüberschreitung bei der PLZ-Suche.", EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit("Keine Verbindung zum Server.", EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"API-Fehler: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"Anfragefehler: {e}", EXIT_NETWORK_ERROR)

    try:
        results = response.json()
    except json.JSONDecodeError:
        error_exit("Ungültige Server-Antwort.", EXIT_API_ERROR)

    if not results:
        error_exit(f"PLZ '{plz}' nicht gefunden.", EXIT_LOCATION_NOT_FOUND)

    # Prüfe ob PLZ in mehreren Ländern existiert
    if not country_code and len(results) > 1:
        countries = {r.get("address", {}).get("country_code", "").upper() for r in results}
        if len(countries) > 1:
            country_list = ", ".join(sorted(countries))
            print(f"PLZ '{plz}' existiert in mehreren Ländern: {country_list}", file=sys.stderr)
            print(f"Bitte mit --land eingrenzen, z.B.: weather.py --plz {plz} --land DE", file=sys.stderr)
            sys.exit(EXIT_AMBIGUOUS)

    result = results[0]
    lat = float(result["lat"])
    lon = float(result["lon"])

    # Baue Ortsnamen
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
    """Hole Wettervorhersage."""
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
        error_exit("Zeitüberschreitung bei der Wetter-Anfrage.", EXIT_NETWORK_ERROR)
    except requests.exceptions.ConnectionError:
        error_exit("Keine Verbindung zum Wetter-Server.", EXIT_NETWORK_ERROR)
    except requests.exceptions.HTTPError as e:
        error_exit(f"Wetter-API Fehler: {e.response.status_code}", EXIT_API_ERROR)
    except requests.exceptions.RequestException as e:
        error_exit(f"Anfragefehler: {e}", EXIT_NETWORK_ERROR)

    try:
        data = response.json()
    except json.JSONDecodeError:
        error_exit("Ungültige Wetter-Antwort.", EXIT_API_ERROR)

    if "daily" not in data or "hourly" not in data:
        error_exit("Unvollständige Wetterdaten.", EXIT_API_ERROR)

    return data


def safe_float(value: float | None, default: float = 0.0) -> float:
    """Konvertiere sicher zu float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_weather(data: dict, location: str) -> str:
    """Formatiere Wetterdaten zur Ausgabe."""
    daily = data["daily"]
    hourly = data["hourly"]
    num_days = len(daily["time"])

    lines = [f"Wetter für {location}", "=" * 50]

    for day_idx in range(num_days):
        try:
            dt = datetime.fromisoformat(daily["time"][day_idx])
            date = f"{dt.strftime('%d.%m.%Y')} ({WEEKDAYS[dt.weekday()]})"
        except (ValueError, TypeError):
            date = daily["time"][day_idx] or "Unbekannt"

        weather_code = daily["weather_code"][day_idx]
        weather_desc = WEATHER_CODES.get(weather_code, f"Code {weather_code}")

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
            f"Wetterlage:    {weather_desc}",
            f"Temperatur:    {temp_min:.1f}°C bis {temp_max:.1f}°C",
            f"Niederschlag:  {precip:.1f} mm",
            f"Wind (max):    {wind:.1f} km/h",
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
            desc = WEATHER_CODES.get(code, "")

            precip_str = f", {hour_precip:.1f}mm" if hour_precip > 0 else ""
            lines.append(f"  {hour}  {temp:5.1f}°C  {desc}{precip_str}")

    return "\n".join(lines)


def format_weather_json(data: dict, location: str) -> dict:
    """Formatiere Wetterdaten als JSON."""
    daily = data["daily"]
    hourly = data["hourly"]
    num_days = len(daily["time"])

    result: dict = {"location": location, "days": []}

    for day_idx in range(num_days):
        weather_code = daily["weather_code"][day_idx]

        day_data: dict = {
            "date": daily["time"][day_idx],
            "weather_code": weather_code,
            "weather_description": WEATHER_CODES.get(weather_code, f"Code {weather_code}"),
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
                "weather_description": WEATHER_CODES.get(code, f"Code {code}"),
            })

        result["days"].append(day_data)

    return result


def main() -> int:
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(
        description="Wettervorhersage für einen Ort",
        epilog="Beispiel: weather.py Berlin  oder  weather.py --plz 10115",
    )
    parser.add_argument("ort", nargs="?", help="Name des Ortes")
    parser.add_argument("--plz", "-p", type=str, help="Postleitzahl")
    parser.add_argument("--land", "-l", type=str, metavar="CODE", help="Ländercode (DE, AT, CH, ...)")
    parser.add_argument(
        "--tage", "-t",
        type=int,
        default=1,
        choices=range(1, 17),
        metavar="1-16",
        help="Vorhersagetage (Standard: 1)",
    )
    parser.add_argument("--json", "-j", action="store_true", help="JSON-Ausgabe")
    args = parser.parse_args()

    if not args.ort and not args.plz:
        parser.print_help()
        return EXIT_INVALID_INPUT

    if args.ort and args.plz:
        print(f"Hinweis: Ortsname '{args.ort}' wird ignoriert, verwende PLZ.", file=sys.stderr)

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
