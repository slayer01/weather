# Weather CLI

Kommandozeilen-Tool für Wettervorhersagen mit der [Open-Meteo API](https://open-meteo.com/).

## Installation

```bash
pip install requests
```

## Verwendung

```bash
python3 weather.py <ort> [--land CODE] [--tage N] [--json]
python3 weather.py --plz <PLZ> [--land CODE] [--tage N] [--json]
```

### Argumente

| Argument | Kurz | Beschreibung |
|----------|------|--------------|
| `ort` | | Name des Ortes |
| `--plz PLZ` | `-p` | Postleitzahl (alternativ zum Ortsnamen) |
| `--land CODE` | `-l` | Ländercode (DE, AT, CH, US, ...) |
| `--tage N` | `-t` | Vorhersagetage, 1-16 (Standard: 1) |
| `--json` | `-j` | Ausgabe im JSON-Format |

### Beispiele

```bash
# Per Ortsname
python3 weather.py Berlin
python3 weather.py München --land DE

# Per PLZ
python3 weather.py --plz 10115
python3 weather.py --plz 10115 --land DE

# Mehrere Tage
python3 weather.py Berlin -t 7

# JSON-Ausgabe
python3 weather.py Berlin --json
```

### Mehrdeutige Orte

Bei mehreren Treffern (z.B. "Frankfurt") erscheint ein Hinweis:

```
'Frankfurt' ist nicht eindeutig. Bitte PLZ verwenden:
  weather.py --plz <PLZ>
```

## APIs

- [Open-Meteo](https://open-meteo.com/) - Wetterdaten und Ortssuche
- [Nominatim/OpenStreetMap](https://nominatim.org/) - PLZ-Suche

Keine Registrierung oder API-Keys erforderlich.
