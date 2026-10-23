"""En utvecklingsmiljö; explicit inmatning möjliggör databasfria tester."""
from dataclasses import dataclass, field
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path("/home/web/seaparser/config/app.env")
KEYS = ("APP_ENV", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
        "DB_SSLMODE", "DB_SSLROOTCERT", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL")


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


BUDGET_PATH = ROOT / "config" / "budget.conf"

BUDGET_KEYS = frozenset({
    "APP_MAX_API_CALLS", "APP_MAX_TOOL_ROUNDS", "APP_MAX_ITERATIONS",
    "APP_MAX_TOKENS_FLASH", "APP_MAX_TOKENS_PRO",
    "AUTONOMY_MAX_API_CALLS", "AUTONOMY_MAX_TOOL_ROUNDS",
    "AUTONOMY_MAX_ITERATIONS", "AUTONOMY_MAX_TOKENS_FLASH",
    "AUTONOMY_MAX_TOKENS_PRO",
    "DEEPSEEK_MAX_RETRIES", "DEEPSEEK_BACKOFF_SECONDS",
    "DEEPSEEK_TIMEOUT_FLASH", "DEEPSEEK_TIMEOUT_PRO",
})


def load_budget(path=None):
    """Läser budget.conf; tom dict om filen saknas.

    Samma KEY=value-format som app.env men utan hemligheter.
    Okända nycklar avvisas så att stavfel inte tystnar.
    """
    from pathlib import Path as _Path
    p = _Path(path) if path is not None else BUDGET_PATH
    if not p.exists():
        return {}
    values = {}
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"Ogiltigt budgetformat i {p.name}")
        if key not in BUDGET_KEYS:
            raise ValueError(f"Okänd budgetnyckel: {key}")
        if key in values:
            raise ValueError(f"Duplicerad budgetnyckel: {key}")
        values[key] = value.strip()
    return values


_BUDGET = load_budget()


def budget_int(key, default):
    """Return int from budget.conf, else default on missing or invalid."""
    try:
        return int(_BUDGET[key])
    except (KeyError, ValueError, TypeError):
        return default


def budget_float(key, default):
    """Return float from budget.conf, else default on missing or invalid."""
    try:
        return float(_BUDGET[key])
    except (KeyError, ValueError, TypeError):
        return default


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
    if host.startswith(("/", "@")) or "," in host:
        raise ValueError("Databasanslutningen kräver en TCP-värd för TLS")
    if sslrootcert and not Path(sslrootcert).is_absolute():
        raise ValueError("CA-filen måste anges med absolut sökväg")
    if sslmode in ("verify-ca", "verify-full") and not sslrootcert:
        raise ValueError("Certifikatverifiering kräver en explicit betrodd CA-fil")
    return DatabaseSettings(environment, host, port, name, user, password,
                            sslmode, sslrootcert)


DEEPSEEK_DEFAULT_MODEL = "deepseek-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_STRONG_MODEL = "deepseek-v4-pro"


@dataclass(frozen=True)
class DeepSeekSettings:
    api_key: str = field(repr=False)
    model: str = DEEPSEEK_DEFAULT_MODEL
    base_url: str = DEEPSEEK_BASE_URL


def load_deepseek(*, variables=None, private_path=PRIVATE, model_override=None):
    """Läser DeepSeek-konfiguration utan att någonsin logga hemligheten."""
    values = read_env(private_path) if variables is None else dict(variables)
    api_key = values.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY saknas i konfigurationen")
    if any(c.isspace() for c in api_key):
        raise ValueError("DEEPSEEK_API_KEY innehåller ogiltiga tecken")
    if model_override is not None:
        model = model_override
    else:
        model = values.get("DEEPSEEK_MODEL", DEEPSEEK_DEFAULT_MODEL).strip() or DEEPSEEK_DEFAULT_MODEL
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", model):
        raise ValueError("DEEPSEEK_MODEL har ogiltigt format")
    return DeepSeekSettings(api_key=api_key, model=model)
