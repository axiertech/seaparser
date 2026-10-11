# Beslutslogg

## Bekräftat 2026-10-11

- Privat projekt hos axiertech, fristående från Splitgrid.
- Repository: `axiertech/seaparser`.
- Hemmakatalog: `/home/web/seaparser`; kod: `app/`; privat konfiguration: `config/app.env`.
- Linux-användaren seaparser saknar sudo. Config-katalog har 700 och filen 600.
- Ubuntu 26.04.1 LTS, Git 2.53.0, Node.js 22.22.1, npm 9.2.0 och Codex CLI 0.162.1 har rapporterats.
- Codex-inloggning med ChatGPT samt SSH-kloning av repositoryt har lyckats.
- PostGIS rapporteras aktivt. Databasanslutning behöver verifieras efter ändrade namnuppgifter.
- Kod, layout, konfiguration och databasåtkomst ska separeras.
- Designer ska kunna ändra befintlig layout visuellt utan programmerare.
- Modellbehov utvärderas veckovis och under aktivt arbete vid behov. Dyrare alternativ rekommenderas med konkret motivering.

## Föreslaget, ännu inte beslutat

- Python/FastAPI, PostgreSQL/PostGIS och React/TypeScript.
- Beräkningsprototyp före konton och betalning.
- Mobilanpassad webbapp som första plattform.

## Öppna beslut före implementation

- Första verkliga testregion och representativa resor.
- Databasnamn, roll, värd och port, kontrollerade utan lösenordsutskrift.
- Visuell layouteditor och dess licens, kostnad, export och komponentintegration.
- Första båtprofiler och rättigheter till polarer.
- Prognos- och geografiska datakällor samt kvalitet och licenser.
- Numeriska toleranser, komfortmått och absoluta begränsningar.
- Routingalgoritm efter referenstester.
- Exakt definition av abonnemangens uppdateringar.
- Docker eller annan reproducerbar drift och tillåtna serveroperationer.
- Godkännande av första GitHub-publiceringen av dessa grundfiler.
