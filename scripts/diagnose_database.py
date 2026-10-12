"""Skrivskyddad diagnostik utan utskrift av privat konfiguration eller rå feltext."""
import socket
import subprocess
from infrastructure.settings import ROOT, load_database
from infrastructure.postgres import psql_environment


def main():
    try:
        db = load_database("development")
        with socket.create_connection((db.host, db.port), timeout=5):
            pass
        env = psql_environment(db, read_only=True)
        result = subprocess.run(
            ["psql", "-X", "-w", "--set=ON_ERROR_STOP=1", "--file=-"],
            input=(ROOT / "deploy/diagnose-database.sql").read_text(),
            env=env, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise SystemExit("PostgreSQL-diagnostik misslyckades; rå feltext döljs")
        # Även serverns resultat filtreras mot det inlästa lösenordet.
        print(result.stdout.replace(db.password, "[dolt]"), end="")
    except PermissionError as error:
        raise SystemExit(f"Anslutning nekad av körmiljön; PermissionError errno={error.errno}") from None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise SystemExit("Diagnostik misslyckades; konfiguration och rå feltext döljs") from None


if __name__ == "__main__":
    main()
