# SeaParser

Privat projekt för väderbaserad ruttplanering för segel- och motorbåtar.

Appen ska jämföra snabbaste och bekvämaste rutt samt flera avgångstider. Vädret ska utvärderas vid den position och tid där båten beräknas befinna sig. Beräkningsmotorn ska vara deterministisk och kunna testas utan internet, databas eller användargränssnitt.

## Status

En fristående beräkningsprototyp med syntetiska data finns i
[prototype/](prototype/README.md). Den använder enbart Pythons standardbibliotek
och separerar båtmodell, väder/ström, integration och JSON-presentation.
Endast migrationshistorik finns i databasen; produktmodell och deployment återstår.

Bekräftad servermiljö: Ubuntu 26.04.1 LTS, Linux-användare `seaparser`, projektkatalog `/home/web/seaparser/app`, privat konfiguration `/home/web/seaparser/config/app.env`, Node.js 22.22.1, npm 9.2.0 och Codex CLI 0.162.1. Repositoryt är privat hos `axiertech/seaparser` och klonat på servern. Git-läsning är verifierad; push är ännu inte testad. Docker är inte installerat enligt senaste kontrollen.

Databas och roll är seaparser i projektets enda utvecklingsmiljö. Serveridentitet, PostGIS 3.6.2 och behörigheter verifierades 2026-10-12 med skrivskyddad diagnostik; se docs/progress.md. Ny kontroll kan göras via `.venv/bin/python -B -m scripts.diagnose_database`. Enhetstester är databasfria. Inför drift separeras miljön och en ny driftroll skapas. Domänkoppling ingår inte i första steget.

## Läsordning

- `AGENTS.md`: instruktioner för utvecklingsagenten.
- `docs/requirements.md`: krav och första acceptanskriterier.
- `docs/architecture.md`: ansvarsfördelning och tekniska vägval.
- `docs/decisions.md`: beslut och öppna frågor.
- `deploy/app.env.example`: exempel på miljöinställningar utan hemligheter.

Första utvecklingsleveransen ska vara en verifierbar beräkningsprototyp med syntetiska prognoser. Konton, abonnemang och betalning följer efter att kärnan har validerats.
