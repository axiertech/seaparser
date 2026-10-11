"""Skriv bara kända variabelnamn och förekomst, aldrig värden."""
from infrastructure.settings import KEYS, PRIVATE, read_env

try:
    values = read_env(PRIVATE)
except (OSError, ValueError):
    raise SystemExit("Konfiguration kunde inte kontrolleras; inga värden visas")
for key in KEYS:
    print(f"{key}: {'finns' if values.get(key) else 'saknas/tomt'}")
