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
for folder in ("prototype", "infrastructure", "application", "presentation", "api", "deployment", "scripts", "tests"):
    for path in (root / folder).rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path.relative_to(root)))
        if path.name in ("calculation.py", "model.py", "environment.py", "obstacles.py", "routes.py", "polar.py", "sailing.py", "weather.py", "forecast.py", "departures.py", "forecast_data.py", "forecast_metadata.py", "segment_weather.py", "polygon.py", "auto_routing.py"):
            allowed = {"dataclasses", "datetime", "math", "typing"}
            if path.name in ("segment_weather.py", "polygon.py"):
                allowed.add("fractions")
            if path.name == "auto_routing.py":
                allowed.add("heapq")
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
# Exact direct pins, complete hashed wheel lock and installed metadata must agree.
from importlib.metadata import version
locked = {}
for line in (root / "requirements.lock").read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    match = re.fullmatch(r"([a-z0-9-]+)==([^ ]+) --hash=sha256:([0-9a-f]{64})", line)
    if not match or match[1] in locked:
        raise SystemExit("Ogiltig eller dubbel Pythonlåsning")
    locked[match[1]] = match[2]
for pin in project["project"]["dependencies"] + project["project"]["optional-dependencies"]["test"]:
    name, exact = pin.split("==")
    if locked.get(name) != exact:
        raise SystemExit("Direktberoende saknar motsvarande hashlås")
for name, exact in locked.items():
    if version(name) != exact:
        raise SystemExit("Installerade Pythonberoenden stämmer inte med låsfilen")
subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
package = json.loads((root / "frontend/package.json").read_text())
lock = json.loads((root / "frontend/package-lock.json").read_text())
for group in ("dependencies", "devDependencies"):
    if package.get(group, {}) != lock["packages"][""].get(group, {}):
        raise SystemExit("npm-direktberoenden och låsfil skiljer sig")
    for name, pin in package.get(group, {}).items():
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pin) or lock["packages"]["node_modules/"+name]["version"] != pin:
            raise SystemExit("npm kräver exakta versionslås")
for name, item in lock["packages"].items():
    if name and (not item.get("resolved", "").startswith("https://registry.npmjs.org/") or not item.get("integrity", "").startswith("sha512-")):
        raise SystemExit("npm-paket saknar officiell källa/integritet")
# Every external action must reference an immutable complete Git commit.
for workflow in (root / ".github/workflows").glob("*.yml"):
    for line in workflow.read_text().splitlines():
        command = re.match(r"\s*-\s*run:\s*(.+)", line)
        if command and not command[1].startswith(("'", '"', '|', '>')) and re.search(r":(?:\s|$)", command[1]):
            raise SystemExit("Workflow-kommandon med kolon/mellanslag kräver YAML-block eller citering")
        match = re.match(r"\s*-?\s*uses:\s*(\S+)", line)
        if match and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}", match[1]):
            raise SystemExit("GitHub Actions kräver granskad fullständig commit-SHA")
subprocess.run(["/bin/bash", "-n", str(root / "deployment/activate-demo.sh"), str(root / "deployment/rollback-demo.sh"), str(root / "deployment/activation-preflight.sh"), str(root / "deployment/activate-vinga.sh"), str(root / "deployment/rollback-vinga.sh")], check=True)
for suite in ("prototype/tests", "tests"):
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", suite, "-v"], cwd=root, check=True)
print("Syntax, konfiguration, beroendebas, domängränser och tester godkända")
