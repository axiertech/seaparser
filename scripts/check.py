"""Beroendefria syntax- och arkitekturkontroller; inget nätverk eller DB."""
import ast
import json
import re
from pathlib import Path
import subprocess
import sys
import tomllib
import warnings
warnings.simplefilter("error", SyntaxWarning)

root = Path(__file__).resolve().parents[1]
for folder in ("prototype", "infrastructure", "scripts", "tests"):
    for path in (root / folder).rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path.relative_to(root)))
        if path.name in ("calculation.py", "model.py", "environment.py", "obstacles.py", "routes.py", "polar.py", "sailing.py", "weather.py", "forecast.py"):
            allowed = {"dataclasses", "datetime", "math", "typing"}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.ImportFrom) and node.level:
                        continue
                    modules = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
                    if any(m.split(".")[0] not in allowed for m in modules):
                        raise SystemExit("Otillåtet beroende i domänen")
for path in (root / "settings").glob("*.toml"):
    tomllib.loads(path.read_text())
project = tomllib.loads((root / "pyproject.toml").read_text())
if project["project"]["dependencies"] or any(
    line.strip() and not line.startswith("#")
    for line in (root / "requirements.lock").read_text().splitlines()
):
    raise SystemExit("Nya beroenden kräver granskad låsstrategi")
package = json.loads((root / "frontend/package.json").read_text())
lock = json.loads((root / "frontend/package-lock.json").read_text())
if package.get("dependencies") or package.get("devDependencies") or set(lock["packages"]) != {""}:
    raise SystemExit("Nya frontendberoenden kräver uppdaterad kontroll")
# Every external action must reference an immutable complete Git commit.
for workflow in (root / ".github/workflows").glob("*.yml"):
    for line in workflow.read_text().splitlines():
        match = re.match(r"\s*-?\s*uses:\s*(\S+)", line)
        if match and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}", match[1]):
            raise SystemExit("GitHub Actions kräver granskad fullständig commit-SHA")
for suite in ("prototype/tests", "tests"):
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", suite, "-v"], cwd=root, check=True)
print("Syntax, konfiguration, beroendebas, domängränser och tester godkända")
