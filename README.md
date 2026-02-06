# Weather CLI

Command-line tool for weather forecasts using the [Open-Meteo API](https://open-meteo.com/).

## Installation

```bash
pip install requests
```

## Usage

```bash
python3 weather.py <location> [--country CODE] [--days N] [--lang LANG] [--json]
python3 weather.py --plz <postal_code> [--country CODE] [--days N] [--lang LANG] [--json]
```

### Arguments

| Argument | Short | Description |
|----------|-------|-------------|
| `location` | | Location name |
| `--plz` | `-p` | Postal code (alternative to location name) |
| `--land` / `--country` | `-l` | Country code (DE, AT, CH, US, ...) |
| `--tage` / `--days` | `-t` | Forecast days, 1-16 (default: 1) |
| `--lang` | `-L` | Language: `de` or `en` (default: en) |
| `--json` | `-j` | JSON output |

### Examples

```bash
# By location name
python3 weather.py Berlin
python3 weather.py Munich --country DE

# By postal code
python3 weather.py --plz 10115
python3 weather.py --plz 10115 --country DE

# Multiple days
python3 weather.py Berlin --days 7

# German output
python3 weather.py Berlin --lang de

# JSON output
python3 weather.py Berlin --json
```

### Ambiguous Locations

If multiple locations match (e.g., "Frankfurt"):

```
'Frankfurt' is ambiguous. Please use postal code:
  weather.py --plz <postal_code>
```

If a postal code exists in multiple countries:

```
Postal code '10115' exists in multiple countries: DE, US, ...
Please specify country, e.g.: weather.py --plz 10115 --country DE
```

## APIs

- [Open-Meteo](https://open-meteo.com/) - Weather data and location search
- [Nominatim/OpenStreetMap](https://nominatim.org/) - Postal code search

No registration or API keys required.
