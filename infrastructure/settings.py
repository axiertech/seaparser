"""En utvecklingsmiljö; explicit inmatning möjliggör databasfria tester."""
from dataclasses import dataclass, field
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path("/home/web/seaparser/config/app.env")
KEYS = ("APP_ENV", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
        "DB_SSLMODE", "DB_SSLROOTCERT")


def read_env(path):
    """Begränsat KEY=value-format; ingen shellutvärdering eller interpolation."""
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Ogiltigt konfigurationsformat; inga värden visas")
        if key.startswith("TEST_DB_"):
            raise ValueError("Endast utvecklingskonfiguration stöds")
        if key in values:
            raise ValueError("Duplicerad konfigurationsvariabel")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Ogiltigt citerat konfigurationsvärde")
            value = value[1:-1]
        if key in KEYS:
            values[key] = value
    return values


@dataclass(frozen=True)
class DatabaseSettings:
    environment: str
    host: str
    port: int
    name: str
    user: str
    password: str = field(repr=False)
    sslmode: str = "require"
    sslrootcert: str = ""


def load_database(environment, *, variables=None, private_path=PRIVATE):
    if environment != "development":
        raise ValueError("Miljö måste väljas explicit")
    base = tomllib.loads((ROOT / "settings" / f"{environment}.toml").read_text())
    # variables är en explicit inmatning, aldrig hela processmiljön som fallback.
    values = read_env(private_path) if variables is None else dict(variables)
    if values.get("APP_ENV", environment) != environment:
        raise ValueError("APP_ENV stämmer inte med vald miljö")
    db = base["database"]
    if any(k.startswith("TEST_DB_") for k in values):
        raise ValueError("Endast utvecklingskonfiguration stöds")
    def get(key):
        return values.get("DB_" + key.upper(), db.get(key, ""))
    name, user = get("name"), get("user")
    expected = "seaparser"
    if name != expected or user != expected:
        raise ValueError("Databas och roll måste motsvara vald miljö")
    host, password = get("host"), get("password")
    try:
        port = int(get("port"))
    except (ValueError, TypeError):
        raise ValueError("Ogiltig databasport") from None
    if not host or not password or not 1 <= port <= 65535:
        raise ValueError("Nödvändig databaskonfiguration saknas eller är ogiltig")
    sslmode, sslrootcert = get("sslmode"), get("sslrootcert")
    if sslmode not in ("require", "verify-ca", "verify-full"):
        raise ValueError("TLS kräver require, verify-ca eller verify-full")
    # libpq ignorerar sslmode för Unix-sockets; tillåt endast TCP-värdar.
    if host.startswith(("/", "@")) or "," in host:
        raise ValueError("Databasanslutningen kräver en TCP-värd för TLS")
    if sslrootcert and not Path(sslrootcert).is_absolute():
        raise ValueError("CA-filen måste anges med absolut sökväg")
    if sslmode in ("verify-ca", "verify-full") and not sslrootcert:
        raise ValueError("Certifikatverifiering kräver en explicit betrodd CA-fil")
    return DatabaseSettings(environment, host, port, name, user, password,
                            sslmode, sslrootcert)
