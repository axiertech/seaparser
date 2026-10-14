# Kontrollerad utvecklingsmiljö – förslag 2026-10-12

## Uppdaterad test-/auditinstallation 2026-10-14

Nedan finns den ursprungliga miljöbeskrivningen. Aktuella runtimeberoenden och
testberoenden anges i `pyproject.toml`; `requirements.lock` innehåller båda med
exakta versioner och wheel-hashar för CPython 3.14/Linux x86_64.
Installera hela låsfilen i en venv utan system-site-packages:

```sh
python3 -m venv /tmp/seaparser-ci-clean
/tmp/seaparser-ci-clean/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements.lock
npm --prefix frontend ci --ignore-scripts
make check PYTHON=/tmp/seaparser-ci-clean/bin/python
```

Offline NetCDF-audit kräver numpy, xarray, h5netcdf och h5py samt låsta transitiva
beroenden packaging, pandas, python-dateutil och six. Audit och fixture-export
väljer explicit h5netcdf för HDF5/NetCDF-filerna. Toolbox, nätverkshämtning och
databas krävs inte för testerna. Paketversionerna verifierades mot officiella
PyPI-releaseposter före installation; inga befintliga låsta paket uppgraderades.

CI installerar samma hela låsfil och kör `scripts.check`, vars unittest-discovery
kör både `test_forecast_coordinate_extents.py` och `test_copernicus_import.py`.
NetCDF-integrationstesterna har inga beroendevillkorade skips: saknade paket ska
fälla kontrollen. En utvecklingsmiljö med extra Toolbox-paket räcker därför inte
som verifiering av CI-installationen.

## Omfattning och antaganden

Pythonprototypen använder endast standardbiblioteket. Ingen frontend, API eller
produktdatabasmodell finns. Därför låses nu en tom beroendegraf i
requirements.lock och frontend/package-lock.json. Det är inte en låsning av
framtida FastAPI/React/editor. Python 3.14.4, Node 22.22.1 och npm 9.2.0 har
verifierats lokalt; versionerna är baslinje, inte påstående om senaste version.
Inget installerades. Officiella versioner/licenser ska verifieras före varje
framtida installation. Editorval kräver kravens fullständiga utvärdering.

Python isoleras i .venv med system-site-packages avstängt (venv-standard).
Frontendberoenden placeras i frontend/node_modules via npm ci, utan globala
installationer. Verktygsversioner finns i .python-version, .nvmrc och package.json.
pyproject.toml beskriver projektet; körning sker från projektrot utan paketering.
Inga tredjepartsverktyg krävs för nuvarande tester. När beroenden tillkommer:
granskade exakta versioner och transitive hash-lås för Python, npm-lås för frontend;
uppdatera samtidigt scripts/check.py som nu uttryckligen bevakar den tomma grafen.

## Konfiguration och separation

Projektet har en enda utvecklingsmiljö med databas och roll seaparser.
settings/development.toml innehåller offentliga standarder. Privat konfiguration
läses från /home/web/seaparser/config/app.env som data, aldrig via shell source.
Endast kända APP_ENV/DB_*-nycklar läses. Lösenord visas inte i objektvisning eller
fel och ska aldrig versionshanteras. Separat testlösenord krävs inte.
Explicit variables-inmatning ersätter privat fil helt och används med syntetiska
värden i enhetstester. Endast miljön development accepteras.

## Migrationer och kontroller

`make check` kör alla enhetstester utan databas, syntax/TOML, beroendebas,
domängränser och frontendkontroller. Frontend har ännu inga produkttester.
`make migration-plan` ansluter inte. Första migrationen är godkänd och tillämpad;
framtida migrationer kräver separat godkännande. `--status` ansluter skrivskyddat.
CI kör endast offlinekontroller; tidigare migrationsjobb är borttaget.

Skrivskyddad diagnostik med projektrollen är godkänd. Databasändringar,
framtida migrationer, privata filändringar, sudo, systempaket och push ingår inte.
Databastester får inte tömma befintliga tabeller. Använd rollback och testegna
objekt utan ändringar av befintliga sekvenser eller externa sidoeffekter.
Se [database-test-runbook.md](database-test-runbook.md) för diagnostik och testregler.
Inför drift ska miljön separeras och en ny driftroll skapas med minsta rättigheter.

TLS-policy och isolerade integrationstesters plan finns i
[database-test-runbook.md](database-test-runbook.md). Actions-revisioner och
granskningsomfattning finns i [actions-review.md](actions-review.md).
